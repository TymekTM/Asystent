// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, AppHandle, Window, WindowEvent};
use tokio::time::sleep;
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use raw_window_handle::{HasRawWindowHandle, RawWindowHandle};
use std::time::{Instant, Duration};
use futures_util::StreamExt;

#[derive(Clone, Serialize)]
struct StatusUpdate {
    status: String,
    text: String,
    is_listening: bool,
    is_speaking: bool,
    wake_word_detected: bool,
}

#[derive(Debug, Deserialize, Clone)]
struct AssistantStatusResponse {
    status: String,
    text: Option<String>,
    message: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct OverlayState {
    visible: bool,
    status: String,
    text: String,
    is_listening: bool,
    is_speaking: bool,
    wake_word_detected: bool,
    interactive_mode: bool,  // New field to track interactive state
    #[serde(skip_serializing)]
    last_activity_time: Instant,
}

impl OverlayState {
    fn new() -> Self {
        OverlayState {
            visible: false,
            status: "Offline".to_string(),
            text: "".to_string(),
            is_listening: false,
            is_speaking: false,
            wake_word_detected: false,
            interactive_mode: false,
            last_activity_time: Instant::now(),
        }
    }
}

type SharedState = Arc<Mutex<OverlayState>>;

#[tauri::command]
async fn show_overlay(window: Window, state: tauri::State<'_, SharedState>) -> Result<(), String> {
    window.show().map_err(|e| e.to_string())?;
    {
        let mut overlay_state = state.lock().unwrap();
        overlay_state.visible = true;
    }

    // Apply proper click-through when showing
    set_click_through(&window, true);
    Ok(())
}

#[tauri::command]
async fn hide_overlay(window: Window, state: tauri::State<'_, SharedState>) -> Result<(), String> {
    window.hide().map_err(|e| e.to_string())?;
    {
        let mut overlay_state = state.lock().unwrap();
        overlay_state.visible = false;
        overlay_state.interactive_mode = false;
    }
    Ok(())
}

#[tauri::command]
async fn update_status(
    window: Window,
    status: String,
    text: String,
    is_listening: bool,
    is_speaking: bool,
    wake_word_detected: bool,
    state: tauri::State<'_, SharedState>
) -> Result<(), String> {
    {
        let mut overlay_state = state.lock().unwrap();
        overlay_state.status = status.clone();
        overlay_state.text = text.clone();
        overlay_state.is_listening = is_listening;
        overlay_state.is_speaking = is_speaking;
        overlay_state.wake_word_detected = wake_word_detected;

        // Determine if overlay should be interactive
        let should_be_interactive = is_listening && overlay_state.visible;

        if should_be_interactive != overlay_state.interactive_mode {
            overlay_state.interactive_mode = should_be_interactive;
            // Apply click-through settings
            set_click_through(&window, !should_be_interactive);
        }
    }

    window.emit("status-update", serde_json::json!({
        "status": status,
        "text": text,
        "is_listening": is_listening,
        "is_speaking": is_speaking,
        "wake_word_detected": wake_word_detected
    })).map_err(|e| e.to_string())?;

    Ok(())
}

#[tauri::command]
fn get_state(state: tauri::State<Arc<Mutex<OverlayState>>>) -> Result<OverlayState, String> {
    Ok(state.inner().lock().unwrap().clone())
}

async fn poll_assistant_status(app_handle: AppHandle, state: Arc<Mutex<OverlayState>>) {
    let client = reqwest::Client::new();
    let ports = vec!["5000", "5001"];
    let mut working_port = None;

    // Find which port is working
    for port in &ports {
        let test_url = format!("http://localhost:{}/api/status", port);
        if let Ok(response) = client.get(&test_url).send().await {
            if response.status().is_success() {
                working_port = Some(port.to_string());
                println!("[Rust] Found working port: {}", port);
                break;
            }
        }
    }

    let current_port = working_port.unwrap_or_else(|| {
        std::env::var("GAJA_PORT").unwrap_or_else(|_| {
            if cfg!(debug_assertions) { "5001".to_string() } else { "5000".to_string() }
        })
    });

    // Try SSE first, fallback to polling if not available
    let sse_url = format!("http://localhost:{}/status/stream", current_port);

    println!("[Rust] Attempting to connect to SSE stream: {}", sse_url);

    match client.get(&sse_url).send().await {
        Ok(response) => {
            if response.status().is_success() {
                println!("[Rust] Successfully connected to SSE stream");
                handle_sse_stream(response, app_handle.clone(), state.clone()).await;
            } else {
                println!("[Rust] SSE not available, falling back to polling");
                handle_polling(client, current_port, app_handle, state).await;
            }
        }
        Err(e) => {
            println!("[Rust] Failed to connect to SSE: {}, falling back to polling", e);
            handle_polling(client, current_port, app_handle, state).await;
        }
    }
}

async fn handle_sse_stream(response: reqwest::Response, app_handle: AppHandle, state: Arc<Mutex<OverlayState>>) {
    let mut stream = response.bytes_stream();
    let mut buffer = String::new();

    while let Some(chunk) = stream.next().await {
        match chunk {
            Ok(bytes) => {
                let chunk_str = String::from_utf8_lossy(&bytes);
                buffer.push_str(&chunk_str);

                // Process complete SSE messages
                while let Some(pos) = buffer.find("\n\n") {
                    let message = buffer[..pos].to_string();
                    buffer.drain(..pos + 2);

                    if message.starts_with("data: ") {
                        let json_str = &message[6..];
                        match serde_json::from_str::<serde_json::Value>(json_str) {
                            Ok(data) => {
                                println!("[Rust] Received SSE data: {}", data);
                                process_status_data(data, app_handle.clone(), state.clone()).await;
                            }
                            Err(e) => {
                                eprintln!("[Rust] Failed to parse SSE JSON: {}", e);
                                eprintln!("[Rust] Raw JSON: {}", json_str);
                            }
                        }
                    }
                }
            }
            Err(e) => {
                eprintln!("[Rust] SSE stream error: {}", e);
                break;
            }
        }
    }

    println!("[Rust] SSE stream ended, attempting to reconnect...");
    tokio::time::sleep(Duration::from_secs(5)).await;
    Box::pin(poll_assistant_status(app_handle, state)).await;
}

async fn handle_polling(client: reqwest::Client, mut current_port: String, app_handle: AppHandle, state: Arc<Mutex<OverlayState>>) {
    println!("[Rust] Using polling mode");

    loop {
        sleep(Duration::from_millis(500)).await;

        let poll_url = format!("http://localhost:{}/api/status", current_port);
        match client.get(&poll_url).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    match response.json::<serde_json::Value>().await {
                        Ok(data) => {
                            process_status_data(data, app_handle.clone(), state.clone()).await;
                        }
                        Err(e) => {
                            eprintln!("[Rust] Failed to parse JSON response: {}", e);
                        }
                    }
                } else {
                    eprintln!("[Rust] Status endpoint returned error: {}", response.status());
                }
            }
            Err(e) => {
                eprintln!("[Rust] Failed to connect to status endpoint on port {}: {}. Trying other ports...", current_port, e);

                // Try the other port if connection fails
                for test_port in &["5000", "5001"] {
                    if test_port != &current_port {
                        let test_url = format!("http://localhost:{}/api/status", test_port);
                        if let Ok(response) = client.get(&test_url).send().await {
                            if response.status().is_success() {
                                eprintln!("[Rust] Successfully connected to port {}, switching...", test_port);
                                current_port = test_port.to_string();
                                break;
                            }
                        }
                    }
                }
            }
        }
    }
}

async fn process_status_data(data: serde_json::Value, app_handle: AppHandle, state: Arc<Mutex<OverlayState>>) {
    println!("[Rust] Processing status data: {}", data);
    let mut state_guard = state.lock().unwrap();
    let window = app_handle.get_window("main").unwrap();

    // Extract data from JSON
    let status = data.get("status").and_then(|v| v.as_str()).unwrap_or("Unknown").to_string();
    let current_text = data.get("text").and_then(|v| v.as_str()).unwrap_or("").to_string();
    let is_listening = data.get("is_listening").and_then(|v| v.as_bool()).unwrap_or(false);
    let is_speaking = data.get("is_speaking").and_then(|v| v.as_bool()).unwrap_or(false);
    let wake_word_detected = data.get("wake_word_detected").and_then(|v| v.as_bool()).unwrap_or(false);
    let overlay_visible = data.get("overlay_visible").and_then(|v| v.as_bool()).unwrap_or(false);

    // Enhanced visibility logic
    let has_activity = wake_word_detected || is_speaking || is_listening;
    let has_meaningful_content = !current_text.is_empty() && current_text != "Listening..." && current_text != "Offline";
    let should_be_visible = has_activity || has_meaningful_content || overlay_visible;

    // Interactive mode logic - only when actively listening
    let should_be_interactive = is_listening && should_be_visible;

    let mut changed = false;
    if state_guard.text != current_text ||
        state_guard.is_listening != is_listening ||
        state_guard.is_speaking != is_speaking ||
        state_guard.wake_word_detected != wake_word_detected ||
        state_guard.visible != should_be_visible ||
        state_guard.interactive_mode != should_be_interactive
    {
        changed = true;
    }

    if changed {
        println!("[Rust] Status update: listening={}, speaking={}, wake_word={}, text='{}', visible={}, interactive={}",
                is_listening, is_speaking, wake_word_detected, current_text, should_be_visible, should_be_interactive);

        state_guard.status = status.clone();
        state_guard.text = current_text.clone();
        state_guard.is_listening = is_listening;
        state_guard.is_speaking = is_speaking;
        state_guard.wake_word_detected = wake_word_detected;

        // Update interactive mode and click-through settings
        if should_be_interactive != state_guard.interactive_mode {
            state_guard.interactive_mode = should_be_interactive;
            println!("[Rust] Setting interactive mode: {}", should_be_interactive);
            set_click_through(&window, !should_be_interactive);
        }

        // Show/hide window based on calculated visibility
        if should_be_visible && !state_guard.visible {
            println!("[Rust] Showing overlay window");
            window.show().unwrap_or_else(|e| eprintln!("Failed to show window: {}", e));
            state_guard.visible = true;
            // Ensure proper click-through when showing
            set_click_through(&window, !should_be_interactive);
        } else if !should_be_visible && state_guard.visible {
            println!("[Rust] Hiding overlay window");
            window.hide().unwrap_or_else(|e| eprintln!("Failed to hide window: {}", e));
            state_guard.visible = false;
            state_guard.interactive_mode = false;
        }

        // Emit status update to frontend
        let payload = StatusUpdate {
            status: status.clone(),
            text: state_guard.text.clone(),
            is_listening: state_guard.is_listening,
            is_speaking: state_guard.is_speaking,
            wake_word_detected: state_guard.wake_word_detected,
        };
        window.emit("status-update", payload).unwrap_or_else(|e| {
            eprintln!("Failed to emit status-update: {}", e);
        });
        state_guard.last_activity_time = Instant::now();
    }

    // Auto-hide logic - more conservative
    if state_guard.visible && state_guard.last_activity_time.elapsed() > Duration::from_secs(30)
        && current_text.is_empty() && !is_listening && !is_speaking && !wake_word_detected && !overlay_visible {
        if window.is_visible().unwrap_or(false) {
            println!("[Rust] Auto-hiding window due to prolonged inactivity and no relevant status.");
            window.hide().unwrap_or_else(|e| eprintln!("Failed to hide window: {}", e));
            state_guard.visible = false;
            state_guard.interactive_mode = false;
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let state = Arc::new(Mutex::new(OverlayState::new()));

    let app_result = tauri::Builder::default()
        .manage(state.clone())
        .setup(move |app| {
            let main_window = app.get_window("main").unwrap();
            let app_handle = app.handle();
            let state_clone_for_poll = state.clone();

            // Get primary monitor and set window to its size and position
            match main_window.primary_monitor() {
                Ok(Some(monitor)) => {
                    main_window.set_size(monitor.size().to_logical::<u32>(monitor.scale_factor())).unwrap_or_else(|e| eprintln!("Failed to set window size: {}",e));
                    main_window.set_position(monitor.position().to_logical::<i32>(monitor.scale_factor())).unwrap_or_else(|e| eprintln!("Failed to set window position: {}",e));
                    println!("Overlay set to primary monitor: {:?}", monitor.name());
                }
                Ok(None) => {
                    eprintln!("Could not get primary monitor info.");
                }
                Err(e) => {
                    eprintln!("Error getting primary monitor: {}", e);
                }
            }

            // Apply comprehensive click-through settings
            set_click_through_comprehensive(&main_window, true);

            // Start overlay hidden initially
            main_window.hide().unwrap_or_else(|e| eprintln!("Failed to hide window initially: {}", e));
            println!("[Rust] Overlay started and hidden, waiting for client status updates");

            tauri::async_runtime::spawn(async move {
                poll_assistant_status(app_handle, state_clone_for_poll).await;
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            show_overlay,
            hide_overlay,
            update_status,
            get_state
        ])
        .on_window_event(|event| {
            match event.event() {
                WindowEvent::Focused(focused) => {
                    if !focused {
                        // When losing focus, ensure click-through is enabled
                        set_click_through(event.window(), true);
                    }
                }
                WindowEvent::CloseRequested { api, .. } => {
                    // Allow normal exit
                    println!("[Rust] Window close requested");
                }
                _ => {}
            }
        })
        .build(tauri::generate_context!());

    match app_result {
        Ok(app) => {
            app.run(|_app_handle, event| match event {
                tauri::RunEvent::ExitRequested { api: _, .. } => {
                    println!("[Rust] Exit requested, shutting down overlay...");
                }
                _ => {}
            });
        }
        Err(e) => {
            eprintln!("Failed to build Tauri application: {}", e);
        }
    }
}

fn set_click_through(window: &Window, click_through: bool) {
    #[cfg(target_os = "windows")]
    {
        use windows_sys::Win32::UI::WindowsAndMessaging::{
            WS_EX_TRANSPARENT, WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW,
            GWL_EXSTYLE, SetWindowLongPtrW, GetWindowLongPtrW
        };

        match get_hwnd(window) {
            Ok(hwnd) => {
                if hwnd == 0 {
                    eprintln!("Invalid HWND for click-through setup");
                    return;
                }
                unsafe {
                    let ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
                    if click_through {
                        let new_style = ex_style | WS_EX_TRANSPARENT as isize | WS_EX_LAYERED as isize | WS_EX_NOACTIVATE as isize;
                        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_style);
                        println!("[Rust] Applied click-through mode");
                    } else {
                        let new_style = (ex_style & !(WS_EX_TRANSPARENT as isize)) | WS_EX_LAYERED as isize;
                        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_style);
                        println!("[Rust] Applied interactive mode");
                    }
                }
            }
            Err(e) => {
                eprintln!("Could not get HWND for set_click_through: {}", e);
            }
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        println!("Click-through not implemented for this OS");
    }
}

fn set_click_through_comprehensive(window: &Window, click_through: bool) {
    #[cfg(target_os = "windows")]
    {
        use windows_sys::Win32::UI::WindowsAndMessaging::{
            WS_EX_TRANSPARENT, WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW,
            GWL_EXSTYLE, SetWindowLongPtrW, GetWindowLongPtrW,
            SetWindowPos, HWND_TOPMOST, SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE
        };

        match get_hwnd(window) {
            Ok(hwnd) => {
                if hwnd == 0 {
                    eprintln!("Invalid HWND for comprehensive click-through setup");
                    return;
                }
                unsafe {
                    let ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
                    if click_through {
                        // Comprehensive click-through setup
                        let new_style = ex_style |
                            WS_EX_TRANSPARENT as isize |
                            WS_EX_LAYERED as isize |
                            WS_EX_NOACTIVATE as isize |
                            WS_EX_TOOLWINDOW as isize;
                        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_style);

                        // Set proper window positioning
                        SetWindowPos(
                            hwnd,
                            HWND_TOPMOST,
                            0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
                        );

                        println!("[Rust] Applied comprehensive click-through mode");
                    } else {
                        // Interactive mode - remove only WS_EX_TRANSPARENT
                        let new_style = (ex_style & !(WS_EX_TRANSPARENT as isize)) | WS_EX_LAYERED as isize;
                        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, new_style);
                        println!("[Rust] Applied comprehensive interactive mode");
                    }
                }
            }
            Err(e) => {
                eprintln!("Could not get HWND for comprehensive click-through: {}", e);
            }
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        println!("Comprehensive click-through not implemented for this OS");
    }
}

// Helper function to extract HWND
#[cfg(target_os = "windows")]
fn get_hwnd(window: &Window) -> Result<windows_sys::Win32::Foundation::HWND, String> {
    use windows_sys::Win32::Foundation::HWND;
    let handle = window.raw_window_handle();
    match handle {
        RawWindowHandle::Win32(win_handle) => Ok(win_handle.hwnd as HWND),
        _ => Err("Unsupported window handle type. Expected Win32 handle.".to_string()),
    }
}

fn main() {
    run();
}
