# GAJA Server

This folder contains the server-side components of the GAJA Assistant system.

## Main Files

- `server_main.py` - Main server entry point and application logic
- `server_config.json` - Server configuration settings
- `requirements_server.txt` - Server-specific Python dependencies

## Core Modules

- `ai_module.py` - AI integration and processing
- `advanced_memory_system.py` - Advanced memory management
- `function_calling_system.py` - Function calling and execution system
- `database_manager.py` - Database operations and management
- `database_models.py` - Database schema definitions
- `config_loader.py` - Configuration loading utilities

## Feature Modules

- `daily_briefing_module.py` - Daily briefing functionality
- `onboarding_module.py` - User onboarding system
- `performance_monitor.py` - System performance monitoring
- `plugin_manager.py` - Plugin system management
- `plugin_monitor.py` - Plugin monitoring and health checks
- `prompt_builder.py` - AI prompt construction
- `prompts.py` - Predefined prompts and templates

## Web Interface

- `webui.html` - Web-based user interface
- `extended_webui.py` - Extended web UI functionality
- `templates/` - Web UI templates

## Supporting Files

- `active_window_module.py` - Active window detection
- `__init__.py` - Package initialization

## Folders

- `modules/` - Functional modules (API, core, memory, music, search, weather, etc.)
- `configs/` - Configuration files
- `logs/` - Server log files
- `resources/` - Static resources and assets
- `user_data/` - User-specific data and settings

## Database Files

- `gaja_server.db` - Main server database
- `server_data.db` - Additional server data storage

## Documentation

- `DODANE_FUNKCJONALNOSCI.md` - Added functionalities documentation (Polish)

## Usage

Run the server with:
```bash
python server_main.py
```

Make sure to configure the server settings in `server_config.json` before first use.
