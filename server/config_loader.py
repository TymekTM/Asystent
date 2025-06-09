"""
config_loader.py
Uproszczony loader konfiguracji dla serwera
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def load_config(config_file: str = "server_config.json") -> Dict[str, Any]:
    """
    Ładuje konfigurację z pliku JSON.
    
    Args:
        config_file: Nazwa pliku konfiguracyjnego
        
    Returns:
        Dict z konfiguracją
    """
    config_path = Path(config_file)
    
    # Jeśli plik nie istnieje, utwórz domyślną konfigurację
    if not config_path.exists():
        logger.warning(f"Config file {config_file} not found, creating default")
        default_config = create_default_config()
        save_config(default_config, config_file)
        return default_config
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Error loading config {config_file}: {e}")
        return create_default_config()

def save_config(config: Dict[str, Any], config_file: str = "server_config.json"):
    """Zapisuje konfigurację do pliku."""
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved configuration to {config_file}")
    except Exception as e:
        logger.error(f"Error saving config {config_file}: {e}")

def create_default_config() -> Dict[str, Any]:
    """Tworzy domyślną konfigurację serwera."""
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 8000,
            "debug": False
        },
        "database": {
            "url": "sqlite:///./server_data.db",
            "echo": False
        },        "ai": {
            "provider": "openai",
            "model": "gpt-4.1-nano",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        "api_keys": {
            "openai": "YOUR_OPENAI_API_KEY_HERE",
            "anthropic": "YOUR_ANTHROPIC_API_KEY_HERE"
        },
        "plugins": {
            "auto_load": True,
            "default_enabled": ["weather_module", "search_module"]
        },
        "logging": {
            "level": "INFO",
            "file": "logs/server_{time:YYYY-MM-DD}.log"
        }
    }

# Stare zmienne dla kompatybilności
_config = load_config()
STT_MODEL = _config.get("ai", {}).get("stt_model", "base")
MAIN_MODEL = _config.get("ai", {}).get("model", "gpt-4.1-nano")
PROVIDER = _config.get("ai", {}).get("provider", "openai")
DEEP_MODEL = _config.get("ai", {}).get("deep_model", "gpt-4.1-nano")
