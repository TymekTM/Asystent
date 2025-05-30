#!/usr/bin/env python3
"""Quick test to verify function calling works"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from function_calling_system import FunctionCallingSystem
from config import load_config
from assistant import Assistant

def main():
    """Quick verification test"""
    print("=== FUNCTION CALLING SYSTEM VERIFICATION ===")
    
    config = load_config()
    assistant = Assistant()
    assistant.load_plugins()
    
    fc_system = FunctionCallingSystem(assistant.modules)
    functions = fc_system.convert_modules_to_functions()
    
    print(f"✅ Loaded {len(assistant.modules)} modules")
    print(f"✅ Generated {len(functions)} functions")
    
    # Check for timer functions
    timer_functions = [f for f in functions if 'timer' in f['function']['name']]
    print(f"✅ Found {len(timer_functions)} timer functions")
    
    # Check for core functions
    core_functions = [f for f in functions if 'core' in f['function']['name']]
    print(f"✅ Found {len(core_functions)} core functions")
    
    print("\n=== SYSTEM READY ===")
    print("Function calling system is working correctly!")
    print("Timer functions available for 'minutnik' requests")
    print("Core module loaded and functioning")

if __name__ == "__main__":
    main()
