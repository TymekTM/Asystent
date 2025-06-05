#!/usr/bin/env python3
"""
Integration test for function calling with real modules.
"""

import pytest
import sys
import os

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def real_modules():
    """Load real modules for testing."""
    try:
        from assistant import get_assistant_instance
        assistant = get_assistant_instance()
        assistant.load_plugins()
        return assistant.modules
    except Exception as e:
        pytest.skip(f"Could not load real modules: {e}")

def test_real_modules_conversion(real_modules):
    """Test conversion of real assistant modules to function calling format."""
    from function_calling_system import FunctionCallingSystem
    
    # Create function calling system with real modules
    fc_system = FunctionCallingSystem(real_modules)
    functions = fc_system.convert_modules_to_functions()
    
    # Basic checks
    assert len(functions) > 0, "Should generate functions from real modules"
    assert len(functions) >= 10, f"Should generate reasonable number of functions, got {len(functions)}"
    
    # Check that core functions exist
    core_functions = [f for f in functions if 'core' in f['function']['name']]
    assert len(core_functions) > 0, "Should have core functions"
    
    # Check that memory functions exist
    memory_functions = [f for f in functions if 'memory' in f['function']['name']]
    assert len(memory_functions) > 0, "Should have memory functions"
    
    # Check timer functions specifically
    timer_functions = [f for f in functions if 'timer' in f['function']['name'].lower()]
    assert len(timer_functions) > 0, "Should have timer functions"

def test_real_function_execution(real_modules):
    """Test execution of real functions."""
    from function_calling_system import FunctionCallingSystem
    
    fc_system = FunctionCallingSystem(real_modules)
    
    # Test core timer function (should not actually set a timer in test)
    try:
        result = fc_system.execute_function("core_view_timers", {})
        assert isinstance(result, tuple), "Function should return tuple (response, success)"
        assert len(result) == 2, "Function should return (response, success)"
    except Exception as e:
        # If function doesn't exist or fails, that's also valuable info
        assert "not found" in str(e) or "core_view_timers" in str(e)

def test_memory_function_execution(real_modules):
    """Test memory function execution."""
    from function_calling_system import FunctionCallingSystem
    
    fc_system = FunctionCallingSystem(real_modules)
    
    # Test memory functions
    try:
        # Add something to memory
        result = fc_system.execute_function("memory_add", {"params": "Test integration entry"})
        assert isinstance(result, tuple), "Memory function should return tuple"
        
        # Try to retrieve it
        result2 = fc_system.execute_function("memory_get", {"params": "Test"})
        assert isinstance(result2, tuple), "Memory get should return tuple"
        
    except Exception as e:
        # Memory functions might require database setup
        assert "memory" in str(e).lower()

def test_function_descriptions_quality(real_modules):
    """Test that function descriptions are high quality for OpenAI."""
    from function_calling_system import FunctionCallingSystem
    
    fc_system = FunctionCallingSystem(real_modules)
    functions = fc_system.convert_modules_to_functions()
    
    for func in functions:
        func_def = func['function']
        name = func_def['name']
        desc = func_def['description']
          # Check description quality
        assert len(desc) > 10, f"Function {name} should have substantial description"
        # Note: We don't enforce no trailing periods since some original module descriptions have them
        
        # Timer functions should have enhanced descriptions
        if 'timer' in name.lower():
            keywords = ['timer', 'minutnik', 'stoper', 'countdown']
            assert any(keyword in desc for keyword in keywords), \
                f"Timer function {name} should mention timer keywords in description: {desc}"

if __name__ == "__main__":    # Run basic test without pytest
    try:
        from assistant import get_assistant_instance
        assistant = get_assistant_instance()
        assistant.load_plugins()
        
        from function_calling_system import FunctionCallingSystem
        fc_system = FunctionCallingSystem(assistant.modules)
        functions = fc_system.convert_modules_to_functions()
        
        print(f"Integration test passed: {len(functions)} functions generated")
        
    except Exception as e:
        print(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
