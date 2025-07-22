# GAJA Client

This folder contains the client-side components of the GAJA Assistant system.

## Main Files

- `client_main.py` - Main client entry point and application logic
- `client_config.json` - Client configuration settings
- `requirements_client.txt` - Client-specific Python dependencies

## Supporting Modules

- `active_window_module.py` - Active window detection functionality
- `config.py` - Configuration management
- `shared_state.py` - Shared state management between components
- `list_audio_devices.py` - Audio device enumeration utility

## Folders

- `audio_modules/` - Audio processing and speech recognition modules
- `configs/` - Configuration files
- `logs/` - Client log files
- `overlay/` - UI overlay components (Tauri-based)
- `resources/` - Static resources and assets
- `user_data/` - User-specific data and settings

## Usage

Run the client with:
```bash
python client_main.py
```

Make sure to configure the client settings in `client_config.json` before first use.
