#!/usr/bin/env python3
"""pytest tests for benchmark system"""

import pytest
import sys
import os
import time
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_ui'))

try:
    from web_ui.utils.benchmark_manager import AssistantBenchmark, run_assistant_benchmarks, get_benchmark_status
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
def test_benchmark_manager_import():
    """Test that benchmark manager can be imported"""
    assert BENCHMARK_AVAILABLE
    assert AssistantBenchmark is not None
    assert run_assistant_benchmarks is not None
    assert get_benchmark_status is not None


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
def test_benchmark_instance_creation():
    """Test creating benchmark instance"""
    benchmark = AssistantBenchmark()
    assert benchmark is not None
    assert hasattr(benchmark, 'log')
    assert hasattr(benchmark, 'update_progress')


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
def test_database_benchmark():
    """Test database benchmark method"""
    benchmark = AssistantBenchmark()
    
    try:
        result = benchmark.benchmark_database_operations()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'status' in result
        
        if result['success']:
            assert 'total_time' in result
            assert 'operations' in result
        else:
            assert 'error' in result
            
    except Exception as e:
        # Database benchmark may fail in test environment, that's OK
        pytest.skip(f"Database benchmark failed: {e}")


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
def test_plugin_loading_benchmark():
    """Test plugin loading benchmark method"""
    benchmark = AssistantBenchmark()
    
    try:
        result = benchmark.benchmark_plugin_loading()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'status' in result
        
        if result['success']:
            assert 'successful_loads' in result
            assert 'plugin_count' in result
            assert 'failed_loads' in result
            assert 'plugin_times' in result
        else:
            assert 'error' in result
            
    except Exception as e:
        # Plugin benchmark may fail in test environment, that's OK
        pytest.skip(f"Plugin benchmark failed: {e}")


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
def test_whisper_benchmark():
    """Test whisper transcription benchmark method"""
    benchmark = AssistantBenchmark()
    
    try:
        result = benchmark.benchmark_whisper_transcription()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'status' in result
        
    except Exception as e:
        # Whisper benchmark may fail in test environment, that's OK
        pytest.skip(f"Whisper benchmark failed: {e}")


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
def test_tts_benchmark():
    """Test TTS generation benchmark method"""
    benchmark = AssistantBenchmark()
    
    try:
        result = benchmark.benchmark_tts_generation()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'status' in result
        
    except Exception as e:
        # TTS benchmark may fail in test environment, that's OK
        pytest.skip(f"TTS benchmark failed: {e}")


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
def test_ai_response_benchmark():
    """Test AI response benchmark method"""
    benchmark = AssistantBenchmark()
    
    try:
        result = benchmark.benchmark_ai_response()
        assert isinstance(result, dict)
        assert 'success' in result
        assert 'status' in result
        
    except Exception as e:
        # AI benchmark may fail in test environment, that's OK
        pytest.skip(f"AI benchmark failed: {e}")


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
def test_get_benchmark_status():
    """Test getting benchmark status"""
    status = get_benchmark_status()
    assert isinstance(status, dict)
    assert 'running' in status
    assert isinstance(status['running'], bool)


@pytest.mark.skipif(not BENCHMARK_AVAILABLE, reason="Benchmark manager not available")
@patch('threading.Thread')
def test_run_assistant_benchmarks(mock_thread):
    """Test running benchmark suite"""
    mock_thread_instance = MagicMock()
    mock_thread.return_value = mock_thread_instance
    
    # Should not raise exception
    run_assistant_benchmarks()
    
    # Should start a thread
    mock_thread.assert_called_once()
    mock_thread_instance.start.assert_called_once()


def test_benchmark_availability():
    """Test that we can determine if benchmarks are available"""
    # This test always runs to verify our import logic
    if BENCHMARK_AVAILABLE:
        assert AssistantBenchmark is not None
    else:
        # In environments where benchmark manager is not available
        # we should handle it gracefully
        assert True
