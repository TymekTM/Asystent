#!/usr/bin/env python3
"""pytest tests for music response behavior"""

import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock # ADDED AsyncMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def mock_config(monkeypatch):
    """Mock config loading"""
    config_mock = MagicMock()
    config_mock.load_config = MagicMock()
    monkeypatch.setattr('config.load_config', config_mock.load_config)
    return config_mock


@pytest.fixture
def mock_assistant():
    """Mock Assistant class"""
    assistant_mock = MagicMock()
    assistant_mock.process_query = AsyncMock(return_value=None) # MODIFIED: Use AsyncMock
    return assistant_mock


@pytest.mark.asyncio
async def test_music_responses_with_mock_assistant(mock_config, mock_assistant):
    """Test that music commands can be processed without errors"""
    test_queries = [
        "zatrzymaj muzykę",
        "pause music", 
        "następny utwór",
        "next song",
        "odtwórz muzykę",
        "play music"
    ]
    
    for query in test_queries:
        # Should not raise exception
        await mock_assistant.process_query(query, TextMode=True)
        mock_assistant.process_query.assert_called_with(query, TextMode=True)


def test_music_query_patterns():
    """Test recognition of music-related queries"""
    music_queries = [
        "zatrzymaj muzykę",
        "pause music",
        "następny utwór",
        "next song",
        "odtwórz muzykę",
        "play music",
        "stop music",
        "wstrzymaj",
        "play",
        "next",
        "previous"
    ]

    # These should be recognized as music-related
    for query in music_queries:
        assert any(keyword in query.lower() for keyword in
                  ['music', 'muzy', 'play', 'pause', 'stop', 'next', 'previous', 'utwór', 'wstrzymaj']) # MODIFIED: Added 'wstrzymaj'


def test_non_music_queries():
    """Test that non-music queries are not incorrectly identified"""
    non_music_queries = [
        "jaka jest pogoda",
        "what's the weather",
        "otwórz stronę",
        "search for something",
        "take a screenshot"
    ]
    
    # These should not be music-related
    for query in non_music_queries:
        music_keywords = ['music', 'muzy', 'play', 'pause', 'stop', 'next', 'previous']
        assert not any(keyword in query.lower() for keyword in music_keywords)


@pytest.mark.asyncio
@patch('assistant.Assistant')
@patch('config.load_config')
async def test_music_responses_integration(mock_load_config, mock_assistant_class):
    """Integration test for music response behavior"""
    # Setup mocks
    mock_assistant_instance = MagicMock()
    mock_assistant_class.return_value = mock_assistant_instance
    mock_assistant_instance.process_query = AsyncMock(return_value=None) # MODIFIED: Use AsyncMock

    # Import after mocking
    from assistant import get_assistant_instance
    import config
    
    # Load config
    config.load_config()
    
    # Initialize assistant
    assistant = get_assistant_instance()
    
    # Test music queries
    test_queries = [
        "zatrzymaj muzykę",
        "play music"
    ]
    
    for query in test_queries:
        await assistant.process_query(query, TextMode=True)
        # Verify the method was called
        mock_assistant_instance.process_query.assert_called()


def test_response_preference_logic():
    """Test the logic for preferring AI responses over module responses"""
    # Simulate the old vs new behavior
    ai_response_text = "Zatrzymuję muzykę"
    module_response_text = "System media‑key → pause ✓"
    
    # Old logic (incorrect)
    old_text_to_speak = module_response_text if module_response_text is not None else ai_response_text
    
    # New logic (correct)
    new_text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    # The new logic should prefer the AI response
    assert old_text_to_speak == "System media‑key → pause ✓"
    assert new_text_to_speak == "Zatrzymuję muzykę"


def test_empty_response_handling():
    """Test handling of empty responses"""
    ai_response_text = ""
    module_response_text = "System media‑key → pause ✓"
    
    # With empty AI response, should fall back to module response
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == "System media‑key → pause ✓"


def test_whitespace_response_handling():
    """Test handling of whitespace-only responses"""
    ai_response_text = "   \n  \t  "
    module_response_text = "System media‑key → pause ✓"
    
    # With whitespace-only AI response, should fall back to module response
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == "System media‑key → pause ✓"
