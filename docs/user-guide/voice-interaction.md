# Voice Interaction Guide

This guide provides detailed instructions on using Asystent's voice interaction capabilities.

## Wake Word Detection

Asystent listens for a specific wake word to activate. By default, this is set to "asystent" but can be customized in the configuration.

### How Wake Word Detection Works

1. The system continuously monitors audio input
2. When it detects the wake word, you'll hear an activation beep
3. After the beep, speak your command or question
4. Wait for the assistant to process and respond

### Tips for Effective Wake Word Detection

- Speak clearly and at a normal pace
- Ensure you're in a relatively quiet environment
- Position yourself within 1-2 meters of the microphone
- Use the manual activation button if the wake word isn't being detected

## Voice Commands

Asystent understands a wide range of natural language commands. Here are some examples:

### General Information
- "What time is it?"
- "What's the weather like today?"
- "Tell me about [topic]"

### System Control
- "Turn on screen capture"
- "Enable deep reasoning mode"
- "Save this to memory"

### Memory Commands
- "Remember that [information]"
- "What do you remember about [topic]?"
- "Forget about [specific memory]"

## Voice Settings

You can customize the voice interaction experience:

### Microphone Selection
1. Go to the Configuration page
2. Find the "Microphone Device" dropdown
3. Select your preferred microphone
4. Save configuration

### Voice Recognition Model
Asystent supports two voice recognition systems:

- **Vosk**: Offline, lightweight recognition
- **Whisper**: Higher accuracy but may require more resources

To configure:
1. Go to Configuration
2. Toggle "Use Whisper for Command" based on your preference
3. Save configuration

## Troubleshooting Voice Issues

### Wake Word Not Detected
- Check that your microphone is properly connected
- Verify the correct microphone is selected in configuration
- Try speaking slightly louder or clearer
- Manual activation is always available as a backup

### Poor Voice Recognition
- Check for background noise
- Ensure the correct language model is selected
- Try adjusting your distance from the microphone
- Consider using a better quality microphone

### System Doesn't Respond After Wake Word
- Check system status on dashboard
- Look for errors in logs
- Restart the assistant process
- Verify that required models are properly installed
