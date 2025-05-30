#!/usr/bin/env python3
"""Debug script to see what functions are being registered"""

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
    
    print(f"\nFound {len(functions)} functions:")
    for i, func in enumerate(functions[:5]):  # Show first 5 functions
        print(f"Function {i+1}:")
        print(json.dumps(func, indent=2, ensure_ascii=False))
        print()

if __name__ == "__main__":
    main()
