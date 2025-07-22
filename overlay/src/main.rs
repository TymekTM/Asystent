// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, AppHandle, Window, WindowEvent}; // Removed SystemTray, SystemTrayEvent
use tokio::time::sleep;
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use raw_window_handle::{HasRawWindowHandle, RawWindowHandle}; // Added HasRawWindowHandle
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

#[derive(Debug, Deserialize, Clone)] // Added Clone
struct AssistantStatusResponse {
    status: String,
    text: Option<String>,
    message: Option<String>, // For compatibility with potential variations
    // Add other fields if your Python server sends more, e.g.,
    // is_listening: Option<bool>,
    // is_speaking: Option<bool>,
    // wake_word_detected: Option<bool>,
}

#[derive(Debug, Clone, Serialize)] // Added Clone and Serialize
pub struct OverlayState {
    visible: bool,
    status: String,
    text: String,
    is_listening: bool,
    is_speaking: bool,
    wake_word_detected: bool,
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
    Ok(())
}

#[tauri::command]
async fn hide_overlay(window: Window, state: tauri::State<'_, SharedState>) -> Result<(), String> {
    window.hide().map_err(|e| e.to_string())?;
    {
        let mut overlay_state = state.lock().unwrap();
        overlay_state.visible = false;
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
fn get_state(state: tauri::State<Arc<Mutex<OverlayState>>>) -> Result<OverlayState, String> { // Ensure State is tauri::State
    Ok(state.inner().lock().unwrap().clone())
}

async fn poll_assistant_status(app_handle: AppHandle, state: Arc<Mutex<OverlayState>>) {
    let client = reqwest::Client::new();
    // ONLY try client ports - NEVER connect to main server (8001)
    let ports = vec!["5001", "5000"];
    let mut working_port = None;

    // First, find which port is working
    for port in &ports {
        let test_url = format!("http://localhost:{}/api/status", port);
        println!("[Rust] Testing connection to CLIENT port {}", port);
        match client.get(&test_url).timeout(std::time::Duration::from_secs(2)).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    working_port = Some(port.to_string());
                    println!("[Rust] Found working CLIENT port: {}", port);
                    break;
                } else {
                    println!("[Rust] Client port {} returned status: {}", port, response.status());
                }
            }
            Err(e) => {
                println!("[Rust] Client port {} connection failed: {}", port, e);
            }
        }
    }

    let current_port = working_port.clone().unwrap_or_else(|| {
        println!("[Rust] No CLIENT connection found, using fallback port 5001");
        std::env::var("GAJA_PORT").unwrap_or_else(|_| {
            "5001".to_string() // Always default to client port, never server port
        })
    });

    // Show connection status in UI
    {
        let mut state_guard = state.lock().unwrap();
        if working_port.is_some() {
            state_guard.status = format!("Connected to CLIENT port {}", current_port);
        } else {
            state_guard.status = "Waiting for client...".to_string();
        }
    }

    // Try SSE first, fallback to polling if not available
    let sse_url = format!("http://localhost:{}/status/stream", current_port);

    println!("[Rust] Attempting to connect to SSE stream: {}", sse_url);

    // Try to establish SSE connection
    match client.get(&sse_url).timeout(std::time::Duration::from_secs(5)).send().await {
        Ok(response) => {
            if response.status().is_success() {
                println!("[Rust] Successfully connected to SSE stream");
                handle_sse_stream(response, app_handle.clone(), state.clone()).await;
            } else {
                println!("[Rust] SSE not available (status: {}), falling back to polling", response.status());
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
                        let json_str = &message[6..]; // Remove "data: " prefix
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
    // Reconnect after a delay
    tokio::time::sleep(Duration::from_secs(5)).await;
    Box::pin(poll_assistant_status(app_handle, state)).await;
}

async fn handle_polling(client: reqwest::Client, mut current_port: String, app_handle: AppHandle, state: Arc<Mutex<OverlayState>>) {
    println!("[Rust] Using polling mode on CLIENT port {}", current_port);

    loop {
        sleep(Duration::from_millis(1000)).await; // Poll every 1 second

        let poll_url = format!("http://localhost:{}/api/status", current_port);
        match client.get(&poll_url).timeout(Duration::from_secs(3)).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    match response.json::<serde_json::Value>().await {
                        Ok(data) => {
                            // Update connection status
                            {
                                let mut state_guard = state.lock().unwrap();
                                state_guard.status = format!("Connected to CLIENT port {}", current_port);
                            }
                            process_status_data(data, app_handle.clone(), state.clone()).await;
                        }
                        Err(e) => {
                            eprintln!("[Rust] Failed to parse JSON response: {}", e);
                        }
                    }
                } else {
                    eprintln!("[Rust] CLIENT status endpoint returned error: {}", response.status());
                }
            }
            Err(e) => {
                println!("[Rust] Failed to connect to CLIENT port {}: {}", current_port, e);

                // Update UI to show waiting for client
                {
                    let mut state_guard = state.lock().unwrap();
                    state_guard.status = "Waiting for client to start...".to_string();
                    state_guard.text = "Start the Gaja client first".to_string();
                }

                // Try only client ports if connection fails
                for test_port in &["5001", "5000"] {
                    if test_port != &current_port {
                        let test_url = format!("http://localhost:{}/api/status", test_port);
                        if let Ok(response) = client.get(&test_url).timeout(Duration::from_secs(2)).send().await {
                            if response.status().is_success() {
                                println!("[Rust] Successfully reconnected to CLIENT port {}, switching...", test_port);
                                current_port = test_port.to_string();
                                break;
                            }
                        }
                    }
                }

                // Wait longer before retrying when no client available
                sleep(Duration::from_secs(10)).await;
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

    // More generous visibility logic - keep overlay visible if there's any activity or recent text
    let has_activity = wake_word_detected || is_speaking || is_listening;
    let has_content = !current_text.is_empty();
    let should_be_visible = has_activity || has_content;

    let mut changed = false;
    if state_guard.text != current_text ||
        state_guard.is_listening != is_listening ||
        state_guard.is_speaking != is_speaking ||
        state_guard.wake_word_detected != wake_word_detected ||
        state_guard.visible != should_be_visible
    {
        changed = true;
    }

    if changed {
        println!("[Rust] Status update: listening={}, speaking={}, wake_word={}, text='{}', visible={}",
                is_listening, is_speaking, wake_word_detected, current_text, should_be_visible);

        state_guard.status = status.clone();
        state_guard.text = current_text.clone();
        state_guard.is_listening = is_listening;
        state_guard.is_speaking = is_speaking;
        state_guard.wake_word_detected = wake_word_detected;

        if should_be_visible && !state_guard.visible {
            window.show().unwrap_or_else(|e| eprintln!("Failed to show window: {}", e));
            state_guard.visible = true;
        }
        state_guard.visible = should_be_visible;        // Emit status update to frontend
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
    }    // Auto-hide logic - only hide after longer period and when truly inactive
    if state_guard.visible && state_guard.last_activity_time.elapsed() > Duration::from_secs(30)
        && current_text.is_empty() && !is_listening && !is_speaking && !wake_word_detected {
        if window.is_visible().unwrap_or(false) {
            println!("[Rust] Auto-hiding window due to prolonged inactivity and no relevant status.");
            window.hide().unwrap_or_else(|e| eprintln!("Failed to hide window: {}", e));
            state_guard.visible = false;
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
            match main_window.primary_monitor() { // Changed from app.get_primary_monitor()
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
            }            set_click_through(&main_window, true);

            // Force show window for debugging
            main_window.show().unwrap_or_else(|e| eprintln!("Failed to show window: {}", e));
            // Remove focus call to prevent window from stealing focus
            // main_window.set_focus().unwrap_or_else(|e| eprintln!("Failed to focus window: {}", e));

            tauri::async_runtime::spawn(async move {
                poll_assistant_status(app_handle, state_clone_for_poll).await;
            });

            Ok(())
        })        .invoke_handler(tauri::generate_handler![
            show_overlay,
            hide_overlay,
            update_status,
            get_state
        ])
        .on_window_event(|event| {
            match event.event() {
                WindowEvent::Focused(focused) => {
                    if !focused {
                        // set_click_through(event.window(), true);
                    }
                }
                WindowEvent::CloseRequested { api: _api, .. } => { // Silenced unused api
                    // event.window().hide().unwrap();
                    // _api.prevent_close();
                }
                _ => {}
            }
        })
        .build(tauri::generate_context!());

    match app_result {
        Ok(app) => {
            app.run(|_app_handle, event| match event {
                tauri::RunEvent::ExitRequested { api, .. } => {
                    api.prevent_exit();
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
            WS_EX_TRANSPARENT, WS_EX_LAYERED, GWL_EXSTYLE, SetWindowLongPtrW, GetWindowLongPtrW
        };
        // HWND import is now in get_hwnd

        match get_hwnd(window) { // Call renamed helper
            Ok(hwnd) => {
                if hwnd == 0 {
                    eprintln!("Invalid HWND for click-through setup");
                    return;
                }
                unsafe {
                    let ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
                    if click_through {
                        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_TRANSPARENT as isize | WS_EX_LAYERED as isize);
                    } else {
                        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style & !(WS_EX_TRANSPARENT as isize) & !(WS_EX_LAYERED as isize));
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

// Helper function to extract HWND
#[cfg(target_os = "windows")]
fn get_hwnd(window: &Window) -> Result<windows_sys::Win32::Foundation::HWND, String> {
    use windows_sys::Win32::Foundation::HWND; // Import HWND here
    let handle = window.raw_window_handle(); // Assuming this returns RawWindowHandle directly
    match handle {
        RawWindowHandle::Win32(win_handle) => Ok(win_handle.hwnd as HWND),
        _ => Err("Unsupported window handle type. Expected Win32 handle.".to_string()),
    }
}

// main function to call run
fn main() {
    run();
}
