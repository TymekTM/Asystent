#!/usr/bin/env python3
"""pytest tests for other modules verification"""

import pytest
import sys
import os
import importlib

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'modules'))


def test_module_imports():
    """Test that modules can be imported"""
    modules_to_test = [
        'open_web_module',
        'see_screen_module', 
        'music_module',
        'deepseek_module'
    ]
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")


def test_open_web_module_structure():
    """Test open_web_module structure"""
    try:
        from modules.open_web_module import register # Corrected import
        info = register()
        
        assert 'command' in info
        assert 'description' in info
        assert 'handler' in info
        assert callable(info['handler'])
        
    except ImportError:
        pytest.skip("open_web_module not available")


def test_see_screen_module_structure():
    """Test see_screen_module structure"""
    try:
        from modules.see_screen_module import register # Corrected import
        info = register()
        
        assert 'command' in info
        assert 'description' in info
        assert 'handler' in info
        assert callable(info['handler'])
        
    except ImportError:
        pytest.skip("see_screen_module not available")


def test_music_module_structure():
    """Test music_module structure"""
    try:
        from modules.music_module import register # Corrected import
        info = register()
        
        assert 'command' in info
        assert 'description' in info
        
        # Music module might have sub_commands
        if 'sub_commands' in info:
            assert isinstance(info['sub_commands'], dict)
            
    except ImportError:
        pytest.skip("music_module not available")


def test_deepseek_module_structure():
    """Test deepseek_module structure"""
    try:
        from modules.deepseek_module import register # Corrected import
        info = register()
        
        assert 'command' in info
        assert 'description' in info
        assert 'handler' in info
        assert callable(info['handler'])
        
    except ImportError:
        pytest.skip("deepseek_module not available")


def test_modules_registration_consistency():
    """Test that all modules follow consistent registration pattern"""
    modules_to_test = [
        # (module_path, expected_command_key_in_dict, expected_command_value, should_exist)
        ('modules.open_web_module', 'command', 'open', True),
        ('modules.see_screen_module', 'command', 'screenshot', True),
        ('modules.music_module', 'command', 'music', True),
        ('modules.deepseek_module', 'command', 'deep', True) # deepseek module uses 'deep' as its main command
    ]

    for module_path, command_key, expected_command_value, should_exist in modules_to_test:
        try:
            module = importlib.import_module(module_path)
            
            if not hasattr(module, 'register') or not callable(module.register):
                pytest.fail(f"{module_path} does not have a callable register function.")

            registered_info = module.register()

            assert isinstance(registered_info, dict), f"{module_path} did not return a dict"
            assert command_key in registered_info, f"'{command_key}' is missing in {module_path} registration"
            assert 'description' in registered_info, f"description is missing in {module_path} registration"
            
            # Check command value matches expected
            actual_command_value = registered_info.get(command_key)
            assert actual_command_value == expected_command_value, \
                f"Command mismatch for {module_path}. Expected '{expected_command_value}', got '{actual_command_value}'"
                
        except ImportError:
            if should_exist:
                pytest.fail(f"Module {module_path} not found but was expected.")
            else:
                pytest.skip(f"Module {module_path} not found and was not expected.")
        except Exception as e:
            pytest.fail(f"Error testing {module_path}: {e}")


def test_sub_commands_structure():
    """Test sub-commands structure where present"""
    modules_to_test = ['open_web_module', 'see_screen_module', 'music_module', 'deepseek_module']
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            info = module.register()
            
            if 'sub_commands' in info:
                sub_commands = info['sub_commands']
                assert isinstance(sub_commands, dict)
                
                for sub_name, sub_info in sub_commands.items():
                    assert isinstance(sub_name, str)
                    assert isinstance(sub_info, dict)
                    
                    # Check for parameters if present
                    if 'parameters' in sub_info:
                        parameters = sub_info['parameters']
                        assert isinstance(parameters, dict)
                        
                        for param_name, param_info in parameters.items():
                            assert isinstance(param_name, str)
                            assert isinstance(param_info, dict)
                            
                            # Check required parameter fields
                            if 'required' in param_info:
                                assert isinstance(param_info['required'], bool)
                            if 'type' in param_info:
                                assert isinstance(param_info['type'], str)
                                
        except ImportError:
            pytest.skip(f"{module_name} not available")
        except Exception as e:
            pytest.fail(f"Error testing sub-commands for {module_name}: {e}")


def test_module_handlers_callable():
    """Test that module handlers are callable"""
    modules_to_test = ['open_web_module', 'see_screen_module', 'deepseek_module']
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            info = module.register()
            
            if 'handler' in info:
                assert callable(info['handler'])
                
        except ImportError:
            pytest.skip(f"{module_name} not available")
        except Exception as e:
            pytest.fail(f"Error testing handler for {module_name}: {e}")


def test_parameters_validation():
    """Test parameter structure validation"""
    modules_to_test = ['open_web_module', 'see_screen_module', 'music_module', 'deepseek_module']
    
    for module_name in modules_to_test:
        try:
            module = __import__(module_name)
            info = module.register()
            
            if 'sub_commands' in info:
                for sub_name, sub_info in info['sub_commands'].items():
                    if 'parameters' in sub_info:
                        for param_name, param_info in sub_info['parameters'].items():
                            # Validate parameter structure
                            assert isinstance(param_info, dict)
                            
                            # Common fields that should be strings if present
                            for field in ['type', 'description']:
                                if field in param_info:
                                    assert isinstance(param_info[field], str)
                                    
                            # Required field should be boolean if present
                            if 'required' in param_info:
                                assert isinstance(param_info['required'], bool)
                                
        except ImportError:
            pytest.skip(f"{module_name} not available")
        except Exception as e:
            pytest.fail(f"Error validating parameters for {module_name}: {e}")
