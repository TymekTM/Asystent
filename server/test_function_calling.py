#!/usr/bin/env python3

import asyncio
from plugin_manager import plugin_manager
from function_calling_system import FunctionCallingSystem

async def test():
    # Load plugins
    await plugin_manager.discover_plugins()
    for plugin_name in list(plugin_manager.plugins.keys()):
        await plugin_manager.load_plugin(plugin_name)
    
    print(f'Plugin function registry: {len(plugin_manager.function_registry)} functions')
    
    # Test function calling system
    function_system = FunctionCallingSystem()
    functions = function_system.convert_modules_to_functions()
    
    print(f'Converted to OpenAI format: {len(functions)} functions')
    
    # Show first few functions
    for i, func in enumerate(functions[:3]):
        func_name = func["function"]["name"]
        func_desc = func["function"]["description"]
        func_params = func["function"]["parameters"]
        print(f'Function {i+1}: {func_name}')
        print(f'  Description: {func_desc}')
        print(f'  Parameters: {func_params}')
        print()
    
    # Test a simple function execution
    print('Testing weather function execution...')
    try:
        result = await function_system.execute_function('weather_module_get_weather', {
            'location': 'Warsaw',
            'test_mode': True
        })
        print(f'Weather result: {result}')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
