#!/usr/bin/env python3
"""Test script to verify parameter structure for playground interface"""

# Test the search module structure
def test_search_module():
    import sys
    sys.path.append('modules')
    
    # Import search module
    from search_module import register
    
    # Get module info
    info = register()
    print("Search Module Info:")
    print(f"Command: {info['command']}")
    print(f"Description: {info['description']}")
    print(f"Sub-commands: {list(info.get('sub_commands', {}).keys())}")
    
    # Check sub-command structure
    if 'sub_commands' in info:
        for sub_name, sub_info in info['sub_commands'].items():
            print(f"\nSub-command: {sub_name}")
            print(f"  Description: {sub_info.get('description')}")
            if 'parameters' in sub_info:
                print(f"  Parameters: {list(sub_info['parameters'].keys())}")
                for param_name, param_info in sub_info['parameters'].items():
                    print(f"    {param_name}: {param_info}")

if __name__ == "__main__":
    test_search_module()
