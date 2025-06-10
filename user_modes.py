"""
GAJA Assistant User Modes System
Zarządzanie różnymi trybami użytkownika: Poor Man, Paid User, Enterprise
"""

import json
import logging
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class UserMode(Enum):
    """Dostępne tryby użytkownika."""
    POOR_MAN = "poor_man"
    PAID_USER = "paid_user" 
    ENTERPRISE = "enterprise"

class TTSProvider(Enum):
    """Dostępni dostawcy TTS."""
    EDGE_TTS = "edge_tts"  # Free Microsoft Edge TTS
    OPENAI_TTS = "openai_tts"  # OpenAI TTS API
    AZURE_TTS = "azure_tts"  # Azure Cognitive Services
    LOCAL_TTS = "local_tts"  # Local TTS engine

class WhisperProvider(Enum):
    """Dostępni dostawcy Whisper."""
    LOCAL_WHISPER = "local_whisper"  # Local Whisper models
    OPENAI_WHISPER = "openai_whisper"  # OpenAI Whisper API
    AZURE_WHISPER = "azure_whisper"  # Azure Speech Services

@dataclass
class ModeConfig:
    """Konfiguracja trybu użytkownika."""
    name: str
    display_name: str
    description: str
    tts_provider: TTSProvider
    whisper_provider: WhisperProvider
    max_requests_per_hour: int
    features: Dict[str, bool]
    pricing: Dict[str, Any]
    tts_config: Dict[str, Any]
    whisper_config: Dict[str, Any]

class UserModeManager:
    """Zarządza trybami użytkownika i ich konfiguracją."""
    
    def __init__(self, config_path: str = "configs/user_modes.json"):
        self.config_path = Path(config_path)
        self.modes: Dict[UserMode, ModeConfig] = {}
        self.current_mode: Optional[UserMode] = None
        self._initialize_default_modes()
        self._load_config()
    
    def _initialize_default_modes(self):
        """Inicjalizuje domyślne tryby użytkownika."""
        
        # Poor Man Mode - darmowy, lokalny
        self.modes[UserMode.POOR_MAN] = ModeConfig(
            name="poor_man",
            display_name="Poor Man Mode",
            description="Darmowy tryb z lokalnymi narzędziami - Edge TTS + lokalny Whisper",
            tts_provider=TTSProvider.EDGE_TTS,
            whisper_provider=WhisperProvider.LOCAL_WHISPER,
            max_requests_per_hour=100,
            features={
                "voice_commands": True,
                "tts_response": True,
                "web_ui": True,
                "overlay": True,
                "advanced_memory": False,
                "cloud_backup": False,
                "premium_voices": False,
                "real_time_transcription": False
            },
            pricing={
                "monthly_cost": 0,
                "currency": "USD",
                "billing_type": "free"
            },
            tts_config={
                "voice": "pl-PL-MarekNeural",  # Polski głos męski
                "rate": "+0%",
                "volume": "+0%",
                "pitch": "+0Hz",
                "cleanup_temp_files": True,
                "cleanup_interval": 10
            },
            whisper_config={
                "model_size": "base",  # Dynamiczny dobór: tiny, base, small, medium
                "language": "pl",
                "auto_detect_language": True,
                "dynamic_model_selection": True,
                "fallback_models": ["tiny", "base", "small"],
                "max_model_size": "small"  # Ograniczenie dla Poor Man Mode
            }
        )
        
        # Paid User Mode - API-based
        self.modes[UserMode.PAID_USER] = ModeConfig(
            name="paid_user", 
            display_name="Paid User Mode",
            description="Tryb płatny z OpenAI APIs - lepsza jakość i więcej funkcji",
            tts_provider=TTSProvider.OPENAI_TTS,
            whisper_provider=WhisperProvider.OPENAI_WHISPER,
            max_requests_per_hour=500,
            features={
                "voice_commands": True,
                "tts_response": True,
                "web_ui": True,
                "overlay": True,
                "advanced_memory": True,
                "cloud_backup": True,
                "premium_voices": True,
                "real_time_transcription": True,
                "custom_voice_training": False,
                "multi_language_support": True
            },
            pricing={
                "monthly_cost": 20,
                "currency": "USD", 
                "billing_type": "subscription",
                "api_costs": "pay_per_use"
            },
            tts_config={
                "model": "tts-1",
                "voice": "alloy",  # OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
                "response_format": "mp3",
                "speed": 1.0
            },
            whisper_config={
                "model": "whisper-1",
                "language": "pl",
                "response_format": "json",
                "temperature": 0.0
            }
        )
        
        # Enterprise Mode - pełna funkcjonalność
        self.modes[UserMode.ENTERPRISE] = ModeConfig(
            name="enterprise",
            display_name="Enterprise Mode", 
            description="Tryb korporacyjny z pełną funkcjonalnością i wsparciem",
            tts_provider=TTSProvider.AZURE_TTS,
            whisper_provider=WhisperProvider.AZURE_WHISPER,
            max_requests_per_hour=10000,
            features={
                "voice_commands": True,
                "tts_response": True,
                "web_ui": True,
                "overlay": True,
                "advanced_memory": True,
                "cloud_backup": True,
                "premium_voices": True,
                "real_time_transcription": True,
                "custom_voice_training": True,
                "multi_language_support": True,
                "user_management": True,
                "audit_logs": True,
                "sso_integration": True,
                "on_premise_deployment": True
            },
            pricing={
                "monthly_cost": 100,
                "currency": "USD",
                "billing_type": "enterprise",
                "support_included": True
            },
            tts_config={
                "region": "eastus",
                "voice": "pl-PL-MarekNeural",
                "style": "friendly",
                "rate": "medium",
                "volume": "medium"
            },
            whisper_config={
                "region": "eastus", 
                "language": "pl-PL",
                "profanity_filter": True,
                "add_punctuation": True
            }
        )
    
    def _load_config(self):
        """Ładuje konfigurację z pliku."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_mode = UserMode(data.get('current_mode', UserMode.POOR_MAN.value))
                    logger.info(f"Loaded user mode configuration: {self.current_mode.value}")
            except Exception as e:
                logger.error(f"Error loading user mode config: {e}")
                self.current_mode = UserMode.POOR_MAN
        else:
            self.current_mode = UserMode.POOR_MAN
            self._save_config()
    
    def _save_config(self):
        """Zapisuje konfigurację do pliku."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'current_mode': self.current_mode.value if self.current_mode else UserMode.POOR_MAN.value,
                'last_updated': str(Path(__file__).stat().st_mtime)
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving user mode config: {e}")
    
    def get_current_mode(self) -> UserMode:
        """Zwraca aktualny tryb użytkownika."""
        return self.current_mode or UserMode.POOR_MAN
    
    def get_mode_config(self, mode: UserMode = None) -> ModeConfig:
        """Zwraca konfigurację dla podanego trybu (lub aktualnego)."""
        target_mode = mode or self.get_current_mode()
        return self.modes.get(target_mode, self.modes[UserMode.POOR_MAN])
    
    def set_mode(self, mode: UserMode) -> bool:
        """Ustawia nowy tryb użytkownika."""
        if mode in self.modes:
            self.current_mode = mode
            self._save_config()
            logger.info(f"User mode changed to: {mode.value}")
            return True
        else:
            logger.error(f"Invalid user mode: {mode}")
            return False
    
    def get_available_modes(self) -> Dict[UserMode, ModeConfig]:
        """Zwraca wszystkie dostępne tryby."""
        return self.modes.copy()
    
    def has_feature(self, feature: str, mode: UserMode = None) -> bool:
        """Sprawdza czy dany tryb ma określoną funkcję."""
        config = self.get_mode_config(mode)
        return config.features.get(feature, False)
    
    def get_limits(self, mode: UserMode = None) -> Dict[str, Any]:
        """Zwraca limity dla danego trybu."""
        config = self.get_mode_config(mode)
        return {
            "max_requests_per_hour": config.max_requests_per_hour,
            "features": config.features,
            "pricing": config.pricing
        }

# Global instance
user_mode_manager = UserModeManager()

def get_current_mode() -> UserMode:
    """Convenience function to get current mode."""
    return user_mode_manager.get_current_mode()

def get_current_config() -> ModeConfig:
    """Convenience function to get current mode config."""
    return user_mode_manager.get_mode_config()

def has_feature(feature: str) -> bool:
    """Convenience function to check if current mode has feature."""
    return user_mode_manager.has_feature(feature)
