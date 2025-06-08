import asyncio, logging, os, subprocess, uuid, threading
try:
    from openai import OpenAI  # type: ignore
except Exception:  # openai not installed
    OpenAI = None
from performance_monitor import measure_performance

# Handle relative imports
try:
    from .ffmpeg_installer import ensure_ffmpeg_installed
except ImportError:
    try:
        from ffmpeg_installer import ensure_ffmpeg_installed
    except ImportError:
        def ensure_ffmpeg_installed():
            """Fallback function when ffmpeg_installer is not available"""
            pass

# Import TTS prompt
try:
    from prompts import TTS_VOICE_PROMPT
except ImportError:
    TTS_VOICE_PROMPT = "Speak naturally and conversationally."

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


import glob
import time

class TTSModule:
    CLEANUP_INTERVAL = 10  # seconds
    INACTIVITY_THRESHOLD = 30  # seconds

    def __init__(self):        
        # Mute flag to disable TTS in text/chat mode
        self.mute = False
        self.current_process = None
        self._last_activity = time.time()
        self._cleanup_task_started = False        # TTS configuration
        self.volume = 200  # ffplay volume (200% for louder audio)
        self.voice = "sage"  # OpenAI voice
        self.model = "gpt-4o-mini-tts"  # OpenAI TTS model (correct model name)
        # Defer cleanup task start to first use to avoid blocking initialization
        # self._start_cleanup_task()

    def _start_cleanup_task(self):
        if not self._cleanup_task_started:
            try:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._cleanup_temp_files_loop())
                except RuntimeError:
                    # No running loop, start in a background thread
                    threading.Thread(target=lambda: asyncio.run(self._cleanup_temp_files_loop()), daemon=True).start()
                self._cleanup_task_started = True
            except Exception as e:
                logger.error(f"Failed to start TTS cleanup task: {e}")

    async def _cleanup_temp_files_loop(self):
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
                                logger.info(f"[TTS Cleanup] Deleted old temp file: {path}")
                        except Exception as e:
                            logger.warning(f"[TTS Cleanup] Failed to delete {path}: {e}")
            except Exception as e:
                logger.error(f"[TTS Cleanup] Error in cleanup loop: {e}")
            await asyncio.sleep(self.CLEANUP_INTERVAL)

    def cancel(self):
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception as e:
                logger.error("Error stopping TTS: %s", e)
            self.current_process = None

    @measure_performance
    async def speak(self, text: str):
        # Start cleanup task on first use
        if not self._cleanup_task_started:
            self._start_cleanup_task()
            
        # Skip speaking if muted (e.g., in text/chat mode)
        if getattr(self, 'mute', False):
            return
        logger.info("TTS: %s", text)
        if OpenAI is None:
            logger.error("openai library is not available")
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                from config import _config
                api_key = _config.get("API_KEYS", {}).get("OPENAI_API_KEY")
            except Exception:
                api_key = None
        if not api_key:
            logger.error("OpenAI API key not provided")
            return

        client = OpenAI(api_key=api_key)
        self._last_activity = time.time()

        def _stream_and_play() -> None:
            ensure_ffmpeg_installed()
            try:
                with client.audio.speech.with_streaming_response.create(
                    model=self.model,
                    voice=self.voice,
                    input=text,
                    response_format="opus",
                ) as response:
                    self.cancel()
                    self.current_process = subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(self.volume), "-i", "-"] ,
                        stdin=subprocess.PIPE,
                    )
                    for chunk in response.iter_bytes():
                        if self.current_process.stdin:
                            try:
                                self.current_process.stdin.write(chunk)
                                self.current_process.stdin.flush()
                            except BrokenPipeError:
                                break
                    if self.current_process.stdin:
                        self.current_process.stdin.close()
                    self.current_process.wait()
            except Exception as e:
                logger.error("TTS error: %s", e)
            finally:
                self.current_process = None

        await asyncio.to_thread(_stream_and_play)

# Create a global instance of TTSModule
_tts_module_instance = TTSModule()

# Define a module-level async speak function
async def speak(text: str):
    """Module-level function to handle text-to-speech."""
    await _tts_module_instance.speak(text)
