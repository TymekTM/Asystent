#!/usr/bin/env python3
"""Debug script to see what modules are loaded"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import load_config
from assistant import Assistant

def main():
    """Debug module loading"""
    print("Loading configuration...")
    config = load_config()
    
    print("Creating assistant...")
    assistant = Assistant()
    
    print("Loading modules...")
    assistant.load_plugins()
    
    print(f"\nLoaded modules: {list(assistant.modules.keys())}")
    
    for module_name, module_info in assistant.modules.items():
        print(f"\nModule: {module_name}")
        print(f"  Handler: {module_info.get('handler', 'None')}")
        print(f"  Description: {module_info.get('description', 'None')}")
        
        sub_commands = module_info.get('sub_commands', {})
        if sub_commands:
            print(f"  Sub-commands:")
            for sub_name, sub_info in sub_commands.items():
                print(f"    - {sub_name}: {sub_info.get('description', 'No description')}")

if __name__ == "__main__":
    main()
