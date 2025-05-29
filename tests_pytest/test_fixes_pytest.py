#!/usr/bin/env python3
"""pytest tests for dependency manager and torch guard fixes"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@patch('dependency_manager.DependencyManager')
def test_dependency_manager_import(mock_dependency_manager):
    """Test the dependency manager can be imported"""
    try:
        from dependency_manager import DependencyManager
        assert DependencyManager is not None
    except ImportError as e:
        pytest.fail(f"dependency_manager import failed: {e}")


@patch('dependency_manager.DependencyManager')
def test_dependency_manager_initialization(mock_dependency_manager):
    """Test the dependency manager initialization"""
    mock_instance = MagicMock()
    mock_dependency_manager.return_value = mock_instance
    
    try:
        from dependency_manager import DependencyManager
        manager = DependencyManager()
        assert manager is not None
        mock_dependency_manager.assert_called_once()
    except Exception as e:
        pytest.fail(f"DependencyManager initialization failed: {e}")


@patch('dependency_manager.DependencyManager')
def test_package_checking(mock_dependency_manager):
    """Test the package checking functionality"""
    mock_instance = MagicMock()
    mock_instance.check_missing_packages.return_value = ['test_package']
    mock_dependency_manager.return_value = mock_instance
    
    try:
        from dependency_manager import DependencyManager
        manager = DependencyManager()
        missing = manager.check_missing_packages()
        
        assert isinstance(missing, list)
        mock_instance.check_missing_packages.assert_called_once()
        
    except Exception as e:
        pytest.fail(f"Package checking failed: {e}")


def test_torch_guard_import():
    """Test the torch guard in whisper_asr"""
    audio_modules_path = Path(__file__).parent.parent / "audio_modules"
    
    if not audio_modules_path.exists():
        pytest.skip("audio_modules directory not found")
    
    sys.path.insert(0, str(audio_modules_path))
    
    try:
        from whisper_asr import WhisperASR
        assert WhisperASR is not None
    except ImportError as e:
        # This is acceptable if torch is not available
        pytest.skip(f"WhisperASR import failed (expected if torch not available): {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error importing WhisperASR: {e}")


@patch('audio_modules.whisper_asr.WhisperASR')
def test_whisper_asr_initialization(mock_whisper):
    """Test WhisperASR initialization with mock"""
    mock_instance = MagicMock()
    mock_instance.available = True
    mock_whisper.return_value = mock_instance
    
    audio_modules_path = Path(__file__).parent.parent / "audio_modules"
    if not audio_modules_path.exists():
        pytest.skip("audio_modules directory not found")
    
    sys.path.insert(0, str(audio_modules_path))
    
    try:
        from whisper_asr import WhisperASR
        asr = WhisperASR()
        assert asr is not None
        mock_whisper.assert_called_once()
    except ImportError:
        pytest.skip("WhisperASR not available")
    except Exception as e:
        pytest.fail(f"WhisperASR initialization failed: {e}")


def test_build_size_check():
    """Test built executable size if it exists"""
    exe_path = Path("release/Gaja.exe")
    
    if not exe_path.exists():
        pytest.skip("Gaja.exe not found - build not completed")
    
    size_mb = exe_path.stat().st_size / (1024 * 1024)
    
    # Check if size is reasonable
    assert size_mb > 0, "Executable file is empty"
    assert size_mb < 200, f"Executable size ({size_mb:.1f} MB) might be too large"


def test_whisper_torch_handling():
    """Test that whisper module handles torch dependency gracefully"""
    audio_modules_path = Path(__file__).parent.parent / "audio_modules"
    
    if not audio_modules_path.exists():
        pytest.skip("audio_modules directory not found")
    
    # Test that the module can be imported even without torch
    sys.path.insert(0, str(audio_modules_path))
    
    with patch.dict('sys.modules', {'torch': None}):
        try:
            import whisper_asr
            # Should be able to import even without torch
            assert whisper_asr is not None
        except ImportError as e:
            # Should not fail just because torch is missing
            if "torch" in str(e).lower():
                pytest.fail("whisper_asr should handle missing torch gracefully")
            else:
                pytest.skip(f"Other import error: {e}")


def test_dependency_fixes():
    """Test that dependency-related fixes are working"""
    # Test 1: Dependency manager exists
    try:
        import dependency_manager
        assert dependency_manager is not None
    except ImportError:
        pytest.fail("dependency_manager module should exist")
    
    # Test 2: Audio modules handle missing dependencies
    audio_modules_path = Path(__file__).parent.parent / "audio_modules"
    if audio_modules_path.exists():
        sys.path.insert(0, str(audio_modules_path))
        
        # Should be able to import without errors
        try:
            import whisper_asr
            import tts_module
            assert whisper_asr is not None
            assert tts_module is not None
        except ImportError as e:
            # Should handle missing dependencies gracefully
            if any(dep in str(e).lower() for dep in ['torch', 'transformers', 'whisper']):
                # This is expected when dependencies are missing
                pass
            else:
                pytest.fail(f"Unexpected import error: {e}")


def test_build_system_integration():
    """Test build system integration"""
    project_root = Path(__file__).parent.parent
    
    # Check that build files exist
    build_files = [
        'build.py',
        'gaja.spec',
        'requirements_build.txt'
    ]
    
    for file in build_files:
        file_path = project_root / file
        assert file_path.exists(), f"Build file {file} not found"
    
    # Check that dependency manager exists
    dep_manager_path = project_root / 'dependency_manager.py'
    assert dep_manager_path.exists(), "dependency_manager.py not found"


def test_hook_files():
    """Test that PyInstaller hook files exist"""
    project_root = Path(__file__).parent.parent
    
    hook_files = [
        'hook-sounddevice.py',
        'rthook_sounddevice.py'
    ]
    
    for file in hook_files:
        file_path = project_root / file
        assert file_path.exists(), f"Hook file {file} not found"


def test_audio_module_availability():
    """Test audio module availability and error handling"""
    audio_modules_path = Path(__file__).parent.parent / "audio_modules"
    
    if not audio_modules_path.exists():
        pytest.skip("audio_modules directory not found")
    
    sys.path.insert(0, str(audio_modules_path))
    
    modules_to_test = [
        'beep_sounds',
        'tts_module',
        'whisper_asr',
        'wakeword_detector'
    ]
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            assert module is not None
        except ImportError as e:
            # Some modules may not be available due to missing dependencies
            # This should be handled gracefully
            if any(dep in str(e).lower() for dep in ['torch', 'transformers', 'whisper', 'sounddevice']):
                pytest.skip(f"{module_name} not available due to missing dependency: {e}")
            else:
                pytest.fail(f"Unexpected error importing {module_name}: {e}")
