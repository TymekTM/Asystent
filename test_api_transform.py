#!/usr/bin/env python3
"""Test script to verify API transformation for playground interface"""

def test_api_transformation():
    import sys
    sys.path.append('modules')
    
    # Import modules
    from search_module import register as search_register
    from weather_module import register as weather_register
    
    # Get module info
    search_info = search_register()
    weather_info = weather_register()
    
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
    
    # Test search module transformation
    print("=== SEARCH MODULE ===")
    search_subs = transform_sub_commands(search_info.get('sub_commands', {}))
    print(f"Transformed sub-commands: {len(search_subs)}")
    for sub in search_subs:
        print(f"Sub-command: {sub['name']}")
        print(f"  Description: {sub['description']}")
        print(f"  Parameters: {len(sub.get('parameters', []))}")
        for param in sub.get('parameters', []):
            print(f"    {param['name']}: {param['type']} ({'required' if param['required'] else 'optional'})")
    
    # Test weather module transformation
    print("\n=== WEATHER MODULE ===")
    weather_subs = transform_sub_commands(weather_info.get('sub_commands', {}))
    print(f"Transformed sub-commands: {len(weather_subs)}")
    for sub in weather_subs:
        print(f"Sub-command: {sub['name']}")
        print(f"  Description: {sub['description']}")
        print(f"  Has function: {sub['function_name'] != 'unknown'}")
        print(f"  Parameters: {len(sub.get('parameters', []))}")

if __name__ == "__main__":
    test_api_transformation()
