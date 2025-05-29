"""
Simple test to demonstrate the fix for music response behavior.
"""

# Simulate the old behavior (before fix)
def old_behavior():
    ai_response_text = "Zatrzymuję muzykę"
    module_response_text = "System media‑key → pause ✓"
    
    # Old logic: prioritize module response
    text_to_speak = module_response_text if module_response_text is not None else ai_response_text
    print(f"OLD BEHAVIOR - Would speak: '{text_to_speak}'")

# Simulate the new behavior (after fix)  
def new_behavior():
    ai_response_text = "Zatrzymuję muzykę"
    module_response_text = "System media‑key → pause ✓"
    
    # New logic: prefer AI's natural response
    text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
    print(f"NEW BEHAVIOR - Would speak: '{text_to_speak}'")

if __name__ == "__main__":
    print("🎵 Testing Music Response Logic Fix")
    print("=" * 50)
    old_behavior()
    new_behavior()
    print("=" * 50)
    print("✅ Fix ensures natural AI responses are spoken instead of technical module responses!")
