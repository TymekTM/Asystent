// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, AppHandle, Window, WindowEvent}; // Removed SystemTray, SystemTrayEvent
use tokio::time::sleep;
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use raw_window_handle::{HasRawWindowHandle, RawWindowHandle}; // Added HasRawWindowHandle
use std::time::{Instant, Duration};

#[derive(Clone, Serialize)]
struct StatusUpdate {
    #[serde(rename = "isVisible")]
    is_visible: bool,
    #[serde(rename = "statusText")]
    status_text: String,
    #[serde(rename = "isListening")]
    is_listening: bool,
    #[serde(rename = "isSpeaking")]
    is_speaking: bool,
    #[serde(rename = "wakeWordDetected")]
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
    let port = std::env::var("GAJA_PORT").unwrap_or_else(|_| {
        if cfg!(debug_assertions) { "5001".to_string() } else { "5000".to_string() }
    });
    let poll_url = format!("http://localhost:{}/api/status", port);

    loop {
        sleep(Duration::from_millis(200)).await; // Poll frequently but not too aggressively

        match client.get(poll_url).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    match response.json::<AssistantStatusResponse>().await {
                        Ok(data) => {
                            let mut state_guard = state.lock().unwrap();
                            let window = app_handle.get_window("main").unwrap();

                            // Extract text, prioritizing 'text' then 'message'
                            let current_text = data.text.or(data.message).unwrap_or_else(|| "".to_string());

                            // Determine flags based on status string
                            let status_lower = data.status.to_lowercase();
                            let mut wake_word_detected_flag = state_guard.wake_word_detected; // Persist unless explicitly changed
                            let mut is_listening_flag = state_guard.is_listening;
                            let mut is_speaking_flag = state_guard.is_speaking;

                            if status_lower.contains("wakeword") || status_lower.contains("detected") {
                                wake_word_detected_flag = true;
                                is_listening_flag = true; // Typically, wake word means listening starts
                                is_speaking_flag = false;
                            } else if status_lower.contains("listening") || status_lower.contains("recording") {
                                is_listening_flag = true;
                                wake_word_detected_flag = false; // Explicitly listening, not just wake word
                                is_speaking_flag = false;
                            } else if status_lower.contains("speaking") || status_lower.contains("processing") || status_lower.contains("thinking") {
                                is_speaking_flag = true;
                                is_listening_flag = false;
                                wake_word_detected_flag = false;
                            } else if status_lower.contains("idle") || status_lower.contains("online") || status_lower.contains("ready") {
                                // If assistant is idle/online but there's text, it might be a lingering message
                                if current_text.is_empty() {
                                    is_listening_flag = false;
                                    is_speaking_flag = false;
                                    wake_word_detected_flag = false;
                                }
                            } else if status_lower.contains("offline") || status_lower.contains("error") {
                                is_listening_flag = false;
                                is_speaking_flag = false;
                                wake_word_detected_flag = false;
                            }
                            // If there's text, we assume the assistant is "active" in some way (e.g. displaying a message)
                            // or speaking.
                            if !current_text.is_empty() {
                                is_speaking_flag = true; // Or some other appropriate flag to show text
                            }


                            let should_be_visible = wake_word_detected_flag || is_speaking_flag || is_listening_flag || !current_text.is_empty();

                            let mut changed = false;
                            if state_guard.text != current_text || // Use state_guard.text
                                state_guard.is_listening != is_listening_flag ||
                                state_guard.is_speaking != is_speaking_flag ||
                                state_guard.wake_word_detected != wake_word_detected_flag ||
                                state_guard.visible != should_be_visible
                            {
                                changed = true;
                            }

                            if changed {
                                state_guard.status = data.status.clone();
                                state_guard.text = current_text.clone(); // Use state_guard.text
                                state_guard.is_listening = is_listening_flag;
                                state_guard.is_speaking = is_speaking_flag;
                                state_guard.wake_word_detected = wake_word_detected_flag;

                                if should_be_visible && !state_guard.visible {
                                    // Before showing, make it click-through if it's not already (might be redundant if set on setup)
                                    // set_click_through(&window, true);
                                    window.show().unwrap_or_else(|e| eprintln!("Failed to show window: {}", e));
                                    state_guard.visible = true;
                                    // Set focus to allow interaction if needed, then remove if it should be purely an overlay
                                    // window.set_focus().unwrap_or_else(|e| eprintln!("Failed to focus window: {}", e));
                                }
                                state_guard.visible = should_be_visible; // Update visibility state

                                // Emit status update to frontend
                                let payload = StatusUpdate {
                                    is_visible: state_guard.visible,
                                    status_text: state_guard.text.clone(),
                                    is_listening: state_guard.is_listening,
                                    is_speaking: state_guard.is_speaking,
                                    wake_word_detected: state_guard.wake_word_detected,
                                };
                                window.emit("status-update", payload).unwrap_or_else(|e| {
                                    eprintln!("Failed to emit status-update: {}", e);
                                });
                                state_guard.last_activity_time = Instant::now();
                            }

                            if state_guard.visible && state_guard.last_activity_time.elapsed() > Duration::from_secs(10) && current_text.is_empty() && !is_listening_flag && !is_speaking_flag && !wake_word_detected_flag {
                                if !current_text.is_empty() {
                                     // If there's still text, don't hide, reset timer
                                     state_guard.last_activity_time = Instant::now();
                                } else if window.is_visible().unwrap_or(false) {
                                    // Check if there's any reason to stay visible based on flags
                                    if !state_guard.is_listening && !state_guard.is_speaking && !state_guard.wake_word_detected && state_guard.text.is_empty() {
                                        println!("Auto-hiding window due to inactivity and no relevant status.");
                                        window.hide().unwrap_or_else(|e| eprintln!("Failed to hide window: {}", e));
                                        state_guard.visible = false;
                                    } else {
                                        // Still active, reset timer
                                        state_guard.last_activity_time = Instant::now();
                                    }
                                }
                            }
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
                eprintln!("[Rust] Failed to connect to status endpoint ({}): {}. Is the Python server running?", poll_url, e);
            }
        }
        // Poll every 500ms
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
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
            }

            set_click_through(&main_window, true);

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
