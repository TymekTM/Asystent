"""
Test script for AI-powered daily briefing with memory integration.
"""
import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.daily_briefing_module import DailyBriefingModule
from config import _config, load_config

async def test_ai_briefing():
    """Test AI briefing generation with all features enabled."""
    print("Testing AI-powered daily briefing...")
      # Load configuration
    load_config()
    
    # Create test configuration with daily briefing settings
    test_config = {
        'daily_briefing': {
            'enabled': True,
            'use_ai_generation': True,
            'include_memories': True,
            'briefing_style': 'funny',
            'user_name': 'Tymek',
            'location': 'Warsaw,PL',
            'include_weather': True,
            'include_holidays': True,
            'include_calendar': True,
            'weekend_briefing': True,
            'min_interval_hours': 12
        }
    }
    
    # Create briefing module
    briefing = DailyBriefingModule(test_config)
    
    print(f"AI Generation: {briefing.use_ai_generation}")
    print(f"Memory Integration: {briefing.include_memories}")
    print(f"Style: {briefing.briefing_style}")
    
    # Generate briefing
    result = await briefing.deliver_briefing(force_delivery=True)
    
    if result:
        print(f"\n✅ Briefing generated successfully:")
        print(f"📢 {result}")
    else:
        print("❌ Failed to generate briefing")
    
    return result

async def test_template_briefing():
    """Test template-based briefing generation."""
    print("\nTesting template-based daily briefing...")
      # Load configuration
    load_config()
    
    # Create test configuration with daily briefing settings
    test_config = {
        'daily_briefing': {
            'enabled': True,
            'use_ai_generation': False,
            'include_memories': False,
            'briefing_style': 'normal',
            'user_name': 'Tymek',
            'location': 'Warsaw,PL',
            'include_weather': True,
            'include_holidays': True,
            'include_calendar': True,
            'weekend_briefing': True,
            'min_interval_hours': 12
        }
    }
    
    # Create briefing module
    briefing = DailyBriefingModule(test_config)
    
    print(f"AI Generation: {briefing.use_ai_generation}")
    print(f"Memory Integration: {briefing.include_memories}")
    print(f"Style: {briefing.briefing_style}")
    
    # Generate briefing
    result = await briefing.deliver_briefing(force_delivery=True)
    
    if result:
        print(f"\n✅ Template briefing generated successfully:")
        print(f"📢 {result}")
    else:
        print("❌ Failed to generate template briefing")
    
    return result

async def main():
    """Run all tests."""
    print("=== Daily Briefing AI Integration Test ===\n")
    
    try:
        # Test AI generation
        ai_result = await test_ai_briefing()
        
        # Test template fallback
        template_result = await test_template_briefing()
        
        print("\n=== Test Summary ===")
        print(f"AI Briefing: {'✅ Success' if ai_result else '❌ Failed'}")
        print(f"Template Briefing: {'✅ Success' if template_result else '❌ Failed'}")
        
        if ai_result or template_result:
            print("\n🎉 Daily briefing system is working!")
        else:
            print("\n⚠️ Some issues detected, check logs for details")
    
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
