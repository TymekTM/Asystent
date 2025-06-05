#!/usr/bin/env python3
"""pytest tests for response logic fix demonstration"""

import pytest


def test_old_behavior_logic():
    """Test the old (incorrect) behavior logic"""
    ai_response_text = "Zatrzymuję muzykę"
    module_response_text = "System media‑key → pause ✓"
    
    # Old logic: prioritize module response
    text_to_speak = module_response_text if module_response_text is not None else ai_response_text
    
    assert text_to_speak == "System media‑key → pause ✓"


def test_new_behavior_logic():
    """Test the new (correct) behavior logic"""
    ai_response_text = "Zatrzymuję muzykę"
    module_response_text = "System media‑key → pause ✓"
    
    # New logic: prefer AI's natural response
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == "Zatrzymuję muzykę"


def test_response_logic_with_empty_ai():
    """Test response logic when AI response is empty"""
    ai_response_text = ""
    module_response_text = "System media‑key → pause ✓"
    
    # With empty AI response, should fall back to module response
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == "System media‑key → pause ✓"


def test_response_logic_with_whitespace_ai():
    """Test response logic when AI response is only whitespace"""
    ai_response_text = "   \n  \t  "
    module_response_text = "System media‑key → pause ✓"
    
    # With whitespace-only AI response, should fall back to module response
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == "System media‑key → pause ✓"


def test_response_logic_with_none_ai():
    """Test response logic when AI response is None"""
    ai_response_text = None
    module_response_text = "System media‑key → pause ✓"
    
    # With None AI response, should fall back to module response
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == "System media‑key → pause ✓"


def test_response_logic_with_none_module():
    """Test response logic when module response is None"""
    ai_response_text = "Zatrzymuję muzykę"
    module_response_text = None
    
    # Should use AI response even when module response is None
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == "Zatrzymuję muzykę"


def test_response_logic_both_empty():
    """Test response logic when both responses are empty"""
    ai_response_text = ""
    module_response_text = None
    
    # Should return empty string when both are empty/None
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == ""


def test_response_logic_both_have_content():
    """Test response logic when both responses have content"""
    ai_response_text = "Zatrzymuję muzykę"
    module_response_text = "System media‑key → pause ✓"
    
    # Should prefer AI response when both have content
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    
    assert text_to_speak == "Zatrzymuję muzykę"


def test_various_music_responses():
    """Test various music-related responses"""
    test_cases = [
        {
            'ai': "Włączam następny utwór",
            'module': "System media‑key → next ✓",
            'expected': "Włączam następny utwór"
        },
        {
            'ai': "Wstrzymuję odtwarzanie",
            'module': "System media‑key → pause ✓", 
            'expected': "Wstrzymuję odtwarzanie"
        },
        {
            'ai': "Odtwarzam muzykę",
            'module': "System media‑key → play ✓",
            'expected': "Odtwarzam muzykę"
        },
        {
            'ai': "",
            'module': "System media‑key → stop ✓",
            'expected': "System media‑key → stop ✓"
        }
    ]
    
    for case in test_cases:
        ai_response_text = case['ai']
        module_response_text = case['module']
        expected = case['expected']
        
        text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
        
        assert text_to_speak == expected


def test_fix_demonstration():
    """Demonstrate the complete fix"""
    # Before fix: technical responses were spoken
    # After fix: natural AI responses are preferred
    
    scenarios = [
        ("zatrzymaj muzykę", "Zatrzymuję muzykę", "System media‑key → pause ✓"),
        ("play music", "Playing music", "System media‑key → play ✓"),
        ("next song", "Włączam następny utwór", "System media‑key → next ✓"),
    ]
    
    for query, ai_response, module_response in scenarios:
        # New behavior should prefer AI response
        text_to_speak = ai_response if ai_response and ai_response.strip() else (module_response if module_response is not None else "")
        
        # Should be the natural AI response, not the technical module response
        assert text_to_speak == ai_response
        assert text_to_speak != module_response
