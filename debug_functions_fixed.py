#!/usr/bin/env python3
"""Debug script to see what functions are being registered"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from function_calling_system import FunctionCallingSystem
from config import load_config
from assistant import Assistant

def main():
    """Debug function registration"""
    print("Loading configuration...")
    config = load_config()
    
    print("Creating assistant...")
    assistant = Assistant()
    
    print("Loading modules...")
    assistant.load_plugins()
    modules = assistant.modules
    
    print("Creating function calling system...")
    fc_system = FunctionCallingSystem(modules)
    
    print("Converting modules to functions...")
    functions = fc_system.convert_modules_to_functions()
    
    print(f"\nFound {len(functions)} functions:")
    for func in functions:
        name = func['name']
        desc = func['description']
        print(f"  - {name}: {desc}")
        
        # Check for timer-related functions
        if 'timer' in name.lower() or 'minutnik' in desc.lower() or 'stoper' in desc.lower():
            print(f"    ** TIMER FUNCTION: {name}")
            print(f"       Description: {desc}")
            if 'parameters' in func:
                props = func['parameters'].get('properties', {})
                for prop_name, prop_info in props.items():
                    print(f"       Parameter {prop_name}: {prop_info.get('description', 'No description')}")
            print()

if __name__ == "__main__":
    main()
