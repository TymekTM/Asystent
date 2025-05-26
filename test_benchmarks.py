#!/usr/bin/env python3
"""
Direct benchmark test script to verify fixes
"""

import sys
import os

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_ui'))

def test_benchmarks():
    """Test the fixed benchmark system directly."""
    print("🧪 Testing Fixed Benchmark System")
    print("=" * 50)
    
    try:        # Import the benchmark manager
        from web_ui.utils.benchmark_manager import AssistantBenchmark, run_assistant_benchmarks, get_benchmark_status
        
        print("✅ Successfully imported benchmark manager")
        
        # Create benchmark instance
        benchmark = AssistantBenchmark()
        print("✅ Created benchmark instance")
        
        # Test individual benchmarks
        print("\n🔧 Testing individual benchmark methods:")
        
        # Test database benchmark (was failing before)
        print("\n--- Testing Database Benchmark ---")
        try:
            db_result = benchmark.benchmark_database_operations()
            if db_result['success']:
                print(f"✅ Database benchmark: {db_result['status']}")
                print(f"   Total time: {db_result['total_time']}s")
                print(f"   Operations: {db_result['operations']}")
            else:
                print(f"❌ Database benchmark failed: {db_result['error']}")
        except Exception as e:
            print(f"❌ Database benchmark error: {e}")
        
        # Test plugin loading (memory module was failing)
        print("\n--- Testing Plugin Loading Benchmark ---")
        try:
            plugin_result = benchmark.benchmark_plugin_loading()
            if plugin_result['success']:
                print(f"✅ Plugin loading benchmark: {plugin_result['status']}")
                print(f"   Loaded {plugin_result['successful_loads']}/{plugin_result['plugin_count']} modules")
                print(f"   Failed modules: {plugin_result['failed_loads']}")
                for name, time_or_error in plugin_result['plugin_times'].items():
                    if isinstance(time_or_error, str) and "ERROR" in time_or_error:
                        print(f"   ❌ {name}: {time_or_error}")
                    else:
                        print(f"   ✅ {name}: {time_or_error}s")
            else:
                print(f"❌ Plugin loading benchmark failed: {plugin_result['error']}")
        except Exception as e:
            print(f"❌ Plugin loading benchmark error: {e}")
        
        # Test other benchmarks briefly
        print("\n--- Testing Other Benchmarks ---")
        
        # Whisper
        try:
            whisper_result = benchmark.benchmark_whisper_transcription()
            status = "✅" if whisper_result['success'] else "❌"
            print(f"{status} Whisper: {whisper_result['status']}")
        except Exception as e:
            print(f"❌ Whisper error: {e}")
        
        # TTS
        try:
            tts_result = benchmark.benchmark_tts_generation()
            status = "✅" if tts_result['success'] else "❌"
            print(f"{status} TTS: {tts_result['status']}")
        except Exception as e:
            print(f"❌ TTS error: {e}")
        
        # AI Response
        try:
            ai_result = benchmark.benchmark_ai_response()
            status = "✅" if ai_result['success'] else "❌"
            print(f"{status} AI Response: {ai_result['status']}")
        except Exception as e:
            print(f"❌ AI Response error: {e}")
        
        print("\n🏁 Individual benchmark tests completed!")
        
        # Now test the complete benchmark suite
        print("\n--- Testing Complete Benchmark Suite ---")
        print("Starting full benchmark suite...")
        
        start_benchmarks = run_assistant_benchmarks
        
        start_benchmarks()
        
        # Wait a moment and check status
        import time
        time.sleep(2)
        
        status = get_benchmark_status()
        print(f"Benchmark status: {status.get('summary', 'Running...')}")
        
        # Wait for completion
        max_wait = 60  # Wait up to 60 seconds
        while status.get('running', False) and max_wait > 0:
            time.sleep(2)
            max_wait -= 2
            status = get_benchmark_status()
            current_test = status.get('current_test', '')
            progress = status.get('progress', 0)
            print(f"Progress: {current_test} - {progress}%")
        
        # Show final results
        if not status.get('running', False):
            print("\n🎉 Benchmark suite completed!")
            print(f"Summary: {status.get('summary', 'No summary available')}")
            
            # Show detailed results
            results = status.get('results', {})
            for test_name, result in results.items():
                status_icon = "✅" if result.get('success') else "❌"
                test_status = result.get('status', 'unknown')
                error = result.get('error', '')
                print(f"{status_icon} {test_name}: {test_status}")
                if error:
                    print(f"    Error: {error}")
        else:
            print("⏰ Benchmark still running after timeout")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the Asystent directory")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_benchmarks()
