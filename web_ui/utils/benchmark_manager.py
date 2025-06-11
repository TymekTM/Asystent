"""
Real Assistant Performance Benchmark Manager
===========================================

This module provides comprehensive benchmarking for actual assistant operations:
- Whisper transcription performance
- TTS generation speed  
- Plugin loading times
- AI response generation
- Database operations
- Memory usage during operations

All benchmarks measure real-world assistant performance rather than synthetic tests.
"""

import os
import sys
import time
import threading
import tempfile
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

logger = logging.getLogger(__name__)

# Global benchmark state
benchmark_status = {
    'running': False,
    'current_test': '',
    'progress': 0,
    'results': {},
    'log': '',
    'summary': '',
    'start_time': None,
    'end_time': None,
    'errors': []
}

benchmark_lock = threading.Lock()

class AssistantBenchmark:
    """Main benchmark class for assistant performance testing."""
    
    def __init__(self):
        self.results = {}
        self.log_messages = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.log_messages.append(log_entry)
        print(log_entry)
        
        # Update global status
        with benchmark_lock:
            benchmark_status['log'] += log_entry + "\\n"
    
    def update_progress(self, test_name: str, progress: int):
        """Update progress for current test."""
        with benchmark_lock:
            benchmark_status['current_test'] = test_name
            benchmark_status['progress'] = progress

    def benchmark_database_operations(self) -> Dict:
        """Benchmark database CRUD operations performance."""
        self.log("💾 Starting database operations benchmark...")
        self.update_progress("Database Operations", 10)
        
        try:
            from server.database_manager import get_database_manager
            
            operations = {}
            
            # Test database connection
            start_time = time.time()
            conn = get_database_manager().get_db_connection()
            operations['connection'] = round(time.time() - start_time, 4)
            self.update_progress("Database Operations", 30)
            
            # Test insert operation
            start_time = time.time()
            cursor = conn.execute(
                "INSERT INTO conversations (timestamp, type, content) VALUES (?, ?, ?)",
                (datetime.now().isoformat(), 'benchmark', 'test data')
            )
            conn.commit()
            insert_id = cursor.lastrowid  # Fixed: use cursor.lastrowid instead of conn.lastrowid
            operations['insert'] = round(time.time() - start_time, 4)
            self.update_progress("Database Operations", 60)
            
            # Test select operation
            start_time = time.time()
            cursor = conn.execute("SELECT * FROM conversations WHERE id = ?", (insert_id,))
            result = cursor.fetchone()
            operations['select'] = round(time.time() - start_time, 4)
            self.update_progress("Database Operations", 80)
            
            # Test delete operation
            start_time = time.time()
            conn.execute("DELETE FROM conversations WHERE id = ?", (insert_id,))
            conn.commit()
            operations['delete'] = round(time.time() - start_time, 4)
            self.update_progress("Database Operations", 100)
            
            conn.close()
            
            total_time = sum(operations.values())
            
            self.log(f"Database operations completed in {total_time:.4f}s")
            for op, duration in operations.items():
                self.log(f"  {op}: {duration:.4f}s")
                
            return {
                'success': True,
                'total_time': round(total_time, 4),
                'operations': operations,
                'status': 'completed'
            }
            
        except Exception as e:
            self.log(f"Database benchmark error: {e}", "ERROR")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }

    def benchmark_plugin_loading(self) -> Dict:
        """Benchmark plugin loading performance."""
        self.log("🔌 Starting plugin loading benchmark...")
        self.update_progress("Plugin Loading", 10)
        
        try:
            from config import BASE_DIR
            import importlib.util
            
            modules_dir = os.path.join(BASE_DIR, 'modules')
            plugin_times = {}
            total_start = time.time()
            
            if not os.path.exists(modules_dir):
                return {
                    'success': False,
                    'error': 'Modules directory not found',
                    'status': 'failed'
                }
            
            # Find all module files
            module_files = [f for f in os.listdir(modules_dir) 
                          if f.endswith('_module.py') and not f.startswith('__')]
            
            self.log(f"Found {len(module_files)} modules to test")
            
            loaded_count = 0
            for i, module_file in enumerate(module_files):
                module_name = module_file[:-3]  # Remove .py
                self.log(f"Loading module: {module_name}")
                
                try:
                    start_time = time.time()
                    
                    # Import module
                    spec = importlib.util.spec_from_file_location(
                        module_name, os.path.join(modules_dir, module_file)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    load_time = time.time() - start_time
                    plugin_times[module_name] = round(load_time, 4)
                    loaded_count += 1
                    
                    self.log(f"✅ {module_name}: {load_time:.4f}s")
                    
                except Exception as e:
                    plugin_times[module_name] = f"ERROR: {str(e)}"
                    self.log(f"❌ {module_name}: {str(e)}", "ERROR")
                
                # Update progress
                progress = 20 + int((i + 1) / len(module_files) * 70)
                self.update_progress("Plugin Loading", progress)
            
            total_time = time.time() - total_start
            self.update_progress("Plugin Loading", 100)
            
            return {
                'success': True,
                'total_time': round(total_time, 4),
                'loaded_modules': loaded_count,
                'total_modules': len(module_files),
                'module_times': plugin_times,
                'status': 'completed'
            }
            
        except Exception as e:
            self.log(f"Plugin loading benchmark error: {e}", "ERROR")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }

    def benchmark_whisper_transcription(self) -> Dict:
        """Benchmark Whisper transcription performance."""
        self.log("🎤 Starting Whisper transcription benchmark...")
        self.update_progress("Whisper", 10)
        
        try:
            # Add current directory to Python path for audio_modules
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            from audio_modules.whisper_asr import WhisperASR
            
            # Create a simple test audio file (1 second of silence)
            import wave
            import numpy as np
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                sample_rate = 16000
                duration = 1.0  # 1 second
                samples = int(sample_rate * duration)
                
                # Create simple sine wave for testing
                t = np.linspace(0, duration, samples, False)
                audio_data = np.sin(2 * np.pi * 440 * t) * 0.1  # 440 Hz tone, low volume
                
                # Convert to 16-bit integers
                audio_int16 = (audio_data * 32767).astype(np.int16)
                
                # Write WAV file
                with wave.open(temp_audio.name, 'w') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 2 bytes per sample
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_int16.tobytes())
                
                self.update_progress("Whisper", 30)
                
                # Test Whisper transcription
                whisper_asr = WhisperASR()
                
                start_time = time.time()
                result = whisper_asr.transcribe_audio(temp_audio.name)
                transcription_time = time.time() - start_time
                
                self.update_progress("Whisper", 100)
                
                # Clean up
                os.unlink(temp_audio.name)
                
                return {
                    'success': True,
                    'transcription_time': round(transcription_time, 3),
                    'audio_duration': duration,
                    'real_time_factor': round(transcription_time / duration, 2),
                    'result': result if isinstance(result, str) else str(result),
                    'status': 'completed'
                }
                
        except Exception as e:
            self.log(f"Whisper benchmark error: {e}", "ERROR")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }

    def benchmark_tts_generation(self) -> Dict:
        """Benchmark TTS generation performance."""
        self.log("🔊 Starting TTS generation benchmark...")
        self.update_progress("TTS", 10)
        
        try:
            # Add current directory to Python path for audio_modules
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
                
            from audio_modules.tts_module import TTSModule
            
            tts = TTSModule()
            test_text = "This is a test of the text to speech system."
            
            self.update_progress("TTS", 50)
            
            start_time = time.time()
            audio_data = tts.synthesize(test_text)
            generation_time = time.time() - start_time
            
            self.update_progress("TTS", 100)
            
            chars_per_second = len(test_text) / generation_time if generation_time > 0 else 0
            
            return {
                'success': True,
                'generation_time': round(generation_time, 3),
                'text_length': len(test_text),
                'chars_per_second': round(chars_per_second, 1),
                'audio_generated': audio_data is not None,
                'status': 'completed'
            }
            
        except Exception as e:
            self.log(f"TTS benchmark error: {e}", "ERROR")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }

    def benchmark_ai_response(self) -> Dict:
        """Benchmark AI response generation performance."""
        self.log("🤖 Starting AI response benchmark...")
        self.update_progress("AI Response", 10)
        
        test_query = "What is the capital of Poland?"
        
        try:
            # Add current directory to Python path
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            from assistant import get_assistant_instance
            
            # Create assistant instance
            assistant = get_assistant_instance()
            
            if hasattr(assistant, 'ai_module') and assistant.ai_module:
                self.log("Testing AI response generation")
                self.update_progress("AI Response", 50)
                
                start_time = time.time()
                
                try:
                    # Test AI response
                    response = assistant.ai_module.process_query(test_query)
                    response_time = time.time() - start_time
                    
                    response_length = len(response) if isinstance(response, str) else 0
                    
                    self.update_progress("AI Response", 100)
                    
                    return {
                        'success': True,
                        'response_time': round(response_time, 3),
                        'query_length': len(test_query),
                        'response_length': response_length,
                        'chars_per_second': round(response_length / response_time, 1) if response_time > 0 else 0,
                        'response_preview': response[:100] if isinstance(response, str) else str(response)[:100],
                        'status': 'completed'
                    }
                    
                except Exception as e:
                    self.log(f"AI response error: {e}", "ERROR")
                    return {
                        'success': False,
                        'error': str(e),
                        'status': 'failed'
                    }
            else:
                self.log("AI module not available", "WARNING")
                self.update_progress("AI Response", 100)
                return {
                    'success': False,
                    'error': 'AI module not initialized or not available',
                    'status': 'skipped',
                    'reason': 'Module not loaded'
                }
                
        except Exception as e:
            self.log(f"AI response benchmark error: {e}", "ERROR")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed'
            }

    def run_full_benchmark(self) -> Dict:
        """Run all benchmarks and return consolidated results."""
        self.log("🚀 Starting comprehensive assistant benchmark suite...")
        start_time = time.time()
        
        with benchmark_lock:
            benchmark_status['running'] = True
            benchmark_status['start_time'] = start_time
            benchmark_status['results'] = {}
            benchmark_status['errors'] = []
            benchmark_status['log'] = ''
        
        benchmarks = [
            ('whisper', self.benchmark_whisper_transcription),
            ('tts', self.benchmark_tts_generation),
            ('plugins', self.benchmark_plugin_loading),
            ('ai_response', self.benchmark_ai_response),
            ('database', self.benchmark_database_operations)
        ]
        
        passed_tests = 0
        total_tests = len(benchmarks)
        
        for test_name, benchmark_func in benchmarks:
            self.log(f"\\n{'='*50}")
            self.log(f"Running {test_name} benchmark...")
            
            try:
                result = benchmark_func()
                self.results[test_name] = result
                
                with benchmark_lock:
                    benchmark_status['results'][test_name] = result
                
                if result.get('success', False):
                    passed_tests += 1
                    self.log(f"✅ {test_name} benchmark completed successfully")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self.log(f"❌ {test_name} benchmark failed: {error_msg}", "ERROR")
                    with benchmark_lock:
                        benchmark_status['errors'].append(f"{test_name}: {error_msg}")
                        
            except Exception as e:
                error_msg = f"Unexpected error in {test_name}: {str(e)}"
                self.log(error_msg, "ERROR")
                self.results[test_name] = {
                    'success': False,
                    'error': str(e),
                    'status': 'failed'
                }
                with benchmark_lock:
                    benchmark_status['results'][test_name] = self.results[test_name]
                    benchmark_status['errors'].append(error_msg)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Generate summary
        summary = f"Benchmark completed: {passed_tests}/{total_tests} tests passed"
        self.log(f"\\n{'='*50}")
        self.log(f"🏁 BENCHMARK COMPLETE")
        self.log(f"Total duration: {total_duration:.2f} seconds")
        self.log(summary)
        
        # Log individual results
        for test_name, result in self.results.items():
            status = "✅" if result.get('success', False) else "❌"
            self.log(f"{status} {test_name}: {result.get('status', 'unknown')}")
            if not result.get('success', False):
                self.log(f"    Error: {result.get('error', 'Unknown')}")
        
        with benchmark_lock:
            benchmark_status['running'] = False
            benchmark_status['end_time'] = end_time
            benchmark_status['summary'] = summary
        
        return {
            'success': passed_tests == total_tests,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'total_duration': round(total_duration, 2),
            'results': self.results,
            'summary': summary
        }

# Global functions for external access
def run_assistant_benchmarks():
    """Start benchmark suite in background thread."""
    def run_benchmarks():
        try:
            benchmark = AssistantBenchmark()
            result = benchmark.run_full_benchmark()
            return result
        except Exception as e:
            with benchmark_lock:
                benchmark_status['running'] = False
                benchmark_status['summary'] = f"Benchmark failed: {str(e)}"
            return {'success': False, 'error': str(e)}
    
    if benchmark_status['running']:
        return {'success': False, 'error': 'Benchmark already running'}
    
    thread = threading.Thread(target=run_benchmarks)
    thread.daemon = True
    thread.start()
    
    return {'success': True, 'message': 'Benchmark started'}

def get_benchmark_status():
    """Get current benchmark status."""
    with benchmark_lock:
        return benchmark_status.copy()

def clear_benchmark_results():
    """Clear benchmark results and reset status."""
    with benchmark_lock:
        benchmark_status.update({
            'running': False,
            'current_test': '',
            'progress': 0,
            'results': {},
            'log': '',
            'summary': '',
            'start_time': None,
            'end_time': None,
            'errors': []
        })
    return {'success': True, 'message': 'Benchmark results cleared'}

if __name__ == "__main__":
    # Direct execution for testing
    benchmark = AssistantBenchmark()
    result = benchmark.run_full_benchmark()
    print("\\nFinal result:", result)
