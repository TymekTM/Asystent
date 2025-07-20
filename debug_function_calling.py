#!/usr/bin/env python3
"""
Debug script for function calling system
"""
import logging
logging.basicConfig(level=logging.DEBUG)

def debug_function_calling():
    """Debug the function calling system step by step"""
    functions = []
    
    print("=== DEBUGGING FUNCTION CALLING SYSTEM ===")
    
    # First try plugin manager (legacy support)
    print("\n1. Checking plugin manager...")
    try:
        from plugin_manager import plugin_manager
        
        print(f"Plugin manager function_registry length: {len(plugin_manager.function_registry)}")
        
        if plugin_manager.function_registry:
            print("Plugin manager has functions - processing...")
            # (code for plugin manager processing would be here)
        else:
            print("Plugin manager function_registry is empty - skipping")
            
    except Exception as e:
        print(f"Plugin manager error: {e}")
    
    # Add server modules directly (main source of functions)
    print("\n2. Checking server modules...")
    try:
        from server.modules import (
            weather_module, search_module, core_module, music_module, 
            api_module, open_web_module, memory_module, plugin_monitor_module,
            onboarding_plugin_module
        )
        
        server_modules = [
            ('weather', weather_module),
            ('search', search_module),
            ('core', core_module),
            ('music', music_module),
            ('api', api_module),
            ('web', open_web_module),
            ('memory', memory_module),
            ('monitor', plugin_monitor_module),
            ('onboarding', onboarding_plugin_module)
        ]
        
        print(f"Server modules to process: {len(server_modules)}")
        
        for module_name, module in server_modules:
            print(f"\nProcessing module: {module_name}")
            try:
                if hasattr(module, 'get_functions'):
                    module_functions = module.get_functions()
                    print(f"  - Has get_functions: YES")
                    print(f"  - Functions count: {len(module_functions)}")
                    
                    for func in module_functions:
                        function_name = f"{module_name}_{func['name']}"
                        print(f"    + {function_name}")
                        
                        openai_func = {
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "description": func['description'],
                                "parameters": func['parameters']
                            }
                        }
                        functions.append(openai_func)
                        
                else:
                    print(f"  - Has get_functions: NO")
                    print(f"  - Available attributes: {[attr for attr in dir(module) if not attr.startswith('_')][:5]}...")
                    
            except Exception as e:
                print(f"  - ERROR processing {module_name}: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"Error importing server modules: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n=== FINAL RESULT ===")
    print(f"Total functions collected: {len(functions)}")
    
    if functions:
        print(f"First 5 functions:")
        for i, func in enumerate(functions[:5]):
            print(f"  {i+1}. {func['function']['name']}")
    
    return functions

if __name__ == "__main__":
    functions = debug_function_calling()
