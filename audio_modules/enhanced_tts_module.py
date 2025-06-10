"""
Enhanced TTS Module with User Mode Support
Obsługuje różnych dostawców TTS w zależności od trybu użytkownika
"""

import asyncio
import logging
import os
import subprocess
import uuid
import threading
import time
import glob
from typing import Optional, Dict, Any
from pathlib import Path

# Import user modes
from user_modes import get_current_mode, get_current_config, UserMode, TTSProvider

# Optional dependencies based on mode
try:
    from edge_tts import Communicate
except ImportError:
    Communicate = None

try:
    import openai
except ImportError:
    openai = None

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None

# Handle relative imports for ffmpeg
try:
    from .ffmpeg_installer import ensure_ffmpeg_installed
except ImportError:
    try:
        from ffmpeg_installer import ensure_ffmpeg_installed
    except ImportError:
        def ensure_ffmpeg_installed():
            """Fallback function when ffmpeg_installer is not available"""
            pass

from performance_monitor import measure_performance

logger = logging.getLogger(__name__)

class EnhancedTTSModule:
    """Enhanced TTS Module z obsługą różnych trybów użytkownika."""
    
    CLEANUP_INTERVAL = 10  # seconds
    INACTIVITY_THRESHOLD = 30  # seconds
    
    def __init__(self):
        self.mute = False
        self.current_process = None
        self._last_activity = time.time()
        self._cleanup_task_started = False
        self._current_mode = None
        self._tts_providers = {}
        self._initialize_providers()
        self._start_cleanup_task()
    
    def _initialize_providers(self):
        """Inicjalizuje dostępnych dostawców TTS."""
        
        # Edge TTS Provider (Poor Man Mode)
        if Communicate is not None:
            self._tts_providers[TTSProvider.EDGE_TTS] = self._edge_tts_speak
            logger.info("Edge TTS provider initialized")
        
        # OpenAI TTS Provider (Paid User Mode)
        if openai is not None:
            self._tts_providers[TTSProvider.OPENAI_TTS] = self._openai_tts_speak
            logger.info("OpenAI TTS provider initialized")
        
        # Azure TTS Provider (Enterprise Mode)
        if speechsdk is not None:
            self._tts_providers[TTSProvider.AZURE_TTS] = self._azure_tts_speak
            logger.info("Azure TTS provider initialized")
        
        logger.info(f"Initialized {len(self._tts_providers)} TTS providers")
    
    def _start_cleanup_task(self):
        """Uruchamia zadanie czyszczenia plików tymczasowych."""
        if not self._cleanup_task_started:
            try:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._cleanup_temp_files_loop())
                except RuntimeError:
                    # No running loop, start in a background thread
                    threading.Thread(
                        target=lambda: asyncio.run(self._cleanup_temp_files_loop()), 
                        daemon=True
                    ).start()
                self._cleanup_task_started = True
            except Exception as e:
                logger.error(f"Failed to start TTS cleanup task: {e}")
    
    async def _cleanup_temp_files_loop(self):
        """Pętla czyszcząca stare pliki tymczasowe."""
        while True:
            try:
                now = time.time()
                # Only clean up if no TTS activity for INACTIVITY_THRESHOLD
                if now - self._last_activity > self.INACTIVITY_THRESHOLD:
                    pattern = os.path.join("resources", "sounds", "temp_tts_*.mp3")
                    for path in glob.glob(pattern):
                        try:
                            mtime = os.path.getmtime(path)
                            if now - mtime > self.INACTIVITY_THRESHOLD:
                                os.remove(path)
                                logger.debug(f"[TTS Cleanup] Deleted old temp file: {path}")
                        except Exception as e:
                            logger.warning(f"[TTS Cleanup] Failed to delete {path}: {e}")
            except Exception as e:
                logger.error(f"[TTS Cleanup] Error in cleanup loop: {e}")
            await asyncio.sleep(self.CLEANUP_INTERVAL)
    
    def cancel(self):
        """Anuluje aktualny proces TTS."""
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception as e:
                logger.error("Error stopping TTS: %s", e)
            self.current_process = None
    
    @measure_performance
    async def speak(self, text: str):
        """Główna metoda TTS - wybiera dostawcę na podstawie trybu użytkownika."""
        # Skip speaking if muted
        if getattr(self, 'mute', False):
            logger.debug("TTS muted, skipping speech")
            return
        
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS")
            return
        
        logger.info(f"TTS: {text}")
        
        # Get current user mode and config
        current_mode = get_current_mode()
        config = get_current_config()
        tts_provider = config.tts_provider
        
        # Check if provider is available
        if tts_provider not in self._tts_providers:
            logger.error(f"TTS provider {tts_provider.value} not available, falling back to Edge TTS")
            tts_provider = TTSProvider.EDGE_TTS
            
            if tts_provider not in self._tts_providers:
                logger.error("No TTS providers available")
                return
        
        # Update activity timestamp
        self._last_activity = time.time()
        
        # Call appropriate provider
        try:
            await self._tts_providers[tts_provider](text, config.tts_config)
        except Exception as e:
            logger.error(f"TTS error with {tts_provider.value}: {e}")
            # Try fallback to Edge TTS if available
            if tts_provider != TTSProvider.EDGE_TTS and TTSProvider.EDGE_TTS in self._tts_providers:
                logger.info("Falling back to Edge TTS")
                try:
                    await self._edge_tts_speak(text, config.tts_config)
                except Exception as fallback_e:
                    logger.error(f"Fallback TTS also failed: {fallback_e}")
    
    async def _edge_tts_speak(self, text: str, config: Dict[str, Any]):
        """Edge TTS implementation (Poor Man Mode)."""
        if Communicate is None:
            raise Exception("edge_tts library is not available")
        
        voice = config.get('voice', 'pl-PL-MarekNeural')
        rate = config.get('rate', '+0%')
        volume = config.get('volume', '+0%') 
        pitch = config.get('pitch', '+0Hz')
        
        # Create SSML if advanced settings provided
        if rate != '+0%' or volume != '+0%' or pitch != '+0Hz':
            ssml_text = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="pl-PL">
                <voice name="{voice}">
                    <prosody rate="{rate}" volume="{volume}" pitch="{pitch}">
                        {text}
                    </prosody>
                </voice>
            </speak>
            """
            communicate = Communicate(ssml_text, voice)
        else:
            communicate = Communicate(text, voice)
        
        temp_filename = f"temp_tts_{uuid.uuid4().hex}.mp3"
        temp_path = os.path.join("resources", "sounds", temp_filename)
        
        # Ensure sounds directory exists
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        try:
            # Generate speech
            await communicate.save(temp_path)
            
            # Cancel any existing playback
            self.cancel()
            
            # Ensure ffplay is available
            ensure_ffmpeg_installed()
            
            # Play the audio
            self.current_process = subprocess.Popen([
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_path
            ])
            
            # Wait for playback to complete
            await asyncio.to_thread(self.current_process.wait)
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                try:                    os.remove(temp_path)
                except PermissionError:
                    logger.warning(f"Cannot delete {temp_path}, file in use")
                except Exception as e:
                    logger.error(f"Error deleting {temp_path}: {e}")
            self.current_process = None
    
    async def _openai_tts_speak(self, text: str, config: Dict[str, Any]):
        """OpenAI TTS implementation (Paid User Mode) - używa streaming z legacy kodu."""
        if openai is None:
            raise Exception("openai library is not available")
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                from config import _config
                api_key = _config.get("API_KEYS", {}).get("OPENAI_API_KEY")
            except Exception:
                api_key = None
        if not api_key:
            raise Exception("OpenAI API key not provided")
        
        # Configuration from user mode
        model = config.get('model', 'tts-1')
        voice = config.get('voice', 'alloy')
        response_format = config.get('response_format', 'opus')  # opus for streaming
        speed = config.get('speed', 1.0)
        volume = config.get('volume', 200)  # ffplay volume
        
        client = openai.OpenAI(api_key=api_key)
        
        def _stream_and_play():
            """Streaming playback funkcja z legacy kodu."""
            ensure_ffmpeg_installed()
            try:
                with client.audio.speech.with_streaming_response.create(
                    model=model,
                    voice=voice,
                    input=text,
                    response_format=response_format,
                    speed=speed
                ) as response:
                    # Cancel any existing playback
                    self.cancel()
                    
                    # Start ffplay process with streaming input
                    self.current_process = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", 
                         "-volume", str(volume), "-i", "-"],
                        stdin=subprocess.PIPE,
                    )
                    
                    # Stream audio chunks to ffplay
                    for chunk in response.iter_bytes():
                        if self.current_process and self.current_process.stdin:
                            try:
                                self.current_process.stdin.write(chunk)
                                self.current_process.stdin.flush()
                            except BrokenPipeError:
                                break
                    
                    # Close stdin and wait for completion
                    if self.current_process and self.current_process.stdin:
                        self.current_process.stdin.close()
                    if self.current_process:
                        self.current_process.wait()
                        
            except Exception as e:
                logger.error(f"OpenAI TTS streaming error: {e}")
                raise
            finally:
                self.current_process = None
        
        # Run streaming in thread (legacy approach)
        await asyncio.to_thread(_stream_and_play)
    
    async def _azure_tts_speak(self, text: str, config: Dict[str, Any]):
        """Azure TTS implementation (Enterprise Mode)."""
        if speechsdk is None:
            raise Exception("azure-cognitiveservices-speech library is not available")
        
        # Azure TTS configuration
        region = config.get('region', 'eastus')
        voice = config.get('voice', 'pl-PL-MarekNeural')
        style = config.get('style', 'friendly')
        rate = config.get('rate', 'medium')
        volume = config.get('volume', 'medium')
        
        temp_filename = f"temp_tts_{uuid.uuid4().hex}.wav"
        temp_path = os.path.join("resources", "sounds", temp_filename)
        
        # Ensure sounds directory exists
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        try:
            # Configure Azure Speech SDK
            speech_key = os.getenv("AZURE_SPEECH_KEY")
            if not speech_key:
                raise Exception("AZURE_SPEECH_KEY environment variable not set")
            
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=region)
            audio_config = speechsdk.audio.AudioOutputConfig(filename=temp_path)
            
            # Create SSML with advanced settings
            ssml_text = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
                   xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="pl-PL">
                <voice name="{voice}">
                    <mstts:express-as style="{style}">
                        <prosody rate="{rate}" volume="{volume}">
                            {text}
                        </prosody>
                    </mstts:express-as>
                </voice>
            </speak>
            """
            
            # Generate speech
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            result = await asyncio.to_thread(synthesizer.speak_ssml_async(ssml_text).get)
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Cancel any existing playback
                self.cancel()
                
                # Ensure ffplay is available
                ensure_ffmpeg_installed()
                
                # Play the audio
                self.current_process = subprocess.Popen([
                    "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", temp_path
                ])
                
                # Wait for playback to complete
                await asyncio.to_thread(self.current_process.wait)
            else:
                raise Exception(f"Azure TTS failed: {result.reason}")
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.error(f"Error deleting {temp_path}: {e}")
            self.current_process = None

# Create global instance
_enhanced_tts_instance = EnhancedTTSModule()

# Module-level functions for compatibility
async def speak(text: str):
    """Module-level function to handle text-to-speech."""
    await _enhanced_tts_instance.speak(text)

def cancel():
    """Module-level function to cancel TTS."""
    _enhanced_tts_instance.cancel()

def set_mute(muted: bool):
    """Module-level function to mute/unmute TTS."""
    _enhanced_tts_instance.mute = muted

# Legacy compatibility
TTSModule = EnhancedTTSModule
