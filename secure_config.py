"""
Secure Configuration Loader
Handles safe loading of configuration with environment variable substitution
"""
import os
import json
import re
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class SecureConfigLoader:
    """Secure configuration loader with environment variable support"""
    
    def __init__(self, config_path: str = None, env_path: str = None):
        self.config_path = config_path or "config.json"
        self.env_path = env_path or ".env"
        self._load_environment()
    
    def _load_environment(self):
        """Load environment variables from .env file"""
        if Path(self.env_path).exists():
            load_dotenv(self.env_path)
            logger.info(f"Loaded environment variables from {self.env_path}")
        else:
            logger.warning(f"Environment file {self.env_path} not found")
    
    def load_config(self) -> Dict[str, Any]:
        """Load and parse configuration with environment variable substitution"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_text = f.read()
            
            # Substitute environment variables
            config_text = self._substitute_env_vars(config_text)
            
            # Parse JSON
            config = json.loads(config_text)
            
            # Validate critical settings
            self._validate_config(config)
            
            logger.info(f"Configuration loaded successfully from {self.config_path}")
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_path} not found")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _substitute_env_vars(self, text: str) -> str:
        """Substitute ${VAR_NAME} patterns with environment variables"""
        def replace_var(match):
            var_name = match.group(1)
            env_value = os.getenv(var_name)
            
            if env_value is None:
                logger.warning(f"Environment variable {var_name} not found, using empty string")
                return ""
            
            # Mask sensitive data in logs
            if any(sensitive in var_name.lower() for sensitive in ['key', 'password', 'secret']):
                logger.debug(f"Substituted {var_name} with masked value")
            else:
                logger.debug(f"Substituted {var_name} with: {env_value}")
            
            return env_value
        
        # Pattern matches ${VAR_NAME}
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_var, text)
    
    def _validate_config(self, config: Dict[str, Any]):
        """Validate critical configuration settings"""
        # Check for sensitive data in config
        self._check_for_exposed_secrets(config)
        
        # Validate required settings
        required_keys = ['ASSISTANT_NAME', 'LANGUAGE', 'API_KEYS']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Required configuration key '{key}' missing")
        
        # Validate API keys are not hardcoded
        api_keys = config.get('API_KEYS', {})
        for key, value in api_keys.items():
            if value and not value.startswith('${') and key != '_comment':
                if 'sk-' in str(value) or 'key' in str(value).lower():
                    logger.warning(f"Potential hardcoded API key detected in {key}")
    
    def _check_for_exposed_secrets(self, obj, path=""):
        """Recursively check for exposed secrets in configuration"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                self._check_for_exposed_secrets(value, current_path)
        elif isinstance(obj, str):
            # Check for common API key patterns
            if re.match(r'sk-[a-zA-Z0-9]{20,}', obj):
                logger.error(f"Exposed OpenAI API key detected at {path}")
                raise ValueError(f"Hardcoded API key found at {path}")
            elif re.match(r'[a-f0-9]{32,}', obj) and len(obj) >= 32:
                logger.warning(f"Potential API key or token detected at {path}")
    
    def save_secure_config(self, config: Dict[str, Any], output_path: str = None):
        """Save configuration with environment variable placeholders"""
        output_path = output_path or self.config_path
        
        # Replace sensitive values with environment variable placeholders
        secure_config = self._secure_config_data(config)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(secure_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Secure configuration saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving secure configuration: {e}")
            raise
    
    def _secure_config_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Replace sensitive data with environment variable placeholders"""
        import copy
        secure_config = copy.deepcopy(config)
        
        # Define sensitive keys that should use environment variables
        sensitive_patterns = ['key', 'password', 'secret', 'token']
        
        def secure_dict(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check if this is a sensitive key
                    if any(pattern in key.lower() for pattern in sensitive_patterns):
                        if isinstance(value, str) and value and not value.startswith('${'):
                            # Replace with environment variable placeholder
                            env_var = key.upper()
                            obj[key] = f"${{{env_var}}}"
                            logger.info(f"Secured {current_path} with environment variable {env_var}")
                    else:
                        secure_dict(value, current_path)
        
        secure_dict(secure_config)
        return secure_config

# Global instance
config_loader = SecureConfigLoader()

def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration using secure loader"""
    if config_path:
        loader = SecureConfigLoader(config_path)
        return loader.load_config()
    return config_loader.load_config()

def get_api_key(provider: str) -> str:
    """Get API key for specified provider"""
    key_mapping = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'deepseek': 'DEEPSEEK_API_KEY',
        'azure': 'AZURE_SPEECH_KEY',
        'groq': 'GROQ_API_KEY',
        'together': 'TOGETHER_API_KEY'
    }
    
    env_var = key_mapping.get(provider.lower())
    if not env_var:
        raise ValueError(f"Unknown API provider: {provider}")
    
    api_key = os.getenv(env_var)
    if not api_key:
        raise ValueError(f"API key for {provider} not found in environment variables")
    
    return api_key
