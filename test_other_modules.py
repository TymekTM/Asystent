#!/usr/bin/env python3
"""Test script to verify other modules"""

def test_other_modules():
    import sys
    sys.path.append('modules')
    
    # Test multiple modules
    modules_to_test = [
        ('open_web_module', 'open_web'),
        ('see_screen_module', 'see_screen'),
        ('music_module', 'music'),
        ('deepseek_module', 'deepseek')
    ]
    
    for module_name, expected_command in modules_to_test:
        try:
            module = __import__(module_name)
            info = module.register()
            
            print(f"\n=== {module_name.upper()} ===")
            print(f"Command: {info['command']}")
            print(f"Sub-commands: {len(info.get('sub_commands', {}))}")
            
            for sub_name, sub_info in info.get('sub_commands', {}).items():
                print(f"  {sub_name}: {len(sub_info.get('parameters', {}))} parameters")
                for param_name, param_info in sub_info.get('parameters', {}).items():
                    required = param_info.get('required', False)
                    print(f"    {param_name}: {param_info.get('type', 'string')} ({'required' if required else 'optional'})")
        except Exception as e:
            print(f"Error testing {module_name}: {e}")

if __name__ == "__main__":
    test_other_modules()
