"""
User Mode Integrator
Integruje systemy trybów użytkownika, uwierzytelniania i komponentów audio
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

# Import our new systems
from user_modes import UserMode, get_current_mode, get_current_config, user_mode_manager
from auth_system import auth_manager, Permission, User, UserRole
from audio_modules.enhanced_tts_module import EnhancedTTSModule
from audio_modules.enhanced_whisper_asr import EnhancedWhisperASR

logger = logging.getLogger(__name__)

class UserModeIntegrator:
    """Integrator zarządzający trybami użytkownika i ich funkcjonalnościami."""
    
    def __init__(self):
        self.current_session_id: Optional[str] = None
        self.current_user: Optional[User] = None
        self.tts_module: Optional[EnhancedTTSModule] = None
        self.whisper_asr: Optional[EnhancedWhisperASR] = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicjalizuje komponenty audio na podstawie aktualnego trybu."""
        try:
            current_mode = get_current_mode()
            config = get_current_config()
            
            logger.info(f"Initializing components for mode: {current_mode.value}")
            
            # Initialize TTS module
            self.tts_module = EnhancedTTSModule()
            logger.info("Enhanced TTS module initialized")
            
            # Initialize Whisper ASR
            self.whisper_asr = EnhancedWhisperASR()
            logger.info("Enhanced Whisper ASR initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
    
    async def authenticate_and_setup(self, username: str, password: str, 
                                   ip_address: str = "", user_agent: str = "") -> Tuple[bool, str]:
        """Uwierzytelnia użytkownika i konfiguruje tryb."""
        try:
            # Authenticate user
            session_id = auth_manager.authenticate(username, password, ip_address, user_agent)
            
            if session_id is None:
                return False, "Authentication failed"
            
            # Validate session and get user
            user = auth_manager.validate_session(session_id)
            if user is None:
                return False, "Session validation failed"
            
            # Store session info
            self.current_session_id = session_id
            self.current_user = user
            
            # Determine and set user mode based on role and permissions
            user_mode = self._determine_user_mode(user)
            user_mode_manager.set_mode(user_mode)
            
            # Reinitialize components for new mode
            self._initialize_components()
            
            logger.info(f"User {user.username} authenticated and configured for {user_mode.value} mode")
            return True, f"Authenticated as {user.username} in {user_mode.value} mode"
            
        except Exception as e:
            logger.error(f"Error during authentication and setup: {e}")
            return False, f"Setup error: {str(e)}"
    
    def _determine_user_mode(self, user: User) -> UserMode:
        """Określa tryb użytkownika na podstawie roli i uprawnień."""
        # Map user roles to modes
        role_to_mode = {
            UserRole.GUEST: UserMode.POOR_MAN,
            UserRole.USER: UserMode.POOR_MAN,
            UserRole.PREMIUM: UserMode.PAID_USER,
            UserRole.ADMIN: UserMode.PAID_USER,
            UserRole.SUPER_ADMIN: UserMode.ENTERPRISE
        }
        
        # Check if user has specific premium permissions for upgrade
        if user.role in [UserRole.USER, UserRole.GUEST]:
            if Permission.USE_OPENAI_API in user.permissions:
                return UserMode.PAID_USER
        
        return role_to_mode.get(user.role, UserMode.POOR_MAN)
    
    def check_permission(self, permission: Permission) -> bool:
        """Sprawdza uprawnienia aktualnego użytkownika."""
        if self.current_session_id is None:
            return False
        
        return auth_manager.has_permission(self.current_session_id, permission)
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Zwraca informacje o aktualnym użytkowniku."""
        if self.current_user is None:
            return None
        
        current_mode = get_current_mode()
        config = get_current_config()
        
        return {
            "user_id": self.current_user.user_id,
            "username": self.current_user.username,
            "email": self.current_user.email,
            "role": self.current_user.role.value,
            "current_mode": current_mode.value,
            "mode_display_name": config.display_name,
            "permissions": [p.value for p in self.current_user.permissions],
            "features": config.features,
            "limits": {
                "max_requests_per_hour": config.max_requests_per_hour
            }
        }
    
    async def speak_text(self, text: str) -> bool:
        """Wypowiada tekst używając odpowiedniego dostawcy TTS."""
        try:
            # Check TTS permission
            if not self.check_permission(Permission.USE_TTS):
                logger.warning("User doesn't have TTS permission")
                return False
            
            if self.tts_module is None:
                logger.error("TTS module not initialized")
                return False
            
            await self.tts_module.speak(text)
            return True
            
        except Exception as e:
            logger.error(f"Error in speak_text: {e}")
            return False
    
    async def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        """Transkrybuje audio używając odpowiedniego dostawcy Whisper."""
        try:
            # Check voice commands permission
            if not self.check_permission(Permission.USE_VOICE_COMMANDS):
                logger.warning("User doesn't have voice commands permission")
                return None
            
            if self.whisper_asr is None:
                logger.error("Whisper ASR not initialized")
                return None
            
            result = await self.whisper_asr.transcribe(audio_file_path)
            return result
            
        except Exception as e:
            logger.error(f"Error in transcribe_audio: {e}")
            return None
    
    def get_available_features(self) -> Dict[str, bool]:
        """Zwraca dostępne funkcje dla aktualnego użytkownika."""
        if self.current_user is None:
            return {}
        
        config = get_current_config()
        user_permissions = self.current_user.permissions
        
        # Map permissions to features
        permission_feature_map = {
            Permission.USE_VOICE_COMMANDS: "voice_commands",
            Permission.USE_TTS: "tts_response", 
            Permission.USE_WEB_UI: "web_ui",
            Permission.USE_OVERLAY: "overlay",
            Permission.USE_ADVANCED_MEMORY: "advanced_memory",
            Permission.USE_CLOUD_BACKUP: "cloud_backup",
            Permission.USE_PREMIUM_VOICES: "premium_voices",
            Permission.USE_REAL_TIME_TRANSCRIPTION: "real_time_transcription",
            Permission.CUSTOM_VOICE_TRAINING: "custom_voice_training",
            Permission.MULTI_LANGUAGE_SUPPORT: "multi_language_support"
        }
        
        available_features = {}
        for permission, feature in permission_feature_map.items():
            available_features[feature] = (
                permission in user_permissions and 
                config.features.get(feature, False)
            )
        
        return available_features
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki użycia."""
        stats = {
            "current_mode": get_current_mode().value,
            "tts_provider": get_current_config().tts_provider.value,
            "whisper_provider": get_current_config().whisper_provider.value
        }
        
        # Add Whisper performance stats if available
        if self.whisper_asr:
            try:
                whisper_stats = self.whisper_asr.get_model_performance_stats()
                stats["whisper_performance"] = whisper_stats
            except Exception as e:
                logger.warning(f"Could not get Whisper stats: {e}")
        
        return stats
    
    async def switch_mode(self, new_mode: UserMode) -> Tuple[bool, str]:
        """Przełącza tryb użytkownika (jeśli ma uprawnienia)."""
        try:
            if self.current_user is None:
                return False, "No authenticated user"
            
            # Check if user can access the requested mode
            allowed_mode = self._determine_user_mode(self.current_user)
            mode_hierarchy = [UserMode.POOR_MAN, UserMode.PAID_USER, UserMode.ENTERPRISE]
            
            allowed_idx = mode_hierarchy.index(allowed_mode)
            requested_idx = mode_hierarchy.index(new_mode)
            
            if requested_idx > allowed_idx:
                return False, f"User role {self.current_user.role.value} cannot access {new_mode.value} mode"
            
            # Switch mode
            success = user_mode_manager.set_mode(new_mode)
            if success:
                # Reinitialize components
                self._initialize_components()
                logger.info(f"User {self.current_user.username} switched to {new_mode.value} mode")
                return True, f"Switched to {new_mode.value} mode"
            else:
                return False, "Failed to switch mode"
                
        except Exception as e:
            logger.error(f"Error switching mode: {e}")
            return False, f"Error: {str(e)}"
    
    def logout(self) -> bool:
        """Wylogowuje aktualnego użytkownika."""
        try:
            if self.current_session_id:
                success = auth_manager.logout(self.current_session_id)
                self.current_session_id = None
                self.current_user = None
                
                # Reset to Poor Man mode for security
                user_mode_manager.set_mode(UserMode.POOR_MAN)
                self._initialize_components()
                
                logger.info("User logged out successfully")
                return success
            return False
            
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            return False
    
    def get_mode_info(self) -> Dict[str, Any]:
        """Zwraca szczegółowe informacje o aktualnym trybie."""
        config = get_current_config()
        
        return {
            "name": config.name,
            "display_name": config.display_name,
            "description": config.description,
            "tts_provider": config.tts_provider.value,
            "whisper_provider": config.whisper_provider.value,
            "max_requests_per_hour": config.max_requests_per_hour,
            "features": config.features,
            "pricing": config.pricing,
            "tts_config": config.tts_config,
            "whisper_config": config.whisper_config
        }

# Global instance
user_integrator = UserModeIntegrator()

# Convenience functions for easy access
async def authenticate_user_and_setup(username: str, password: str, 
                                    ip_address: str = "", user_agent: str = "") -> Tuple[bool, str]:
    """Convenience function for authentication and setup."""
    return await user_integrator.authenticate_and_setup(username, password, ip_address, user_agent)

async def speak(text: str) -> bool:
    """Convenience function for TTS."""
    return await user_integrator.speak_text(text)

async def transcribe(audio_file_path: str) -> Optional[str]:
    """Convenience function for ASR."""
    return await user_integrator.transcribe_audio(audio_file_path)

def get_user_info() -> Optional[Dict[str, Any]]:
    """Convenience function for user info."""
    return user_integrator.get_user_info()

def check_permission(permission: Permission) -> bool:
    """Convenience function for permission checking."""
    return user_integrator.check_permission(permission)
