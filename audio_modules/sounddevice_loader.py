"""
Centralized sounddevice loader with automatic dependency management.
This module handles sounddevice import with fallback to dependency manager.
"""

import logging

# Global variables to store sounddevice module and availability status
_sounddevice_module = None
_sounddevice_available = None

def ensure_sounddevice():
    """Ensure sounddevice is available, downloading if necessary."""
    global _sounddevice_module, _sounddevice_available
    
    if _sounddevice_available is not None:
        return _sounddevice_available
    
    try:
        import sounddevice as sd
        _sounddevice_module = sd
        _sounddevice_available = True
        logging.getLogger(__name__).info("sounddevice loaded successfully")
        return True
    except (ImportError, OSError) as e:
        logging.getLogger(__name__).warning(f"sounddevice not available: {e}")
        _sounddevice_available = False
        
        # Try to install via dependency manager
        try:
            import sys
            import os
            
            # Add parent directory to path to import dependency_manager
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from dependency_manager import DependencyManager
            
            logging.getLogger(__name__).info("Attempting to install sounddevice via dependency manager...")
            dep_manager = DependencyManager()
              # Check if sounddevice is missing and install it
            missing = dep_manager.check_missing_packages()
            if "sounddevice" in missing:
                success = dep_manager.install_missing_packages(["sounddevice"])
                if success:
                    logging.getLogger(__name__).info("sounddevice installed successfully")
                    # Try importing again
                    try:
                        import sounddevice as sd
                        _sounddevice_module = sd
                        _sounddevice_available = True
                        return True
                    except (ImportError, OSError) as e2:
                        logging.getLogger(__name__).error(f"sounddevice still not available after installation: {e2}")
                        return False
                else:
                    logging.getLogger(__name__).error("Failed to install sounddevice")
                    return False
            else:
                logging.getLogger(__name__).info("sounddevice appears to be installed but not importable")
                return False
                
        except Exception as e2:
            logging.getLogger(__name__).error(f"Failed to use dependency manager for sounddevice: {e2}")
            return False

def get_sounddevice():
    """Get the sounddevice module, ensuring it's available first."""
    ensure_sounddevice()
    return _sounddevice_module

def is_sounddevice_available():
    """Check if sounddevice is available."""
    ensure_sounddevice()
    return _sounddevice_available
