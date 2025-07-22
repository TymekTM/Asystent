#!/usr/bin/env python3
"""Script to check available plugins in Gaja system - simplified version."""

import importlib.util
import os
import sys

# Add paths
sys.path.insert(0, ".")
sys.path.insert(0, "./server")


def load_module_safe(module_name, file_path):
    """Safely load a module from file path."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        return module
    except Exception as e:
        print(f"Error loading {module_name}: {e}")
        return None


def check_module_functions(module_name, file_path):
    """Check what functions a module exports."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        print(f"📦 {module_name.upper()}:")

        # Look for get_functions definition
        if "def get_functions()" in content:
            # Try to extract function names from get_functions
            lines = content.split("\n")
            in_get_functions = False
            functions = []

            for line in lines:
                if "def get_functions()" in line:
                    in_get_functions = True
                    continue

                if in_get_functions:
                    # Look for function definitions in the return list
                    if '"name":' in line:
                        name_start = line.find('"name":') + 8
                        name_end = line.find('"', name_start + 1)
                        if name_end > name_start:
                            func_name = line[name_start:name_end]
                            functions.append(func_name)

                    # Stop when we reach the end of the function
                    if line.strip().startswith("async def ") or (
                        line.strip().startswith("def ") and "get_functions" not in line
                    ):
                        break

            if functions:
                for func in functions:
                    print(f"  • {func}")
            else:
                print("  • (Found get_functions but could not parse function names)")
        else:
            print("  • No get_functions() found")

        print()

    except Exception as e:
        print(f"  Error reading {module_name}: {e}")
        print()


# Check modules
modules_path = "server/modules"
module_files = [
    "weather_module.py",
    "search_module.py",
    "core_module.py",
    "music_module.py",
    "api_module.py",
    "open_web_module.py",
    "memory_module.py",
    "plugin_monitor_module.py",
    "onboarding_plugin_module.py",
]

print("=== DOSTĘPNE PLUGINY AI W SYSTEMIE GAJA ===")
print()

for module_file in module_files:
    module_name = module_file.replace(".py", "")
    file_path = os.path.join(modules_path, module_file)

    if os.path.exists(file_path):
        check_module_functions(module_name, file_path)
    else:
        print(f"⚠️  {module_name}: File not found at {file_path}")
        print()
