#!/usr/bin/env python3
"""Script to check available plugins in Gaja system."""

import sys
import os
sys.path.insert(0, '.')

from server.modules import (
    weather_module, search_module, core_module, music_module, 
    api_module, open_web_module, memory_module, 
    plugin_monitor_module, onboarding_plugin_module
)

modules = [
    ('weather_module', weather_module),
    ('search_module', search_module), 
    ('core_module', core_module),
    ('music_module', music_module),
    ('api_module', api_module),
    ('open_web_module', open_web_module),
    ('memory_module', memory_module),
    ('plugin_monitor_module', plugin_monitor_module),
    ('onboarding_plugin_module', onboarding_plugin_module)
]

print('=== DOSTĘPNE PLUGINY AI W SYSTEMIE GAJA ===')
print()

for name, module in modules:
    if hasattr(module, 'get_functions'):
        functions = module.get_functions()
        print(f'📦 {name.upper()}:')
        for func in functions:
            print(f'  • {func["name"]}: {func["description"]}')
        print()
    else:
        print(f'⚠️  {name}: Brak funkcji get_functions()')
