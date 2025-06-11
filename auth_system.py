"""
Advanced User Authentication and Role Management System
Zaawansowany system uwierzytelniania i zarządzania rolami użytkowników
"""

import hashlib
import secrets
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, asdict, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """Role użytkowników w systemie."""
    GUEST = "guest"
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class Permission(Enum):
    """Uprawnienia w systemie."""
    # Basic permissions
    USE_VOICE_COMMANDS = "use_voice_commands"
    USE_TTS = "use_tts"
    USE_WEB_UI = "use_web_ui"
    USE_OVERLAY = "use_overlay"
    
    # Advanced features
    USE_ADVANCED_MEMORY = "use_advanced_memory"
    USE_CLOUD_BACKUP = "use_cloud_backup"
    USE_PREMIUM_VOICES = "use_premium_voices"
    USE_REAL_TIME_TRANSCRIPTION = "use_real_time_transcription"
    CUSTOM_VOICE_TRAINING = "custom_voice_training"
    MULTI_LANGUAGE_SUPPORT = "multi_language_support"
    
    # API and integrations
    USE_OPENAI_API = "use_openai_api"
    USE_AZURE_API = "use_azure_api"
    API_ACCESS = "api_access"
    WEBHOOK_ACCESS = "webhook_access"
    
    # Administrative
    USER_MANAGEMENT = "user_management"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    SYSTEM_CONFIGURATION = "system_configuration"
    PLUGIN_MANAGEMENT = "plugin_management"
    
    # Enterprise features
    SSO_INTEGRATION = "sso_integration"
    ON_PREMISE_DEPLOYMENT = "on_premise_deployment"
    ADVANCED_ANALYTICS = "advanced_analytics"

@dataclass
class UserSession:
    """Sesja użytkownika."""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    ip_address: str = ""
    user_agent: str = ""
    is_active: bool = True

@dataclass
class User:
    """Użytkownik systemu."""
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    role: UserRole
    permissions: Set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje użytkownika do słownika."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions],
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "metadata": self.metadata
        }

class AuthenticationManager:
    """Zarządza uwierzytelnianiem i sesjami użytkowników."""
    
    def __init__(self, config_path: str = "configs/auth_config.json"):
        self.config_path = Path(config_path)
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.role_permissions: Dict[UserRole, Set[Permission]] = {}
        self.session_timeout = timedelta(hours=24)
        self.max_failed_attempts = 5
        self.lockout_duration = timedelta(minutes=30)
        self.failed_attempts: Dict[str, Dict[str, Any]] = {}
        
        self._initialize_role_permissions()
        self._load_config()
        self._create_default_admin()
    
    def _initialize_role_permissions(self):
        """Inicjalizuje domyślne uprawnienia dla ról."""
        
        # Guest - tylko podstawowe funkcje
        self.role_permissions[UserRole.GUEST] = {
            Permission.USE_VOICE_COMMANDS,
            Permission.USE_TTS,
            Permission.USE_OVERLAY
        }
        
        # User - podstawowe funkcje + web UI
        self.role_permissions[UserRole.USER] = {
            Permission.USE_VOICE_COMMANDS,
            Permission.USE_TTS,
            Permission.USE_WEB_UI,
            Permission.USE_OVERLAY
        }
        
        # Premium - wszystkie funkcje użytkownika + zaawansowane
        self.role_permissions[UserRole.PREMIUM] = {
            Permission.USE_VOICE_COMMANDS,
            Permission.USE_TTS,
            Permission.USE_WEB_UI,
            Permission.USE_OVERLAY,
            Permission.USE_ADVANCED_MEMORY,
            Permission.USE_CLOUD_BACKUP,
            Permission.USE_PREMIUM_VOICES,
            Permission.USE_REAL_TIME_TRANSCRIPTION,
            Permission.CUSTOM_VOICE_TRAINING,
            Permission.MULTI_LANGUAGE_SUPPORT,
            Permission.USE_OPENAI_API,
            Permission.API_ACCESS
        }
        
        # Admin - wszystkie funkcje premium + zarządzanie
        self.role_permissions[UserRole.ADMIN] = self.role_permissions[UserRole.PREMIUM] | {
            Permission.USER_MANAGEMENT,
            Permission.VIEW_AUDIT_LOGS,
            Permission.PLUGIN_MANAGEMENT,
            Permission.USE_AZURE_API,
            Permission.WEBHOOK_ACCESS
        }
        
        # Super Admin - wszystkie uprawnienia
        self.role_permissions[UserRole.SUPER_ADMIN] = set(Permission)
    
    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """Hashuje hasło z solą."""
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 for secure password hashing
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        ).hex()
        
        return password_hash, salt
    
    def _verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Weryfikuje hasło."""
        computed_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(computed_hash, password_hash)
    
    def _generate_session_id(self) -> str:
        """Generuje unikalny ID sesji."""
        return secrets.token_urlsafe(32)
    
    def _is_account_locked(self, identifier: str) -> bool:
        """Sprawdza czy konto jest zablokowane."""
        if identifier not in self.failed_attempts:
            return False
        
        attempts = self.failed_attempts[identifier]
        if attempts['count'] >= self.max_failed_attempts:
            lockout_time = datetime.fromisoformat(attempts['lockout_until'])
            return datetime.now() < lockout_time
        
        return False
    
    def _record_failed_attempt(self, identifier: str):
        """Rejestruje nieudaną próbę logowania."""
        now = datetime.now()
        
        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = {
                'count': 0,
                'first_attempt': now.isoformat(),
                'lockout_until': None
            }
        
        self.failed_attempts[identifier]['count'] += 1
        
        if self.failed_attempts[identifier]['count'] >= self.max_failed_attempts:
            lockout_until = now + self.lockout_duration
            self.failed_attempts[identifier]['lockout_until'] = lockout_until.isoformat()
            logger.warning(f"Account {identifier} locked until {lockout_until}")
    
    def _clear_failed_attempts(self, identifier: str):
        """Czyści nieudane próby logowania."""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]
    
    def _load_config(self):
        """Ładuje konfigurację z pliku."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load users
                for user_data in data.get('users', []):
                    permissions = {Permission(p) for p in user_data.get('permissions', [])}
                    user = User(
                        user_id=user_data['user_id'],
                        username=user_data['username'],
                        email=user_data['email'],
                        password_hash=user_data['password_hash'],
                        salt=user_data['salt'],
                        role=UserRole(user_data['role']),
                        permissions=permissions,
                        created_at=datetime.fromisoformat(user_data['created_at']),
                        last_login=datetime.fromisoformat(user_data['last_login']) if user_data.get('last_login') else None,
                        is_active=user_data.get('is_active', True),
                        metadata=user_data.get('metadata', {})
                    )
                    self.users[user.user_id] = user
                
                # Load failed attempts
                self.failed_attempts = data.get('failed_attempts', {})
                
                logger.info(f"Loaded {len(self.users)} users from config")
                
            except Exception as e:
                logger.error(f"Error loading auth config: {e}")
    
    def _save_config(self):
        """Zapisuje konfigurację do pliku."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'users': [
                    {
                        'user_id': user.user_id,
                        'username': user.username,
                        'email': user.email,
                        'password_hash': user.password_hash,
                        'salt': user.salt,
                        'role': user.role.value,
                        'permissions': [p.value for p in user.permissions],
                        'created_at': user.created_at.isoformat(),
                        'last_login': user.last_login.isoformat() if user.last_login else None,
                        'is_active': user.is_active,
                        'metadata': user.metadata
                    }
                    for user in self.users.values()
                ],
                'failed_attempts': self.failed_attempts,
                'last_updated': datetime.now().isoformat()
            }            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)            
        except Exception as e:
            logger.error(f"Error saving auth config: {e}")
    
    def _create_default_admin(self):
        """Tworzy domyślnego administratora jeśli nie istnieje."""
        admin_exists = any(user.role == UserRole.SUPER_ADMIN for user in self.users.values())
        
        if not admin_exists:
            admin_id = "admin_" + secrets.token_hex(8)
            
            # Generate a secure random password instead of using a default
            secure_password = secrets.token_urlsafe(20)  # 160-bit security
            password_hash, salt = self._hash_password(secure_password)
            
            admin = User(
                user_id=admin_id,
                username="admin",
                email="admin@gaja.local",
                password_hash=password_hash,
                salt=salt,
                role=UserRole.SUPER_ADMIN,
                permissions=self.role_permissions[UserRole.SUPER_ADMIN].copy()
            )
            
            self.users[admin_id] = admin
            self._save_config()
            
            logger.critical("="*80)
            logger.critical("DEFAULT ADMIN ACCOUNT CREATED")
            logger.critical(f"Username: admin")
            logger.critical(f"Password: {secure_password}")
            logger.critical("SAVE THIS PASSWORD IMMEDIATELY!")
            logger.critical("This password will not be shown again.")
            logger.critical("="*80)
            
            # Also save to a secure file that only admin can read
            try:
                admin_creds_file = Path("admin_credentials.txt")
                admin_creds_file.write_text(
                    f"GAJA Assistant - Default Admin Credentials\n"
                    f"Created: {datetime.now().isoformat()}\n"
                    f"Username: admin\n"
                    f"Password: {secure_password}\n\n"
                    f"IMPORTANT: Change this password immediately after first login!\n"
                    f"Delete this file after saving the credentials securely.\n"
                )
                # Set secure permissions (Unix/Linux only)
                try:
                    admin_creds_file.chmod(0o600)  # Read only for owner
                except OSError:
                    # Windows - use alternative approach
                    import stat
                    admin_creds_file.chmod(stat.S_IREAD | stat.S_IWRITE)
                logger.critical(f"Credentials also saved to: {admin_creds_file.absolute()}")
            except Exception as e:
                logger.error(f"Failed to save admin credentials to file: {e}")
    
    def create_user(self, username: str, email: str, password: str, role: UserRole = UserRole.USER) -> Optional[str]:
        """Tworzy nowego użytkownika."""
        try:
            # Check if username or email already exists
            for user in self.users.values():
                if user.username == username:
                    logger.error(f"Username {username} already exists")
                    return None
                if user.email == email:
                    logger.error(f"Email {email} already exists")
                    return None
            
            # Create new user
            user_id = "user_" + secrets.token_hex(8)
            password_hash, salt = self._hash_password(password)
            
            user = User(
                user_id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                salt=salt,
                role=role,
                permissions=self.role_permissions[role].copy()
            )
            
            self.users[user_id] = user
            self._save_config()
            
            logger.info(f"Created new user: {username} ({role.value})")
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def authenticate(self, username: str, password: str, ip_address: str = "", user_agent: str = "") -> Optional[str]:
        """Uwierzytelnia użytkownika i tworzy sesję."""
        try:
            # Check if account is locked
            if self._is_account_locked(username):
                logger.warning(f"Authentication attempt for locked account: {username}")
                return None
            
            # Find user by username or email
            user = None
            for u in self.users.values():
                if u.username == username or u.email == username:
                    user = u
                    break
            
            if user is None or not user.is_active:
                self._record_failed_attempt(username)
                logger.warning(f"Authentication failed: User not found or inactive: {username}")
                return None
            
            # Verify password
            if not self._verify_password(password, user.password_hash, user.salt):
                self._record_failed_attempt(username)
                logger.warning(f"Authentication failed: Invalid password for {username}")
                return None
            
            # Clear failed attempts on successful login
            self._clear_failed_attempts(username)
            
            # Update last login
            user.last_login = datetime.now()
            
            # Create session
            session_id = self._generate_session_id()
            session = UserSession(
                session_id=session_id,
                user_id=user.user_id,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.sessions[session_id] = session
            self._save_config()
            
            logger.info(f"User {username} authenticated successfully")
            return session_id
            
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return None
    
    def validate_session(self, session_id: str) -> Optional[User]:
        """Waliduje sesję i zwraca użytkownika."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is active
        if not session.is_active:
            return None
        
        # Check session timeout
        if datetime.now() - session.last_activity > self.session_timeout:
            session.is_active = False
            logger.info(f"Session {session_id} expired")
            return None
        
        # Update last activity
        session.last_activity = datetime.now()
        
        # Return user
        return self.users.get(session.user_id)
    
    def logout(self, session_id: str) -> bool:
        """Wylogowuje użytkownika."""
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            logger.info(f"User logged out, session: {session_id}")
            return True
        return False
    
    def has_permission(self, session_id: str, permission: Permission) -> bool:
        """Sprawdza czy użytkownik ma określone uprawnienie."""
        user = self.validate_session(session_id)
        if user is None:
            return False
        
        return permission in user.permissions
    
    def get_user_permissions(self, session_id: str) -> Set[Permission]:
        """Zwraca uprawnienia użytkownika."""
        user = self.validate_session(session_id)
        if user is None:
            return set()
        
        return user.permissions.copy()
    
    def update_user_role(self, user_id: str, new_role: UserRole, admin_session_id: str) -> bool:
        """Aktualizuje rolę użytkownika (wymaga uprawnień administratora)."""
        admin_user = self.validate_session(admin_session_id)
        if admin_user is None or not self.has_permission(admin_session_id, Permission.USER_MANAGEMENT):
            logger.warning("Unauthorized attempt to update user role")
            return False
        
        if user_id not in self.users:
            logger.error(f"User {user_id} not found")
            return False
        
        user = self.users[user_id]
        old_role = user.role
        user.role = new_role
        user.permissions = self.role_permissions[new_role].copy()
        
        self._save_config()
        logger.info(f"User {user.username} role updated from {old_role.value} to {new_role.value}")
        return True
    
    def get_all_users(self, admin_session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Zwraca listę wszystkich użytkowników (wymaga uprawnień administratora)."""
        admin_user = self.validate_session(admin_session_id)
        if admin_user is None or not self.has_permission(admin_session_id, Permission.USER_MANAGEMENT):
            logger.warning("Unauthorized attempt to list users")
            return None
        
        return [user.to_dict() for user in self.users.values()]
    
    def cleanup_expired_sessions(self):
        """Czyści wygasłe sesje."""
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if datetime.now() - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

# Global instance
auth_manager = AuthenticationManager()

# Convenience functions
def authenticate_user(username: str, password: str, ip_address: str = "", user_agent: str = "") -> Optional[str]:
    """Convenience function for authentication."""
    return auth_manager.authenticate(username, password, ip_address, user_agent)

def validate_session(session_id: str) -> Optional[User]:
    """Convenience function for session validation."""
    return auth_manager.validate_session(session_id)

def has_permission(session_id: str, permission: Permission) -> bool:
    """Convenience function for permission checking."""
    return auth_manager.has_permission(session_id, permission)

def logout_user(session_id: str) -> bool:
    """Convenience function for logout."""
    return auth_manager.logout(session_id)
