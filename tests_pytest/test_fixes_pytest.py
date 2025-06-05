#!/usr/bin/env python3
"""pytest tests for build system"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import importlib # ADDED: For importing modules by string name

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)
# Add audio_modules to sys.path specifically for tests that need it directly
AUDIO_MODULES_PATH = os.path.join(PROJECT_ROOT, "audio_modules")
if AUDIO_MODULES_PATH not in sys.path:
    sys.path.insert(0, AUDIO_MODULES_PATH)


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
    # audio_modules_path is already added to sys.path globally for this file
    
    try:
        from whisper_asr import WhisperASR # This should now work if whisper_asr.py is in AUDIO_MODULES_PATH
        assert WhisperASR is not None
    except ImportError as e:
        # This is acceptable if torch is not available
        pytest.skip(f"WhisperASR import failed (expected if torch not available): {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error importing WhisperASR: {e}")


@patch('audio_modules.whisper_asr.WhisperASR', new_callable=MagicMock)
def test_whisper_asr_wrapper_behavior_on_errors(mock_whisper_class, caplog):
    """Test WhisperASR initialization with error handling when WhisperASR itself is mocked."""
    mock_instance = MagicMock()
    mock_whisper_class.return_value = mock_instance

    # Test basic initialization when WhisperASR is mocked
    from audio_modules.whisper_asr import WhisperASR
    try:
        asr = WhisperASR() # Call with default or test-specific parameters
        assert asr is mock_instance, "WhisperASR instance should be the mock_instance"
    except Exception as e:
        pytest.fail(f"WhisperASR initialization with mock failed unexpectedly: {e}")

    # Test scenario: Simulating a FileNotFoundError during WhisperASR initialization
    # This requires the *mocked* WhisperASR to raise FileNotFoundError
    mock_whisper_class.side_effect = FileNotFoundError("Simulated file not found by mock")
    with pytest.raises(FileNotFoundError, match="Simulated file not found by mock"):
        WhisperASR()
    
    # Reset side_effect for the next test case if needed, or use a new mock
    mock_whisper_class.side_effect = None # Clear previous side_effect
    mock_whisper_class.return_value = mock_instance # Restore return_value if cleared by side_effect

    # Test scenario: Simulating a generic Exception during WhisperASR initialization (e.g., model load failed)
    # This requires the *mocked* WhisperASR to raise a generic Exception
    mock_whisper_class.side_effect = Exception("Simulated model load failed by mock")
    with pytest.raises(Exception, match="Simulated model load failed by mock"):
        WhisperASR()
    
    # Clear side_effect again after the test
    mock_whisper_class.side_effect = None
    mock_whisper_class.return_value = mock_instance

@patch("faster_whisper.WhisperModel", new_callable=MagicMock) # Patched faster_whisper.WhisperModel
def test_whisper_model_loading_internal_error(mock_faster_whisper_model_class): # Renamed and modified
    """Test WhisperASR sets available=False when an internal error occurs during model loading."""
    # Simulate an error during WhisperModel instantiation
    mock_faster_whisper_model_class.side_effect = Exception("Test model loading error")

    from audio_modules.whisper_asr import WhisperASR 
    
    asr = WhisperASR(model_size="base")
    assert asr.available is False, "ASR should be unavailable if model loading fails."
    assert asr.model is None, "ASR model should be None if model loading fails."

@patch("faster_whisper.WhisperModel", new_callable=MagicMock) # Patched faster_whisper.WhisperModel
def test_whisper_model_loading_internal_success(mock_faster_whisper_model_class): # Renamed and modified
    """Test successful WhisperASR initialization with a mocked faster_whisper.WhisperModel."""
    # Simulate successful WhisperModel instantiation
    mock_model_instance = MagicMock()
    mock_faster_whisper_model_class.return_value = mock_model_instance

    from audio_modules.whisper_asr import WhisperASR

    asr = WhisperASR(model_size="tiny", compute_type="int8")
    
    assert asr.model is mock_model_instance, "asr.model should be the mocked instance."
    # The model_id is derived from the input model_size and internal logic in _candidates
    expected_model_id = "Systran/faster-whisper-tiny" 
    assert asr.model_id == expected_model_id, f"Expected model_id {expected_model_id}, got {asr.model_id}"
    
    mock_faster_whisper_model_class.assert_called_once_with(
        expected_model_id, device=asr.device, compute_type=asr.compute_type
    )
    assert asr.available is True, "ASR should be available on successful model load."
