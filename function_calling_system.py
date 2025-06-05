"""
function_calling_system.py

OpenAI Function Calling system for Gaja AI assistant.
Converts the existing module system to OpenAI function calling format.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Callable
from collections import deque

logger = logging.getLogger(__name__)

class FunctionCallingSystem:
    """Manages conversion of modules to OpenAI function calling format."""
    
    def __init__(self, modules: Dict[str, Any]):
        """Initialize with the current modules dictionary."""
        self.modules = modules
        self.function_handlers: Dict[str, Callable] = {}
        
    def convert_modules_to_functions(self) -> List[Dict[str, Any]]:
        """Convert modules to OpenAI function calling format."""
        functions = []
        
        for module_name, module_info in self.modules.items():
            # Create main function for the module
            main_function = self._create_main_function(module_name, module_info)
            if main_function:
                functions.append(main_function)
                
            # Create functions for sub-commands
            sub_commands = module_info.get('sub_commands', {})
            for sub_name, sub_info in sub_commands.items():
                if isinstance(sub_info, dict) and 'function' in sub_info:
                    sub_function = self._create_sub_function(module_name, sub_name, sub_info)
                    if sub_function:
                        functions.append(sub_function)
        
        return functions
    
    def _create_main_function(self, module_name: str, module_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create main function definition for a module."""
        if 'handler' not in module_info:
            return None
            
        function_name = f"{module_name}_main"
        self.function_handlers[function_name] = module_info['handler']
        
        # Enhanced description for better OpenAI understanding
        base_description = module_info.get('description', f'{module_name} module')
        enhanced_description = self._enhance_main_function_description(module_name, base_description)

        # Build parameters schema
        parameters = {
            "type": "object",
            "properties": {
                "params": {
                    "type": "string",
                    "description": f"Parameters for {module_name} module"
                }
            },
            "required": []
        }
        
        # Add sub-command selection if module has sub-commands
        sub_commands = module_info.get('sub_commands', {})
        if sub_commands:
            parameters["properties"]["action"] = {
                "type": "string",
                "description": f"Action to perform. Available: {', '.join(sub_commands.keys())}",
                "enum": list(sub_commands.keys())
            }
        
        return {
            "type": "function",
            "function": {
                "name": function_name,
                "description": enhanced_description,
                "parameters": parameters
            }
        }
    
    def _create_sub_function(self, module_name: str, sub_name: str, sub_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create function definition for a sub-command."""
        function_name = f"{module_name}_{sub_name}"
        self.function_handlers[function_name] = sub_info['function']
        
        # Build parameters from sub_info
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        # Extract parameters from sub_info - try different formats
        if 'parameters' in sub_info:
            # New format with detailed parameter definitions
            sub_params = sub_info['parameters']
            if isinstance(sub_params, dict):
                for param_name, param_info in sub_params.items():
                    if isinstance(param_info, dict):
                        parameters["properties"][param_name] = {
                            "type": param_info.get('type', 'string'),
                            "description": param_info.get('description', f'Parameter {param_name}')
                        }
                        if param_info.get('required', False):
                            parameters["required"].append(param_name)
        elif 'params_desc' in sub_info:
            # Legacy format with description string like '<seconds>' or '<datetime> <note>'
            params_desc = sub_info['params_desc'].strip()
            if params_desc:
                # Parse simple parameter descriptions
                if params_desc.startswith('<') and params_desc.endswith('>') and params_desc.count('<') == 1:
                    # Single parameter like '<seconds>'
                    param_name = params_desc[1:-1]
                    param_description = self._get_enhanced_param_description(sub_name, param_name)
                    parameters["properties"][param_name] = {
                        "type": "string",
                        "description": param_description
                    }
                    parameters["required"].append(param_name)
                elif '<' in params_desc:
                    # Multiple parameters like '<datetime> <note>'
                    import re
                    param_matches = re.findall(r'<([^>]+)>', params_desc)
                    for param in param_matches:
                        param_description = self._get_enhanced_param_description(sub_name, param)
                        parameters["properties"][param] = {
                            "type": "string", 
                            "description": param_description
                        }
                        parameters["required"].append(param)
                else:
                    # Generic parameter description
                    parameters["properties"]["params"] = {
                        "type": "string",
                        "description": params_desc or f"Parameters for {sub_name} command"
                    }
        
        # Fallback to generic params if no specific parameters defined
        if not parameters["properties"]:
            parameters["properties"]["params"] = {
                "type": "string",
                "description": f"Parameters for {sub_name} command"
            }
        
        # Enhanced description for better OpenAI understanding
        base_description = sub_info.get('description', f'{module_name} {sub_name} command')
        enhanced_description = self._enhance_function_description(module_name, sub_name, base_description)
        
        return {
            "type": "function",            "function": {                "name": function_name,
                "description": enhanced_description,
                "parameters": parameters
            }
        }

    def _enhance_main_function_description(self, module_name: str, base_description: str) -> str:
        """Enhance main function descriptions for better OpenAI understanding."""
        
        enhanced_main_descriptions = {
            'core': 'Core functionality module for timers, calendar events, reminders, shopping lists, and to-do tasks. Use this when user wants to manage time, schedule, or organize tasks',
            'memory': 'Long-term memory management module. Use this when user wants to save, remember, recall, or manage stored information',
            'search': 'Internet search module. Use this when user wants to search for information online, find facts, or research topics',
            'music': 'Music control module for playing, pausing, skipping tracks on Spotify or using media keys. Use when user wants to control music playback'
        }
        
        if module_name in enhanced_main_descriptions:
            return enhanced_main_descriptions[module_name]
        
        return base_description

    def _enhance_function_description(self, module_name: str, sub_name: str, base_description: str) -> str:
        """Enhance function descriptions for better OpenAI understanding."""
        
        # Enhanced descriptions for common functions
        enhanced_descriptions = {
            'core': {                'set_timer': 'Set a countdown timer for a specified duration in seconds. Use this when user wants to set a timer, minutnik, stoper, or countdown',
                'timer': 'Set a countdown timer for a specified duration in seconds. Use this when user wants to set a timer, minutnik, stoper, or countdown',                'view_timers': 'View all active timers and their remaining time. Use this when user wants to check active timers',
                'timers': 'View all active timers and their remaining time. Use this when user wants to check active timers',                'add_event': 'Add a calendar event with date and description. Use for scheduling appointments, meetings, or events',
                'event': 'Add a calendar event with date and description. Use for scheduling appointments, meetings, or events',
                'set_reminder': 'Set a reminder for a specific date and time with a note. Use when user wants to be reminded about something',
                'reminder': 'Set a reminder for a specific date and time with a note. Use when user wants to be reminded about something',
                'add_item': 'Add an item to the shopping list. Use when user wants to add something to buy or purchase',
                'item': 'Add an item to the shopping list. Use when user wants to add something to buy or purchase',
                'add_task': 'Add a task to the to-do list. Use when user wants to add something to do or complete',
                'task': 'Add a task to the to-do list. Use when user wants to add something to do or complete'
            },            'memory': {
                'add': 'Save information to long-term memory. Use when user wants to remember, store, or save something for later',
                'get': 'Retrieve information from long-term memory. Use when user asks to recall, remember, or check stored information',
                'show': 'Retrieve information from long-term memory. Use when user asks to recall, remember, or check stored information',
                'check': 'Retrieve information from long-term memory. Use when user asks to recall, remember, or check stored information'
            },
            'search': {
                'main': 'Search the internet for information and provide summarized results. Use when user asks to search, find, or look up information online'
            }
        }
        
        if module_name in enhanced_descriptions and sub_name in enhanced_descriptions[module_name]:
            return enhanced_descriptions[module_name][sub_name]
        
        # Fallback to original description
        return base_description

    def _get_enhanced_param_description(self, sub_name: str, param_name: str) -> str:
        """Get enhanced parameter descriptions for better OpenAI understanding."""
        
        param_descriptions = {
            'seconds': 'Duration in seconds for the timer (e.g., 60 for 1 minute, 300 for 5 minutes)',
            'datetime': 'Date and time in ISO format (e.g., 2025-05-30T14:30:00)',
            'note': 'Text note or description for the reminder',
            'desc': 'Description or details for the event',
            'item': 'Name of the item to add to the shopping list',
            'task': 'Description of the task to add to the to-do list',
            'task_number': 'Number of the task to complete or remove'
        }
        
        if param_name in param_descriptions:
            return param_descriptions[param_name]
        
        return f"The {param_name} parameter for {sub_name} command"

    def execute_function(self, function_name: str, arguments: Dict[str, Any], 
                        conversation_history: Optional[deque] = None,
                        user: Optional[str] = None,
                        assistant = None) -> Any:
        """Execute a function call."""
        if function_name not in self.function_handlers:
            logger.error(f"Function {function_name} not found in handlers")
            return f"Error: Function {function_name} not found"
        
        handler = self.function_handlers[function_name]
        
        try:
            # Prepare arguments for the handler
            kwargs = {}
            
            # Handle different argument patterns based on function naming
            if function_name.endswith('_main'):
                # Main module handler - check if it has action parameter
                if 'action' in arguments:
                    # For main handlers with action/sub-command selection
                    kwargs['params'] = {
                        'action': arguments['action'],
                        **{k: v for k, v in arguments.items() if k != 'action'}
                    }
                elif 'params' in arguments:
                    kwargs['params'] = arguments['params']
                else:
                    # Pass all arguments as params
                    kwargs['params'] = arguments if len(arguments) > 1 else (list(arguments.values())[0] if arguments else "")
            else:
                # Sub-command handler - handle structured parameters
                if 'params' in arguments:
                    # Generic params field
                    kwargs['params'] = arguments['params']
                elif len(arguments) == 1:
                    # Single parameter - pass directly
                    kwargs['params'] = list(arguments.values())[0]
                elif len(arguments) == 0:
                    kwargs['params'] = ""
                else:
                    # Multiple named parameters - try to construct appropriate format
                    # Check if function expects structured parameters
                    import inspect
                    handler_sig = inspect.signature(handler)
                    params_param = handler_sig.parameters.get('params')
                    
                    if params_param and params_param.annotation in (str, inspect.Parameter.empty):
                        # Handler expects string params - join them
                        if all(isinstance(v, (str, int, float)) for v in arguments.values()):
                            kwargs['params'] = ' '.join(str(v) for v in arguments.values())
                        else:
                            kwargs['params'] = str(arguments)
                    else:
                        # Handler might accept dict params
                        kwargs['params'] = arguments
            
            # Add additional context if handler supports it
            import inspect
            sig = inspect.signature(handler)
            if 'conversation_history' in sig.parameters:
                kwargs['conversation_history'] = conversation_history
            if 'user' in sig.parameters:
                kwargs['user'] = user
            if 'assistant' in sig.parameters and assistant:
                kwargs['assistant'] = assistant
            
            # Execute the handler
            result = handler(**kwargs)
            
            # Handle async results
            import asyncio
            if asyncio.iscoroutine(result):
                # This is async but we're in sync context - need to handle this properly
                # For now, we'll need to refactor the calling code to be async
                logger.warning(f"Function {function_name} returned async result but we're in sync context")
                # Return a placeholder - this needs proper async handling
                return "Async function execution initiated"
            
            logger.info(f"Function {function_name} executed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}", exc_info=True)
            return f"Error executing {function_name}: {str(e)}"


def convert_module_system_to_function_calling(modules: Dict[str, Any]) -> FunctionCallingSystem:
    """Convert the entire module system to function calling format."""
    return FunctionCallingSystem(modules)
