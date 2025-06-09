"""
Test script for OpenAI function calling debug
"""
import asyncio
import json
import logging
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_function_calling():
    """Test OpenAI function calling with debug information."""
    
    try:
        # Import modules
        from server.plugin_manager import plugin_manager
        from server.function_calling_system import FunctionCallingSystem
        from server.ai_module import chat_with_providers
        from server.config_loader import load_config
        
        # Load config
        config = load_config()
        api_key = config.get("api_keys", {}).get("openai")
        if not api_key:
            print("❌ No OpenAI API key found!")
            return
        
        print("✅ OpenAI API key found")
        
        # Initialize plugin manager
        await plugin_manager.discover_plugins()
        
        # Enable core plugin for user 1
        await plugin_manager.enable_plugin_for_user("1", "core_module")
        
        print(f"📋 Available plugins: {list(plugin_manager.plugins.keys())}")
        print(f"🔧 Function registry: {list(plugin_manager.function_registry.keys())}")
        
        # Create function calling system
        function_calling_system = FunctionCallingSystem()
        functions = function_calling_system.convert_modules_to_functions()
        
        print(f"🎯 Converted {len(functions)} functions:")
        for func in functions:
            print(f"  - {func['function']['name']}: {func['function']['description']}")
        
        # Test message - something that should trigger a function call
        messages = [
            {
                "role": "system",
                "content": "You are GAJA, an AI assistant. When users ask about time, timers, or scheduling, use the available functions. Always use function calls when appropriate rather than just giving generic responses."
            },
            {
                "role": "user", 
                "content": "What time is it now?"
            }
        ]
        
        print("🚀 Testing OpenAI function calling...")
        print(f"📝 Message: {messages[-1]['content']}")
        
        # Make API call
        response = chat_with_providers(
            model="gpt-4.1-nano",
            messages=messages,
            functions=functions,
            function_calling_system=function_calling_system,
            provider_override="openai"
        )
        
        print("\n📦 OpenAI Response:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        # Check if tool calls were executed
        if response and response.get("tool_calls_executed"):
            print(f"✅ Function calls executed: {response['tool_calls_executed']}")
        else:
            print("⚠️ No function calls were executed")
            
        # Test another message that should definitely trigger a function call
        print("\n" + "="*50)
        print("🔄 Testing with explicit timer request...")
        
        messages2 = [
            {
                "role": "system",
                "content": "You are GAJA, an AI assistant. When users ask about timers, use the set_timer function. Always use function calls when appropriate."
            },
            {
                "role": "user",
                "content": "Set a timer for 60 seconds please"
            }
        ]
        
        response2 = chat_with_providers(
            model="gpt-4.1-nano",
            messages=messages2,
            functions=functions,
            function_calling_system=function_calling_system,
            provider_override="openai"
        )
        
        print("\n📦 Timer Test Response:")
        print(json.dumps(response2, indent=2, ensure_ascii=False))
        
        if response2 and response2.get("tool_calls_executed"):
            print(f"✅ Function calls executed: {response2['tool_calls_executed']}")
        else:
            print("⚠️ No function calls were executed")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_function_calling())
            result = await chat_ai(
                query,
                conversation_history=conversation_history,
                user_id=1,
                modules=user_plugins,
                use_function_calling=True
            )
            
            print(f"Response: {result}")
            
            # Parse the response
            try:
                parsed_result = json.loads(result)
                if parsed_result.get("command"):
                    print(f"Command executed: {parsed_result['command']}")
                    print(f"Parameters: {parsed_result['params']}")
                    
                # Add to conversation history
                conversation_history.append({"role": "user", "content": query})
                conversation_history.append({"role": "assistant", "content": parsed_result.get("text", result)})
                    
            except json.JSONDecodeError:
                print(f"Non-JSON response: {result}")
                conversation_history.append({"role": "user", "content": query})
                conversation_history.append({"role": "assistant", "content": result})
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        # Keep conversation history manageable
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]
        
        print("-" * 40)

async def test_function_registry():
    """Test the function registry conversion."""
    
    print("\n" + "="*60)
    print("TESTING FUNCTION REGISTRY")
    print("="*60)
    
    # Initialize plugin manager
    plugin_manager = PluginManager()
    await plugin_manager.initialize()
    
    # Get plugins for user 1
    user_plugins = await plugin_manager.get_modules_for_user(1)
      # Create function calling system
    from server.function_calling_system import convert_module_system_to_function_calling
    function_calling_system = convert_module_system_to_function_calling(user_plugins)
    
    # Get OpenAI functions
    functions = function_calling_system.convert_modules_to_functions()
    
    print(f"Converted {len(functions)} functions:")
    for func in functions:
        print(f"  - {func['function']['name']}: {func['function']['description']}")
        
    print("\nFunction calling system handler registry:")
    for name, handler in function_calling_system.function_handlers.items():
        print(f"  - {name}: {handler}")

if __name__ == "__main__":
    asyncio.run(test_function_registry())
    asyncio.run(test_function_calling())
