#!/usr/bin/env python3
"""pytest tests for API transformation for playground interface"""

import pytest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'modules'))

from modules.search_module import register as search_register
from modules.weather_module import register as weather_register


def transform_sub_commands(sub_commands):
    """Transform sub_commands from dict to array format like in API"""
    if not sub_commands:
        return []
        
    sub_commands_array = []
    for sub_name, sub_info in sub_commands.items():
        if isinstance(sub_info, dict):
            sub_cmd_obj = {
                'name': sub_name,
                'description': sub_info.get('description', 'No description'),
                'aliases': sub_info.get('aliases', []),
                'params_desc': sub_info.get('params_desc', ''),
                'function_name': getattr(sub_info.get('function'), '__name__', 'unknown') if 'function' in sub_info else None
            }
            
            # Convert parameters object to array format for frontend
            if 'parameters' in sub_info and isinstance(sub_info['parameters'], dict):
                parameters_array = []
                for param_name, param_info in sub_info['parameters'].items():
                    param_obj = {
                        'name': param_name,
                        'type': param_info.get('type', 'string'),
                        'description': param_info.get('description', ''),
                        'required': param_info.get('required', False)
                    }
                    parameters_array.append(param_obj)
                sub_cmd_obj['parameters'] = parameters_array
            
            sub_commands_array.append(sub_cmd_obj)
    
    return sub_commands_array


def test_search_module_transformation():
    """Test search module API transformation"""
    search_info = search_register()
    search_subs = transform_sub_commands(search_info.get('sub_commands', {}))
    
    assert isinstance(search_subs, list)
    assert len(search_subs) >= 0
    
    for sub in search_subs:
        assert 'name' in sub
        assert 'description' in sub
        assert isinstance(sub.get('parameters', []), list)
        
        for param in sub.get('parameters', []):
            assert 'name' in param
            assert 'type' in param
            assert 'required' in param
            assert isinstance(param['required'], bool)


def test_weather_module_transformation():
    """Test weather module API transformation"""
    weather_info = weather_register()
    weather_subs = transform_sub_commands(weather_info.get('sub_commands', {}))
    
    assert isinstance(weather_subs, list)
    assert len(weather_subs) >= 0
    
    for sub in weather_subs:
        assert 'name' in sub
        assert 'description' in sub
        assert 'function_name' in sub
        assert isinstance(sub.get('parameters', []), list)


def test_transform_sub_commands_empty():
    """Test transformation with empty input"""
    result = transform_sub_commands({})
    assert result == []
    
    result = transform_sub_commands(None)
    assert result == []


def test_transform_sub_commands_structure():
    """Test transformation with mock structure"""
    mock_sub_commands = {
        'test_command': {
            'description': 'Test command',
            'aliases': ['tc'],
            'parameters': {
                'query': {
                    'type': 'string',
                    'description': 'Search query',
                    'required': True
                },
                'count': {
                    'type': 'integer',
                    'description': 'Number of results',
                    'required': False
                }
            }
        }
    }
    
    result = transform_sub_commands(mock_sub_commands)
    
    assert len(result) == 1
    assert result[0]['name'] == 'test_command'
    assert result[0]['description'] == 'Test command'
    assert result[0]['aliases'] == ['tc']
    assert len(result[0]['parameters']) == 2
    
    # Check parameters structure
    params = result[0]['parameters']
    query_param = next(p for p in params if p['name'] == 'query')
    count_param = next(p for p in params if p['name'] == 'count')
    
    assert query_param['required'] is True
    assert count_param['required'] is False
    assert query_param['type'] == 'string'
    assert count_param['type'] == 'integer'
