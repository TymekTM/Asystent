# Voice Interaction Guide

This guide provides detailed instructions on using Asystent's voice interaction capabilities.

## Wake Word Detection

Asystent listens for a specific wake word to activate. By default, this is set to "asystencie" but can be customized in the configuration.

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
- If using Whisper STT, wait for the beep before speaking your command

## Speech-to-Text Options

Asystent supports two STT (Speech-to-Text) systems:

### Vosk
- Operates completely offline
- Uses less system resources
- Better for simple commands and phrases
- Available in multiple languages
- Faster response time

### Whisper
- Higher accuracy for complex speech
- Better at handling background noise
- Superior multilingual capabilities
- Larger model options for better accuracy
- More resource-intensive

You can select your preferred system in the Configuration page under Voice Recognition settings.

## Voice Commands

Asystent understands a wide range of natural language commands. Here are some examples:

### General Information
- "What time is it?"
- "What's the weather like today?"
- "Tell me about [topic]"

### System Control
- "Take a screenshot and analyze it"
- "Use deep reasoning to solve this problem"
- "Save this information to memory"

### Memory Commands
- "Remember that [information]"
- "What do you remember about [topic]?"
- "Delete the memory about [specific topic]"

### Core Functions
- "Set a timer for 5 minutes"
- "Add a reminder for tomorrow at 2pm"
- "Add milk to my shopping list"

### Search Commands
- "Search the web for quantum computing"
- "Find information about healthy recipes"
- "Look up the latest news on AI development"

## Voice Settings

You can customize the voice interaction experience through the Configuration page:

### Microphone Selection
1. Go to the Configuration page
2. Find the "Microphone Device" dropdown
3. Select your preferred microphone
4. Save configuration

### Wake Word Settings
1. Navigate to Wake Word settings
2. Enter your preferred activation phrase
3. Test your new wake word
4. Save changes

### STT Engine Selection
1. Go to Voice Recognition settings
2. Choose between Vosk and Whisper
3. If using Whisper, select model size (small/medium/large)
4. Save configuration

## Troubleshooting

### Wake Word Not Detected
- Try speaking more clearly and slightly louder
- Reduce background noise in the environment
- Check that your microphone is working correctly
- Try using the manual activation button instead

### Poor Speech Recognition
- Switch between Vosk and Whisper to see which works better
- Use a higher quality microphone if available
- Speak at a moderate pace and articulate clearly
- Try adjusting the silence threshold in audio settings
- Verify the language settings match the language you're speaking

### No Response After Recognition
- Check if the assistant is connected to the AI provider
- Verify internet connection if using cloud-based AI models
- Restart the assistant if it becomes unresponsive
- Check the logs for specific error messages

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
