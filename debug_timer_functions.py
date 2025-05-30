#!/usr/bin/env python3
"""Debug script to find timer functions"""

import sys
import os
import json
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
    
    print(f"\nSearching for timer functions among {len(functions)} functions:")
    
    for i, func in enumerate(functions):
        if 'function' in func and 'name' in func['function']:
            name = func['function']['name']
            desc = func['function']['description']
            
            # Check for timer-related functions
            if 'timer' in name.lower() or 'minutnik' in desc.lower() or 'stoper' in desc.lower() or 'core' in name.lower():
                print(f"\n** FOUND TIMER/CORE FUNCTION: {name}")
                print(f"   Description: {desc}")
                if 'parameters' in func['function']:
                    props = func['function']['parameters'].get('properties', {})
                    for prop_name, prop_info in props.items():
                        print(f"   Parameter {prop_name}: {prop_info.get('description', 'No description')}")
                print()

if __name__ == "__main__":
    main()
