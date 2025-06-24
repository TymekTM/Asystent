// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, AppHandle, Window, WindowEvent, SystemTray, SystemTrayEvent, SystemTrayMenu, SystemTrayMenuItem, CustomMenuItem, WindowBuilder, WindowUrl};
use tokio::time::sleep;
use std::sync::{Arc, Mutex};
use serde::{Deserialize, Serialize};
use raw_window_handle::{HasRawWindowHandle, RawWindowHandle}; // Added HasRawWindowHandle
use std::time::{Instant, Duration};
use futures_util::StreamExt;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioDevice {
    id: String,
    name: String,
    is_default: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioDevices {
    input_devices: Vec<AudioDevice>,
    output_devices: Vec<AudioDevice>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Settings {
    audio: AudioSettings,
    voice: VoiceSettings,
    overlay: OverlaySettings,
    daily_briefing: DailyBriefingSettings,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioSettings {
    input_device: Option<String>,
    output_device: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceSettings {
    wake_word: String,
    sensitivity: f32,
    language: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverlaySettings {
    enabled: bool,
    position: String,
    opacity: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DailyBriefingSettings {
    enabled: bool,
    startup_briefing: bool,
    briefing_time: String,
    location: String,
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            audio: AudioSettings {
                input_device: None,
                output_device: None,
            },
            voice: VoiceSettings {
                wake_word: "gaja".to_string(),
                sensitivity: 0.6,
                language: "pl-PL".to_string(),
            },
            overlay: OverlaySettings {
                enabled: true,
                position: "top-right".to_string(),
                opacity: 0.9,
            },
            daily_briefing: DailyBriefingSettings {
                enabled: true,
                startup_briefing: true,
                briefing_time: "08:00".to_string(),
                location: "Sosnowiec,PL".to_string(),
            },
        }
    }
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

#[tauri::command]
async fn open_settings(app_handle: AppHandle) -> Result<(), String> {
    println!("[Rust] open_settings called");
    // Check if settings window already exists
    if let Some(settings_window) = app_handle.get_window("settings") {
        println!("[Rust] Settings window exists, showing it");
        settings_window.show().map_err(|e| e.to_string())?;
        settings_window.set_focus().map_err(|e| e.to_string())?;
    } else {
        println!("[Rust] Creating new settings window");
        // Create new settings window
        let _settings_window = tauri::WindowBuilder::new(
            &app_handle,
            "settings",
            tauri::WindowUrl::App("settings.html".into())
        )
        .title("Gaja - Ustawienia")
        .inner_size(800.0, 600.0)
        .min_inner_size(600.0, 400.0)
        .center()
        .resizable(true)
        .decorations(true)
        .transparent(false)
        .always_on_top(false)
        .skip_taskbar(false)
        .initialization_script(
            r#"
            console.log('[Tauri] Initializing Tauri API in settings window...');
            console.log('[Tauri] window.__TAURI__ available:', !!window.__TAURI__);
            if (window.__TAURI__) {
                console.log('[Tauri] Tauri API successfully loaded');
            } else {
                console.error('[Tauri] Tauri API not available!');
            }
            "#
        )
        .build()
        .map_err(|e| {
            println!("[Rust] Error creating settings window: {}", e);
            e.to_string()
        })?;
        println!("[Rust] Settings window created successfully");
    }
    Ok(())
}

#[tauri::command]
async fn close_settings(app_handle: AppHandle) -> Result<(), String> {
    if let Some(settings_window) = app_handle.get_window("settings") {
        settings_window.close().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
async fn get_audio_devices() -> Result<AudioDevices, String> {
    // On Windows, we can use WinAPI to enumerate audio devices
    // For now, we'll provide mock data but this could be enhanced with cpal or windows crate
    let input_devices = vec![
        AudioDevice {
            id: "default_input".to_string(),
            name: "Domyślne urządzenie wejściowe".to_string(),
            is_default: true,
        },
        AudioDevice {
            id: "microphone_array".to_string(),
            name: "Mikrofon (zintegrowany)".to_string(),
            is_default: false,
        },
        AudioDevice {
            id: "usb_microphone".to_string(),
            name: "Mikrofon USB".to_string(),
            is_default: false,
        },
        AudioDevice {
            id: "headset_microphone".to_string(),
            name: "Mikrofon słuchawkowy".to_string(),
            is_default: false,
        },
    ];

    let output_devices = vec![
        AudioDevice {
            id: "default_output".to_string(),
            name: "Domyślne urządzenie wyjściowe".to_string(),
            is_default: true,
        },
        AudioDevice {
            id: "speakers_builtin".to_string(),
            name: "Głośniki (zintegrowane)".to_string(),
            is_default: false,
        },
        AudioDevice {
            id: "headphones".to_string(),
            name: "Słuchawki".to_string(),
            is_default: false,
        },
        AudioDevice {
            id: "bluetooth_speaker".to_string(),
            name: "Głośnik Bluetooth".to_string(),
            is_default: false,
        },
    ];

    Ok(AudioDevices {
        input_devices,
        output_devices,
    })
}

fn get_settings_path() -> Result<std::path::PathBuf, String> {
    let exe_dir = std::env::current_exe()
        .map_err(|e| format!("Nie można znaleźć katalogu aplikacji: {}", e))?
        .parent()
        .ok_or("Nie można znaleźć katalogu nadrzędnego")?
        .to_path_buf();

    Ok(exe_dir.join("overlay_settings.json"))
}

fn load_settings() -> Result<Settings, String> {
    let settings_path = get_settings_path()?;

    if settings_path.exists() {
        let content = fs::read_to_string(&settings_path)
            .map_err(|e| format!("Nie można odczytać pliku ustawień: {}", e))?;

        serde_json::from_str(&content)
            .map_err(|e| format!("Błąd parsowania ustawień: {}", e))
    } else {
        Ok(Settings::default())
    }
}

#[tauri::command]
async fn get_connection_status() -> Result<serde_json::Value, String> {
    println!("[Rust] get_connection_status called");
    let client = reqwest::Client::new();
    let ports = vec!["5000", "5001"];

    for port in &ports {
        let test_url = format!("http://localhost:{}/api/status", port);
        println!("[Rust] Testing connection to: {}", test_url);

        match client.get(&test_url).send().await {
            Ok(response) => {
                println!("[Rust] Response status: {}", response.status());
                if response.status().is_success() {
                    match response.json::<serde_json::Value>().await {
                        Ok(json) => {
                            println!("[Rust] Server response: {}", json);
                            return Ok(serde_json::json!({
                                "connected": true,
                                "port": port,
                                "server_status": json
                            }));
                        }
                        Err(e) => {
                            println!("[Rust] JSON parse error: {}", e);
                            continue;
                        }
                    }
                }
            }
            Err(e) => {
                println!("[Rust] Connection error to {}: {}", test_url, e);
                continue;
            }
        }
    }

    println!("[Rust] No server found on any port");
    Ok(serde_json::json!({
        "connected": false,
        "error": "Nie można połączyć się z serwerem Gaja"
    }))
}

#[tauri::command]
async fn get_current_settings() -> Result<Settings, String> {
    load_settings()
}

#[tauri::command]
async fn save_settings(settings: Settings) -> Result<(), String> {
    let settings_path = get_settings_path()?;

    // Create directory if it doesn't exist
    if let Some(parent) = settings_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("Nie można utworzyć katalogu ustawień: {}", e))?;
    }

    let json_content = serde_json::to_string_pretty(&settings)
        .map_err(|e| format!("Błąd serializacji ustawień: {}", e))?;

    fs::write(&settings_path, json_content)
        .map_err(|e| format!("Nie można zapisać ustawień: {}", e))?;

    println!("Ustawienia zapisane do: {:?}", settings_path);
    Ok(())
}

async fn poll_assistant_status(app_handle: AppHandle, state: Arc<Mutex<OverlayState>>) {
    let client = reqwest::Client::new();
    let ports = vec!["5000", "5001"]; // Try both ports
    let mut working_port = None;

    // First, find which port is working
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

    // Try to establish SSE connection
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
    println!("[Rust] Using polling mode");

    loop {
        sleep(Duration::from_millis(500)).await; // Poll every 500ms

        let poll_url = format!("http://localhost:{}/api/status", current_port);        match client.get(&poll_url).send().await {
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

    // Enhanced visibility logic - show overlay when there's activity OR when explicitly set visible
    let has_activity = wake_word_detected || is_speaking || is_listening;
    let has_meaningful_content = !current_text.is_empty() && current_text != "Listening..." && current_text != "Offline";
    let should_be_visible = has_activity || has_meaningful_content || overlay_visible;

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
        println!("[Rust] Status update: listening={}, speaking={}, wake_word={}, text='{}', visible={}, overlay_visible_flag={}",
                is_listening, is_speaking, wake_word_detected, current_text, should_be_visible, overlay_visible);

        state_guard.status = status.clone();
        state_guard.text = current_text.clone();
        state_guard.is_listening = is_listening;
        state_guard.is_speaking = is_speaking;
        state_guard.wake_word_detected = wake_word_detected;

        // Show/hide window based on calculated visibility
        if should_be_visible && !state_guard.visible {
            println!("[Rust] Showing overlay window");
            window.show().unwrap_or_else(|e| eprintln!("Failed to show window: {}", e));
            state_guard.visible = true;
        } else if !should_be_visible && state_guard.visible {
            println!("[Rust] Hiding overlay window");
            window.hide().unwrap_or_else(|e| eprintln!("Failed to hide window: {}", e));
            state_guard.visible = false;
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

    // Auto-hide logic - only hide after longer period and when truly inactive
    if state_guard.visible && state_guard.last_activity_time.elapsed() > Duration::from_secs(30)
        && current_text.is_empty() && !is_listening && !is_speaking && !wake_word_detected && !overlay_visible {
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

    // Create system tray menu
    let tray_menu = SystemTrayMenu::new()
        .add_item(CustomMenuItem::new("settings".to_string(), "Ustawienia"))
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(CustomMenuItem::new("show".to_string(), "Pokaż overlay"))
        .add_item(CustomMenuItem::new("hide".to_string(), "Ukryj overlay"))
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(CustomMenuItem::new("quit".to_string(), "Zakończ"));

    let system_tray = SystemTray::new()
        .with_menu(tray_menu)
        .with_tooltip("Gaja - Asystent AI");

    let app_result = tauri::Builder::default()
        .manage(state.clone())
        .system_tray(system_tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::LeftClick {
                position: _,
                size: _,
                ..
            } => {
                println!("System tray left click");
            }
            SystemTrayEvent::RightClick {
                position: _,
                size: _,
                ..
            } => {
                println!("System tray right click");
            }
            SystemTrayEvent::DoubleClick {
                position: _,
                size: _,
                ..
            } => {
                // Double click opens settings
                let app_handle = app.clone();
                tauri::async_runtime::spawn(async move {
                    let _ = open_settings(app_handle).await;
                });
            }
            SystemTrayEvent::MenuItemClick { id, .. } => {
                match id.as_str() {
                    "settings" => {
                        let app_handle = app.clone();
                        tauri::async_runtime::spawn(async move {
                            let _ = open_settings(app_handle).await;
                        });
                    }
                    "show" => {
                        if let Some(window) = app.get_window("main") {
                            let _ = window.show();
                        }
                    }
                    "hide" => {
                        if let Some(window) = app.get_window("main") {
                            let _ = window.hide();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                }
            }
            _ => {}
        })
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

            // Start overlay hidden initially - will be shown when client sends status
            main_window.hide().unwrap_or_else(|e| eprintln!("Failed to hide window initially: {}", e));
            println!("[Rust] Overlay started and hidden, waiting for client status updates");

            tauri::async_runtime::spawn(async move {
                poll_assistant_status(app_handle, state_clone_for_poll).await;
            });

            Ok(())
        })        .invoke_handler(tauri::generate_handler![
            show_overlay,
            hide_overlay,
            update_status,
            get_state,
            open_settings,
            close_settings,
            get_audio_devices,
            get_current_settings,
            get_connection_status,
            save_settings,
            debug_log
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
        })        .build(tauri::generate_context!());

    match app_result {
        Ok(app) => {
            app.run(|_app_handle, event| match event {
                tauri::RunEvent::ExitRequested { api, .. } => {
                    // Allow normal exit when client closes - don't prevent it
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

#[tauri::command]
async fn debug_log(message: String) -> Result<(), String> {
    println!("[Rust] JS Debug: {}", message);
    Ok(())
}
