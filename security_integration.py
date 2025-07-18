"""Security Integration System Integrates all security modules into the main
application."""
import logging
import sys
from pathlib import Path
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from secure_config import SecureConfigLoader
from server.auth.security import SecurityManager
from server.database.secure_database import DatabaseEncryption
from server.security.input_validator import SecurityValidator
from server.security.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SecurityIntegration:
    """Main security integration system."""

    def __init__(self, config_path: str = "config.json"):
        self.config_loader = SecureConfigLoader(config_path)
        self.config = None
        self.security_manager = None
        self.db_encryption = None
        self.input_validator = None
        self.rate_limiter = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize all security systems."""
        try:
            logger.info("Initializing security integration system...")

            # Load secure configuration
            self.config = self.config_loader.load_config()
            logger.info("✅ Secure configuration loaded")

            # Initialize security manager
            self.security_manager = SecurityManager()
            logger.info("✅ Security manager initialized")

            # Initialize database encryption
            self.db_encryption = DatabaseEncryption()
            logger.info("✅ Database encryption initialized")

            # Initialize input validator
            self.input_validator = SecurityValidator()
            logger.info("✅ Input validator initialized")

            # Initialize rate limiter
            self.rate_limiter = RateLimiter()
            logger.info("✅ Rate limiter initialized")

            self._initialized = True
            logger.info("🔒 Security integration system initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize security system: {e}")
            return False

    def get_security_status(self) -> dict[str, Any]:
        """Get current security status."""
        if not self._initialized:
            return {"status": "not_initialized", "components": {}}

        status = {
            "status": "initialized",
            "components": {
                "config_loader": bool(self.config),
                "security_manager": bool(self.security_manager),
                "db_encryption": bool(self.db_encryption),
                "input_validator": bool(self.input_validator),
                "rate_limiter": bool(self.rate_limiter),
            },
            "api_keys_secured": self._check_api_keys_secured(),
            "database_encrypted": self._check_database_encryption(),
            "rate_limiting_active": self._check_rate_limiting(),
        }

        return status

    def _check_api_keys_secured(self) -> bool:
        """Check if API keys are properly secured."""
        if not self.config:
            return False

        api_keys = self.config.get("API_KEYS", {})
        for key, value in api_keys.items():
            if key == "_comment":
                continue
            # Check if value is environment variable placeholder
            if value and not value.startswith("${"):
                return False

        return True

    def _check_database_encryption(self) -> bool:
        """Check if database encryption is available."""
        return bool(self.db_encryption)

    def _check_rate_limiting(self) -> bool:
        """Check if rate limiting is active."""
        return bool(self.rate_limiter)

    def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate input data."""
        if not self.input_validator:
            raise RuntimeError("Input validator not initialized")

        return self.input_validator.validate_request_data(data)

    def authenticate_user(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate user with security manager."""
        if not self.security_manager:
            raise RuntimeError("Security manager not initialized")

        return self.security_manager.authenticate_user(username, password)

    def create_user(self, username: str, password: str, role: str = "user") -> bool:
        """Create new user with security manager."""
        if not self.security_manager:
            raise RuntimeError("Security manager not initialized")

        return self.security_manager.create_user(username, password, role)

    def check_rate_limit(self, identifier: str, endpoint: str) -> bool:
        """Check rate limit for identifier."""
        if not self.rate_limiter:
            raise RuntimeError("Rate limiter not initialized")

        return self.rate_limiter.check_rate_limit(identifier, endpoint)

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        if not self.db_encryption:
            raise RuntimeError("Database encryption not initialized")

        return self.db_encryption.encrypt_data(data)

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        if not self.db_encryption:
            raise RuntimeError("Database encryption not initialized")

        return self.db_encryption.decrypt_data(encrypted_data)

    def get_api_key(self, provider: str) -> str:
        """Get API key for provider (from environment)"""
        from secure_config import get_api_key

        return get_api_key(provider)

    def shutdown(self):
        """Shutdown security systems."""
        logger.info("Shutting down security integration system...")

        if self.rate_limiter:
            # Clean up rate limiter if needed
            pass

        if self.security_manager:
            # Clean up security manager if needed
            pass

        self._initialized = False
        logger.info("🔒 Security integration system shutdown complete")


# Global security instance
_security_integration = None


def get_security_integration() -> SecurityIntegration:
    """Get global security integration instance."""
    global _security_integration
    if _security_integration is None:
        _security_integration = SecurityIntegration()
    return _security_integration


def initialize_security() -> bool:
    """Initialize security integration."""
    security = get_security_integration()
    return security.initialize()


def get_security_status() -> dict[str, Any]:
    """Get security status."""
    security = get_security_integration()
    return security.get_security_status()


def main():
    """Test security integration."""
    logging.basicConfig(level=logging.INFO)

    print("🔒 Testing Security Integration System...")

    # Initialize security
    success = initialize_security()
    if not success:
        print("❌ Security initialization failed")
        return

    # Get status
    status = get_security_status()
    print(f"📊 Security Status: {status}")

    print("✅ Security integration test complete")


if __name__ == "__main__":
    main()
