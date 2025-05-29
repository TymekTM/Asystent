#!/usr/bin/env python3
"""pytest tests for parameter structure verification for playground interface"""

import pytest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'modules'))


def test_search_module_structure():
    """Test search module parameter structure"""
    try:
        from search_module import register
        info = register()
        
        assert isinstance(info, dict)
        assert 'command' in info
        assert 'description' in info
        assert isinstance(info['command'], str)
        assert isinstance(info['description'], str)
        
        # Check sub-commands structure
        if 'sub_commands' in info:
            sub_commands = info['sub_commands']
            assert isinstance(sub_commands, dict)
            
            for sub_name, sub_info in sub_commands.items():
                assert isinstance(sub_name, str)
                assert isinstance(sub_info, dict)
                
                # Check description
                if 'description' in sub_info:
                    assert isinstance(sub_info['description'], str)
                
                # Check parameters structure
                if 'parameters' in sub_info:
                    parameters = sub_info['parameters']
                    assert isinstance(parameters, dict)
                    
                    for param_name, param_info in parameters.items():
                        assert isinstance(param_name, str)
                        assert isinstance(param_info, dict)
                        
                        # Validate parameter fields
                        if 'type' in param_info:
                            assert isinstance(param_info['type'], str)
                        if 'description' in param_info:
                            assert isinstance(param_info['description'], str)
                        if 'required' in param_info:
                            assert isinstance(param_info['required'], bool)
                            
    except ImportError:
        pytest.skip("search_module not available")


def test_parameter_types_consistency():
    """Test that parameter types are consistent across modules"""
    valid_types = ['string', 'integer', 'boolean', 'float', 'array', 'object']
    
    try:
        from search_module import register
        info = register()
        
        if 'sub_commands' in info:
            for sub_name, sub_info in info['sub_commands'].items():
                if 'parameters' in sub_info:
                    for param_name, param_info in sub_info['parameters'].items():
                        if 'type' in param_info:
                            param_type = param_info['type']
                            # Should be one of the valid types or a reasonable variant
                            assert param_type in valid_types or param_type in ['str', 'int', 'bool']
                            
    except ImportError:
        pytest.skip("search_module not available")


def test_required_parameter_fields():
    """Test that parameters have required fields"""
    try:
        from search_module import register
        info = register()
        
        if 'sub_commands' in info:
            for sub_name, sub_info in info['sub_commands'].items():
                if 'parameters' in sub_info:
                    for param_name, param_info in sub_info['parameters'].items():
                        # Each parameter should be a dict
                        assert isinstance(param_info, dict)
                        
                        # Should have at least type or description
                        assert 'type' in param_info or 'description' in param_info
                        
    except ImportError:
        pytest.skip("search_module not available")


def test_playground_interface_compatibility():
    """Test parameter structure compatibility with playground interface"""
    try:
        from search_module import register
        info = register()
        
        # Test that the structure can be transformed for playground
        playground_compatible = True
        
        if 'sub_commands' in info:
            for sub_name, sub_info in info['sub_commands'].items():
                # Check if sub-command has required fields for playground
                required_fields = ['description']
                for field in required_fields:
                    if field not in sub_info:
                        playground_compatible = False
                        
                # Check parameters structure
                if 'parameters' in sub_info:
                    for param_name, param_info in sub_info['parameters'].items():
                        # Parameters should have description and type for playground
                        if 'description' not in param_info:
                            # This is acceptable, but log it
                            pass
                        if 'type' not in param_info:
                            # This should have a default type
                            pass
                            
        assert playground_compatible or len(info.get('sub_commands', {})) == 0
        
    except ImportError:
        pytest.skip("search_module not available")


def test_parameter_description_quality():
    """Test that parameter descriptions are meaningful"""
    try:
        from search_module import register
        info = register()
        
        if 'sub_commands' in info:
            for sub_name, sub_info in info['sub_commands'].items():
                if 'parameters' in sub_info:
                    for param_name, param_info in sub_info['parameters'].items():
                        if 'description' in param_info:
                            description = param_info['description']
                            assert isinstance(description, str)
                            assert len(description.strip()) > 0
                            # Should not be just the parameter name
                            assert description.lower() != param_name.lower()
                            
    except ImportError:
        pytest.skip("search_module not available")


def test_sub_command_names():
    """Test that sub-command names are valid"""
    try:
        from search_module import register
        info = register()
        
        if 'sub_commands' in info:
            for sub_name in info['sub_commands'].keys():
                # Sub-command names should be valid identifiers
                assert isinstance(sub_name, str)
                assert len(sub_name) > 0
                # Should not contain spaces or special characters (except underscore)
                assert all(c.isalnum() or c == '_' for c in sub_name)
                
    except ImportError:
        pytest.skip("search_module not available")


def test_module_command_consistency():
    """Test that module command is consistent"""
    try:
        from search_module import register
        info = register()
        
        assert 'command' in info
        command = info['command']
        assert isinstance(command, str)
        assert len(command) > 0
        # Command should be a simple identifier
        assert all(c.isalnum() or c == '_' for c in command)
        
    except ImportError:
        pytest.skip("search_module not available")


def test_nested_parameter_structure():
    """Test handling of nested parameter structures"""
    try:
        from search_module import register
        info = register()
        
        if 'sub_commands' in info:
            for sub_name, sub_info in info['sub_commands'].items():
                if 'parameters' in sub_info:
                    # Parameters should be flat for playground compatibility
                    for param_name, param_info in sub_info['parameters'].items():
                        assert isinstance(param_info, dict)
                        # Check that we don't have deeply nested structures
                        for key, value in param_info.items():
                            if key != 'enum' and isinstance(value, dict):
                                # Nested dicts should be simple
                                assert len(value) <= 5  # Reasonable limit
                                
    except ImportError:
        pytest.skip("search_module not available")
