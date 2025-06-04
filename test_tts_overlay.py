#!/usr/bin/env python3
"""
Test script to simulate TTS events and check if overlay displays the text correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from shared_state import save_assistant_state
import time

def test_tts_display():
    print("Starting TTS overlay test...")
    
    # Test 1: Show speaking state with text
    print("Test 1: Speaking with text")
    save_assistant_state(
        is_listening=False,
        is_speaking=True,
        wake_word_detected=False,
        last_tts_text="Cześć! Jestem Gaja, twój asystent AI.",
        is_processing=False
    )
    time.sleep(5)
    
    # Test 2: Clear speaking state
    print("Test 2: Clear speaking state")
    save_assistant_state(
        is_listening=False,
        is_speaking=False,
        wake_word_detected=False,
        last_tts_text="",
        is_processing=False
    )
    time.sleep(3)
    
    # Test 3: Another TTS message
    print("Test 3: Another TTS message")
    save_assistant_state(
        is_listening=False,
        is_speaking=True,
        wake_word_detected=False,
        last_tts_text="Jak mogę ci dzisiaj pomóc?",
        is_processing=False
    )
    time.sleep(5)
    
    # Test 4: Long message
    print("Test 4: Long TTS message")
    save_assistant_state(
        is_listening=False,
        is_speaking=True,
        wake_word_detected=False,
        last_tts_text="To jest dłuższa wiadomość testowa, która sprawdzi jak overlay radzi sobie z wyświetlaniem dłuższego tekstu. Czy wszystko działa poprawnie?",
        is_processing=False
    )
    time.sleep(7)
    
    # Test 5: Clear all
    print("Test 5: Clear all states")
    save_assistant_state(
        is_listening=False,
        is_speaking=False,
        wake_word_detected=False,
        last_tts_text="",
        is_processing=False
    )
    
    print("Test completed!")

if __name__ == "__main__":
    test_tts_display()
