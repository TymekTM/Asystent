#!/usr/bin/env python3

"""
Simple test to check core_module functions
"""

import sys
import os

# Add the server directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

# Import the core module directly
from server.modules import core_module

def test_core_module():
    print("Testing core_module functions...")
    
    # Check if get_functions exists
    if hasattr(core_module, 'get_functions'):
        print("✓ get_functions method found")
        try:
            functions = core_module.get_functions()
            print(f"✓ get_functions() returned {len(functions)} functions:")
            for func in functions:
                print(f"  - {func['name']}: {func['description']}")
        except Exception as e:
            print(f"✗ Error calling get_functions(): {e}")
            import traceback
            traceback.print_exc()
    else:
        print("✗ get_functions method not found")
    
    # Check if execute_function exists
    if hasattr(core_module, 'execute_function'):
        print("✓ execute_function method found")
        try:
            # Test get_current_time function
            result = core_module.execute_function("get_current_time", {})
            print(f"✓ execute_function('get_current_time', {{}}) = {result}")
        except Exception as e:
            print(f"✗ Error calling execute_function(): {e}")
            import traceback
            traceback.print_exc()
    else:
        print("✗ execute_function method not found")

if __name__ == "__main__":
    test_core_module()
