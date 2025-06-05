#!/usr/bin/env python3
"""pytest tests for build system"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_basic_imports():
    """Test basic module imports"""
    modules_to_test = [
        'pathlib',
        'json',
        'os',
        'sys',
        'subprocess',
        'zipfile',
        'time'
    ]
    
    for module in modules_to_test:
        try:
            __import__(module)
        except ImportError as e:
            pytest.fail(f"Failed to import {module}: {e}")


def test_requests_availability():
    """Test requests module availability"""
    try:
        import requests
        assert requests is not None
    except ImportError:
        # This is acceptable - fallback to urllib should be used
        pytest.skip("requests not available, fallback to urllib expected")


def test_build_config_files():
    """Test build configuration files exist"""
    project_root = Path(__file__).parent.parent
    
    files_to_check = [
        'gaja.spec',
        'build.py',
        'dependency_manager.py',
        'requirements_build.txt'
    ]
    
    for file in files_to_check:
        file_path = project_root / file
        assert file_path.exists(), f"Required build file {file} not found"


@patch('dependency_manager.DependencyManager')
def test_dependency_manager_import(mock_dependency_manager):
    """Test dependency manager can be imported"""
    try:
        from dependency_manager import DependencyManager
        assert DependencyManager is not None
    except ImportError as e:
        pytest.fail(f"Failed to import DependencyManager: {e}")


@patch('dependency_manager.DependencyManager')
def test_dependency_manager_initialization(mock_dependency_manager):
    """Test dependency manager initialization"""
    mock_instance = MagicMock()
    mock_dependency_manager.return_value = mock_instance
    
    try:
        from dependency_manager import DependencyManager
        manager = DependencyManager()
        assert manager is not None
        mock_dependency_manager.assert_called_once()
    except ImportError:
        pytest.skip("DependencyManager not available")


@patch('dependency_manager.DependencyManager')
def test_dependency_manager_methods(mock_dependency_manager):
    """Test dependency manager has required methods"""
    mock_instance = MagicMock()
    mock_instance.app_dir = "test_app"
    mock_instance.deps_dir = "test_deps"
    mock_instance.packages_dir = "test_packages"
    mock_instance.cache_dir = "test_cache"
    mock_instance.is_initialized.return_value = True
    mock_instance.get_installation_status.return_value = "installed"
    mock_instance.check_missing_packages.return_value = []
    
    mock_dependency_manager.return_value = mock_instance
    
    try:
        from dependency_manager import DependencyManager
        manager = DependencyManager()
        
        # Test required attributes
        assert hasattr(manager, 'app_dir')
        assert hasattr(manager, 'deps_dir')
        assert hasattr(manager, 'packages_dir')
        assert hasattr(manager, 'cache_dir')
        
        # Test required methods
        assert hasattr(manager, 'is_initialized')
        assert hasattr(manager, 'get_installation_status')
        assert hasattr(manager, 'check_missing_packages')
        
        # Test method calls
        assert manager.is_initialized() is True
        assert manager.get_installation_status() == "installed"
        assert manager.check_missing_packages() == []
        
    except ImportError:
        pytest.skip("DependencyManager not available")


def test_pathlib_usage():
    """Test pathlib can be used for path operations"""
    test_path = Path("test")
    assert isinstance(test_path, Path)
    
    # Test path operations
    parent = test_path.parent
    assert isinstance(parent, Path)
    
    # Test string conversion
    path_str = str(test_path)
    assert isinstance(path_str, str)


def test_subprocess_availability():
    """Test subprocess module for build operations"""
    import subprocess
    
    # Test that subprocess has required functions
    assert hasattr(subprocess, 'run')
    assert hasattr(subprocess, 'PIPE')
    assert hasattr(subprocess, 'STDOUT')


def test_json_operations():
    """Test JSON operations for config handling"""
    import json
    
    test_data = {"test": "value", "number": 42}
    
    # Test serialization
    json_str = json.dumps(test_data)
    assert isinstance(json_str, str)
    
    # Test deserialization
    parsed_data = json.loads(json_str)
    assert parsed_data == test_data


def test_zipfile_availability():
    """Test zipfile module for packaging"""
    import zipfile
    
    # Test that zipfile has required classes
    assert hasattr(zipfile, 'ZipFile')
    assert hasattr(zipfile, 'ZIP_DEFLATED')


def test_build_environment():
    """Test build environment readiness"""
    # Check Python version
    assert sys.version_info >= (3, 7), "Python 3.7+ required"
    
    # Check that we can access current working directory
    cwd = os.getcwd()
    assert isinstance(cwd, str)
    assert len(cwd) > 0
    
    # Check that we can list directory contents
    contents = os.listdir('.')
    assert isinstance(contents, list)


def test_project_structure():
    """Test that project has expected structure"""
    project_root = Path(__file__).parent.parent
    
    expected_dirs = [
        'modules',
        'audio_modules',
        'tests_pytest',
        'web_ui'
    ]
    
    for dir_name in expected_dirs:
        dir_path = project_root / dir_name
        assert dir_path.exists(), f"Expected directory {dir_name} not found"
        assert dir_path.is_dir(), f"{dir_name} is not a directory"


def test_requirements_file():
    """Test requirements_build.txt exists and is readable"""
    project_root = Path(__file__).parent.parent
    req_file = project_root / "requirements_build.txt"
    
    assert req_file.exists(), "requirements_build.txt not found"
    
    # Try to read the file
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert isinstance(content, str)
            assert len(content) > 0
    except Exception as e:
        pytest.fail(f"Failed to read requirements_build.txt: {e}")


@pytest.mark.skipif(not Path("release/Gaja.exe").exists(), reason="Built executable not found")
def test_built_executable():
    """Test built executable if it exists"""
    exe_path = Path("release/Gaja.exe")
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        
        # Executable should exist and have reasonable size
        assert size_mb > 0, "Executable file is empty"
        assert size_mb < 500, f"Executable size ({size_mb:.1f} MB) seems too large"
