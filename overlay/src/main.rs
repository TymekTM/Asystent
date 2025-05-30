// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, Window, WindowEvent, AppHandle}; // Removed Runtime
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use raw_window_handle::HasRawWindowHandle; // Ensure this is in scope

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct OverlayState {
    pub visible: bool,
    pub status: String,
    pub text: String,
    pub is_listening: bool,
    pub is_speaking: bool,
    pub wake_word_detected: bool,
}

impl Default for OverlayState {
    fn default() -> Self {
        Self {
            visible: false,
            status: "idle".to_string(),
            text: "".to_string(),
            is_listening: false,
            is_speaking: false,
            wake_word_detected: false,
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
async fn get_state(state: tauri::State<'_, SharedState>) -> Result<OverlayState, String> {
    let overlay_state = state.lock().unwrap();
    Ok(overlay_state.clone())
}

async fn poll_assistant_status(window: Window, _state: SharedState, _app_handle: AppHandle) {
    let client = reqwest::Client::new();
    let mut last_shown_status = (false, false, false, String::new()); // is_listening, is_speaking, wake_word_detected, current_text

    loop {
        match client.get("http://localhost:5001/api/status").send().await {
            Ok(response) => {
                if response.status().is_success() {
                    match response.json::<serde_json::Value>().await {
                        Ok(status_data) => {
                            eprintln!("[Rust] Received status data: {:?}", status_data);

                            let python_status_str = status_data.get("status").and_then(|s| s.as_str()).unwrap_or("").to_lowercase();
                            eprintln!("[Rust] Parsed Python status string: '{}'", python_status_str);

                            let is_listening = python_status_str == "listening" || python_status_str == "recording" || python_status_str == "stt_working";
                            let is_speaking = python_status_str == "speaking" || python_status_str == "tts_speaking";
                            let wake_word_detected = python_status_str == "wakeworddetected" || python_status_str == "active";
                            
                            // Try to get current text from a few common field names
                            let current_text = status_data.get("current_response")
                                .or_else(|| status_data.get("message"))
                                .or_else(|| status_data.get("text"))
                                .and_then(|v| v.as_str())
                                .unwrap_or("").to_string();

                            eprintln!("[Rust] Parsed values: listening={}, speaking={}, wake_word={}, text='{}'", is_listening, is_speaking, wake_word_detected, current_text);

                            let current_status = (is_listening, is_speaking, wake_word_detected, current_text.clone());

                            if current_status != last_shown_status {
                                let status_str = if is_listening {
                                    "listening"
                                } else if is_speaking {
                                    "speaking"
                                } else if wake_word_detected {
                                    "wake_word_detected"
                                } else if !current_text.is_empty() {
                                    "displaying_text"
                                }
                                 else {
                                    "idle"
                                };
                                eprintln!("[Rust] Derived status_str: {}", status_str);

                                window.emit("status-update", {
                                    let mut payload = serde_json::Map::new();
                                    payload.insert("status".to_string(), serde_json::Value::String(status_str.to_string()));
                                    payload.insert("text".to_string(), serde_json::Value::String(current_text.clone()));
                                    payload.insert("is_listening".to_string(), serde_json::Value::Bool(is_listening));
                                    payload.insert("is_speaking".to_string(), serde_json::Value::Bool(is_speaking));
                                    payload.insert("wake_word_detected".to_string(), serde_json::Value::Bool(wake_word_detected));
                                    payload
                                }).unwrap_or_else(|e| eprintln!("[Rust] Error emitting status-update: {}", e));

                                if is_listening || is_speaking || wake_word_detected || !current_text.is_empty() {
                                    if let Err(e) = window.show() {
                                        eprintln!("[Rust] Error showing window: {}", e);
                                    }
                                    eprintln!("[Rust] Window should be visible due to: listening={}, speaking={}, wake_word={}, text='{}'", is_listening, is_speaking, wake_word_detected, current_text);
                                } else {
                                    if let Err(e) = window.hide() {
                                        eprintln!("[Rust] Error hiding window: {}", e);
                                    }
                                    eprintln!("[Rust] Window should be hidden.");
                                }
                                last_shown_status = current_status;
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
                eprintln!("[Rust] Failed to connect to status endpoint (http://localhost:5001/api/status): {}. Is the Python server running?", e);
            }
        }
        // Poll every 500ms
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
    }
}

fn main() {
    let state = SharedState::default();

    tauri::Builder::default()
        .manage(state.clone()) 
        .invoke_handler(tauri::generate_handler![
            show_overlay,
            hide_overlay,
            update_status,
            get_state
        ])
        .setup(move |app| { // Added move here
            let window = app.get_window("main").unwrap();
            let app_handle = app.handle(); 
            
            window.set_always_on_top(true).unwrap();
            window.set_skip_taskbar(true).unwrap();

            // Attempt to show the window directly after setup
            println!("[Rust] Attempting to show window directly in setup...");
            window.show().expect("Failed to show window during setup");
            println!("[Rust] window.show() called in setup.");


            #[cfg(target_os = "windows")]
            {
                // Ensure HasRawWindowHandle is in scope for window.raw_window_handle()
                // The raw_window_handle method directly returns RawWindowHandle enum
                match window.raw_window_handle() { 
                    raw_window_handle::RawWindowHandle::Win32(win_handle) => {
                        unsafe {
                            use windows_sys::Win32::UI::WindowsAndMessaging::{
                                GetWindowLongW, SetWindowLongW, GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT, WS_EX_TOOLWINDOW
                            };
                            
                            let hwnd = win_handle.hwnd as isize;
                            let mut ex_style = GetWindowLongW(hwnd, GWL_EXSTYLE);
                            ex_style |= WS_EX_LAYERED as i32 | WS_EX_TRANSPARENT as i32 | WS_EX_TOOLWINDOW as i32;
                            SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style);
                        }
                    }
                    _ => {
                        eprintln!("Not a Win32 window handle or unsupported platform for this specific setup.");
                    }
                }
            }
            
            let state_clone_for_poll = state.clone(); // Clone state for the polling task
            let window_clone_for_poll = window.clone(); // Clone window for the polling task
            let app_handle_clone_for_poll = app_handle.clone(); // Clone app_handle for the polling task

            // Changed from tokio::spawn to tauri::async_runtime::spawn
            tauri::async_runtime::spawn(async move {
                poll_assistant_status(window_clone_for_poll, state_clone_for_poll, app_handle_clone_for_poll).await;
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|_app_handle, event| match event {
            tauri::RunEvent::WindowEvent {
                label,
                event: WindowEvent::CloseRequested { api, .. },
                ..
            } => {
                if label == "main" {
                    api.prevent_close(); // Prevent default close
                    // Optionally hide the window or do nothing, as it's an overlay
                    // let window = _app_handle.get_window("main").unwrap();
                    // window.hide().unwrap();
                    println!("Main window close requested, but prevented for overlay.");
                }
            }
            _ => {}
        });
}
