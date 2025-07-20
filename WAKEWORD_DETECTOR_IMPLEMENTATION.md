# Wake Word Detector Implementation

## Overview

This document describes the implementation of the wake word detector module for the GAJA Assistant, based on the legacy working code. The implementation follows AGENTS.md guidelines for asynchronous, testable, and modular code.

## Features

### Core Functionality

- **OpenWakeWord Integration**: Uses ONNX models for accurate wake word detection
- **Voice Activity Detection (VAD)**: Simple amplitude-based detection for command recording
- **Manual Trigger Support**: Allows manual activation via threading events
- **Async/Await Compatible**: Full async wrapper support as required by AGENTS.md
- **Fallback Error Handling**: Graceful degradation when dependencies are missing

### Audio Processing

- **Sample Rate**: 16 kHz (optimized for Whisper ASR and OpenWakeWord)
- **Chunk Processing**: 50ms chunks for real-time processing
- **Command Recording**: Up to 7 seconds with silence detection
- **Multiple Audio Formats**: int16 for OpenWakeWord, float32 for Whisper

## Architecture

### Main Components

1. **record_command_audio()**: Synchronous audio recording with VAD
2. **record_command_audio_async()**: Async wrapper for above
3. **run_wakeword_detection()**: Main detection loop with OpenWakeWord
4. **run_wakeword_detection_async()**: Async wrapper for main loop

### Dependencies

- **sounddevice**: Audio capture from microphone
- **openwakeword**: ML-based wake word detection
- **numpy**: Audio data processing
- **asyncio**: Async/await support

### Resource Structure

```
F:\Asystent\
├── resources\
│   └── openWakeWord\
│       ├── gaia.onnx           # Wake word models
│       ├── gai_uh.onnx
│       ├── Gaja1.onnx
│       ├── ga_ya.onnx
│       ├── melspectrogram.onnx # Required preprocessing
│       └── embedding_model.onnx # Optional (not used)
└── client\
    └── audio_modules\
        └── wakeword_detector.py
```

## Configuration Parameters

### Audio Constants

```python
SAMPLE_RATE = 16000                    # Hz - Standard for ASR/WakeWord
CHUNK_DURATION_MS = 50                 # Chunk size for processing
COMMAND_RECORD_TIMEOUT_SECONDS = 7     # Max command recording time
MIN_COMMAND_AUDIO_CHUNKS = 40          # Min chunks for valid command
VAD_SILENCE_AMPLITUDE_THRESHOLD = 0.01 # VAD silence threshold
```

### OpenWakeWord Parameters

- **Sensitivity Threshold**: Configurable detection sensitivity (0.0-1.0)
- **Model Framework**: ONNX for performance
- **Expected Frame Length**: Auto-detected from model

## Usage

### Basic Usage

```python
import asyncio
import threading
from client.audio_modules.wakeword_detector import run_wakeword_detection_async

# Setup events
manual_trigger = threading.Event()
stop_event = threading.Event()

# Async callback for processing queries
async def process_query(query: str):
    print(f"Processing: {query}")

# Run detection
await run_wakeword_detection_async(
    mic_device_id=None,  # Auto-detect
    stt_silence_threshold_ms=2000,
    wake_word_config_name="gaja",
    tts_module=None,
    process_query_callback_async=process_query,
    async_event_loop=asyncio.get_event_loop(),
    oww_sensitivity_threshold=0.6,
    whisper_asr_instance=whisper_instance,
    manual_listen_trigger_event=manual_trigger,
    stop_detector_event=stop_event
)
```

### Manual Trigger

```python
# Trigger listening without wake word
manual_trigger.set()
```

### Stopping Detection

```python
# Stop the detection loop
stop_event.set()
```

## Error Handling

### Graceful Degradation

- **No SoundDevice**: Logs error and returns None
- **No OpenWakeWord**: Logs warning and disables detection
- **No Models**: Checks for required ONNX files
- **Audio Errors**: Plays error beep and continues

### Device Discovery

- **Auto-Detection**: Finds default input device automatically
- **Host API Integration**: Uses system's preferred audio device
- **Fallback Logic**: Falls back to first available input device

## Testing

### Manual Testing

```bash
python test_wakeword_manual.py
```

### Unit Tests

```bash
python -m pytest tests/test_wakeword_detector.py -v
```

### Integration Testing

The module includes comprehensive tests covering:

- Basic imports and constants
- Configuration compatibility
- SoundDevice availability
- OpenWakeWord model loading
- Async function behavior
- Error conditions

## Performance Characteristics

### Real-time Performance

- **Latency**: ~50ms processing chunks
- **Memory Usage**: Minimal buffering (3 seconds max)
- **CPU Usage**: Optimized ONNX inference
- **Background Processing**: Non-blocking audio callbacks

### Resource Requirements

- **Memory**: ~50MB for loaded models
- **Storage**: ~10MB for ONNX models
- **Network**: None (fully offline)

## Troubleshooting

### Common Issues

1. **"sounddevice not available"**

   - Install: `pip install sounddevice`
   - Check audio drivers

2. **"openwakeword library import failed"**

   - Install: `pip install openwakeword`
   - Verify ONNX runtime

3. **"Model directory not found"**

   - Ensure `resources/openWakeWord/` exists
   - Check file permissions

4. **"No custom ONNX models found"**
   - Verify .onnx files in model directory
   - Check melspectrogram.onnx presence

### Debug Logging

Enable debug logging to troubleshoot:

```python
import logging
logging.getLogger('client.audio_modules.wakeword_detector').setLevel(logging.DEBUG)
```

## Implementation Notes

### AGENTS.md Compliance

- ✅ **Asynchronous**: Full async/await wrapper support
- ✅ **Testable**: Comprehensive unit tests with mocking
- ✅ **Modular**: Clean separation of concerns
- ✅ **Type Hints**: Full type annotation
- ✅ **Documentation**: Docstrings for all functions
- ✅ **Error Handling**: Graceful degradation
- ✅ **Logging**: Structured logging throughout

### Legacy Compatibility

This implementation maintains compatibility with the legacy working detector while adding:

- Modern async/await patterns
- Better error handling
- Improved testability
- Cleaner architecture
- Enhanced logging

## Future Improvements

### Planned Features

- [ ] Multiple wake word support
- [ ] Dynamic sensitivity adjustment
- [ ] Performance metrics collection
- [ ] Custom model training support
- [ ] Real-time audio visualization

### Optimization Opportunities

- [ ] GPU acceleration for inference
- [ ] Advanced VAD algorithms
- [ ] Noise cancellation integration
- [ ] Adaptive threshold tuning
- [ ] Power-efficient mobile support
