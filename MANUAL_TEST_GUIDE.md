# Manual Test Guide for Client Fixes

## Overview

This guide provides step-by-step instructions to manually test the fixes for the client issues.

## Issues Fixed

### 1. Daily Briefing TTS Issue

**Problem**: Daily briefing messages were not being spoken aloud
**Fix**: Enhanced TTS error handling and initialization

### 2. Settings Interface Access

**Problem**: System tray settings option was not working
**Fix**: Simplified settings access with fallback methods

### 3. Overlay Click-Through

**Problem**: Overlay was blocking clicks when active
**Fix**: Overlay is now always click-through when visible

### 4. Audio Device Configuration

**Problem**: No way to test or configure microphone and audio devices
**Fix**: Added audio device detection and testing endpoints

## Manual Testing Steps

### Test 1: Daily Briefing TTS

1. Start the client: `python client/client_main.py`
2. Wait for client to connect to server
3. Trigger a daily briefing from the server
4. **Expected**: The briefing should be spoken aloud through TTS
5. **Check**: Look for log messages indicating TTS success/failure

### Test 2: Settings Interface

1. Start the client with system tray enabled
2. Right-click on the system tray icon
3. Select "Settings" from the context menu
4. **Expected**: Settings interface should open in browser or overlay
5. **Check**: Settings page should be accessible via:
   - http://localhost:5001/settings.html
   - http://localhost:5000/settings.html (fallback)

### Test 3: Overlay Click-Through

1. Start the client and ensure overlay is running
2. Trigger the overlay to show (speak a command or test wakeword)
3. Try to click through the overlay to applications below
4. **Expected**: Clicks should pass through to applications below
5. **Check**: Overlay should never block user interaction

### Test 4: Audio Device Detection

1. Open settings interface (see Test 2)
2. Navigate to audio settings section
3. **Expected**: Should see list of available input/output devices
4. **Alternative**: Use HTTP API:
   ```bash
   curl http://localhost:5001/api/audio_devices
   ```
5. **Check**: Should return JSON with input_devices and output_devices

### Test 5: Microphone Testing

1. Open settings interface
2. Look for microphone test option
3. **Alternative**: Use HTTP API:
   ```bash
   curl http://localhost:5001/api/test_microphone
   ```
4. **Expected**: Should return success/failure status for microphone

### Test 6: TTS Testing

1. Open settings interface
2. Look for TTS test option
3. **Alternative**: Use HTTP API:
   ```bash
   curl http://localhost:5001/api/test_tts
   ```
4. **Expected**: Should play test TTS message

## API Endpoints for Testing

### Status Endpoint

```
GET http://localhost:5001/api/status
```

Returns current client status

### Audio Devices

```
GET http://localhost:5001/api/audio_devices
```

Returns available audio devices

### Test Microphone

```
GET http://localhost:5001/api/test_microphone
```

Tests microphone functionality

### Test TTS

```
GET http://localhost:5001/api/test_tts
```

Tests TTS functionality

### Settings Page

```
GET http://localhost:5001/settings.html
```

Settings interface

## Expected Log Messages

### TTS Initialization

```
Legacy TTS module initialized
TTS settings adjusted
```

### Daily Briefing

```
Daily briefing received: [text...]
Starting TTS for daily briefing...
Daily briefing spoken successfully
```

### Audio Device Detection

```
Found X input devices
Found Y output devices
```

### Settings Access

```
Settings requested from system tray
Opened settings via HTTP server
```

### Overlay Click-Through

```
[Rust] ZAWSZE włącz click-through - overlay ma być przeźroczysty
[Rust] Overlay started and hidden with click-through enabled
```

## Troubleshooting

### TTS Not Working

1. Check OpenAI API key is configured
2. Verify ffmpeg is installed
3. Check audio output device settings
4. Look for TTS initialization errors in logs

### Settings Not Opening

1. Verify HTTP server is running on port 5001 or 5000
2. Check if settings.html exists in client/resources/
3. Try accessing directly via browser

### Overlay Issues

1. Check if overlay process is running
2. Verify Tauri overlay executable exists
3. Look for overlay-related errors in logs

### Audio Device Issues

1. Verify sounddevice package is installed
2. Check system audio permissions
3. Test with different audio devices

## Verification Checklist

- [ ] Daily briefing is spoken aloud via TTS
- [ ] Settings interface opens from system tray
- [ ] Settings interface opens from HTTP endpoint
- [ ] Overlay allows click-through when visible
- [ ] Audio devices are properly detected
- [ ] Microphone testing works
- [ ] TTS testing works
- [ ] System tray shows correct status
- [ ] No overlay blocking issues
- [ ] All HTTP endpoints respond correctly

## Configuration Files

### Client Config

Location: `client/client_config.json`
Contains server URL, API keys, and component settings

### Settings

Location: `client/resources/settings.html`
Web interface for configuration

### Overlay Settings

Location: `overlay/overlay_settings.json`
Overlay-specific configuration

## Common Issues and Solutions

1. **Port conflicts**: Try different ports if 5000/5001 are in use
2. **API key missing**: Configure OpenAI API key for TTS
3. **Audio permissions**: Ensure microphone access is granted
4. **Overlay not showing**: Check if Tauri overlay process is running
5. **Click-through not working**: Verify Windows-specific implementation

## Contact and Support

If tests fail, check:

1. Log files for error messages
2. Component initialization status
3. Network connectivity
4. Audio system configuration
5. Windows permissions and security settings
