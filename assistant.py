__version__ = "1.2.0" # Updated version

import asyncio, json, logging, os, glob, importlib, time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import ollama
import inspect # Add inspect import back
import queue # Import queue for Empty exception
import threading
import logging.handlers # Add this import
from collections import deque # Import deque for conversation history
# numpy imported lazily when needed

# Import modułów audio z nowej lokalizacji - some imported lazily
from audio_modules.beep_sounds import play_beep
import audio_modules.beep_sounds as beep_sounds
from audio_modules.wakeword_detector import run_wakeword_detection
# TTSModule and WhisperASR imported lazily when needed

# Import funkcji AI z nowego modułu
from ai_module import refine_query, generate_response, parse_response, remove_chain_of_thought, detect_language, detect_language_async
from intent_system import classify_intent, handle_intent
"""Removed database persistence here to avoid duplicate writes; persistence handled by web UI routes."""

# Import performance monitor
from performance_monitor import measure_performance

# Import active window module if tracking is enabled
# from config import Config # REMOVED
from active_window_module import get_active_window_title

# Import specific config variables needed
from config import (
    load_config,
    MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD,
    WHISPER_MODEL, MAX_HISTORY_LENGTH,
    LOW_POWER_MODE, DEV_MODE,
    TRACK_ACTIVE_WINDOW, ACTIVE_WINDOW_POLL_INTERVAL, WAKE_WORD_SENSITIVITY_THRESHOLD,
    AUTO_LISTEN_AFTER_TTS, USE_FUNCTION_CALLING # Ensure USE_FUNCTION_CALLING is imported
)
from config import _config
QUERY_REFINEMENT_ENABLED = False  # prompt refinement disabled for new testing approach


# Set logger to DEBUG globally
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Configuration should be handled in main.py, not here.

PLUGINS_STATE_FILE = os.path.join(os.path.dirname(__file__), 'plugins_state.json')
plugins_state_lock = threading.Lock()

def load_plugins_state():
    try:
        with plugins_state_lock:
            if not os.path.exists(PLUGINS_STATE_FILE):
                return {}
            with open(PLUGINS_STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('plugins', {})
    except Exception as e:
        logger.error(f"Failed to load plugins state: {e}")
        return {}

def save_plugins_state(plugins):
    try:
        with plugins_state_lock:
            with open(PLUGINS_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump({'plugins': plugins}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save plugins state: {e}")


class Assistant:
    async def speak_and_maybe_listen(self, text, listen_after_tts: bool, TextMode: bool = False):
        """Helper: Speak text, and if listen_after_tts, trigger manual listen after TTS."""
        if not text:
            return
        self.conversation_history.append({"role": "assistant", "content": text})
        # Persist assistant response to DB
        try:
            from database_models import add_chat_message
            add_chat_message('assistant', text)
        except Exception:
            logger.warning("Failed to save assistant message to history database.")
            
        # Log the final TTS output with a special marker
        try:
            import datetime, json
            tts_message = {"role": "assistant_tts", "content": text}
            with open("user_data/prompts_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().isoformat()} | {json.dumps(tts_message, ensure_ascii=False)}\n")
        except Exception as log_exc:
            logger.warning(f"[PromptLog] Failed to log TTS output: {log_exc}")
        
        if listen_after_tts:
            logger.info(f"[TTS+Listen] Speaking and will listen again: '{text[:100]}...'")
            self.is_speaking = True
            self.last_tts_text = text
            self._update_shared_state()
            await self.tts.speak(text)
            self.is_speaking = False
            self.last_tts_text = ""
            self._update_shared_state()
            logger.info("[TTS+Listen] TTS finished, triggering manual listen.")
            self.is_processing = False
            self.is_listening = True
            self._update_shared_state()
            self.manual_trigger_event.set()
        else:
            logger.info(f"[TTS] Speaking (no re-listen): '{text[:100]}...'")
            asyncio.create_task(self._speak_async(text))

    async def _speak_async(self, text: str):
        """Background speaking task used when no re-listen is requested."""
        self.is_speaking = True
        self.last_tts_text = text
        self._update_shared_state()
        await self.tts.speak(text)
        self.is_speaking = False
        self.last_tts_text = ""
        self.is_processing = False
        self._update_shared_state()
    """Main class for the assistant."""
    @measure_performance
    def __init__(self, mic_device_id: int = None, wake_word: str = None, stt_silence_threshold: int = None, command_queue: queue.Queue = None): # Type hint for command_queue
        # self.config = Config() # REMOVED
        # Load configuration values using _config or global vars from config.py
        # Assumes load_config() has been called once (e.g., in main.py) to populate _config and globals initially.
        self.mic_device_id = mic_device_id if mic_device_id is not None else _config.get('MIC_DEVICE_ID', MIC_DEVICE_ID)
        self.wake_word = wake_word if wake_word is not None else _config.get('WAKE_WORD', WAKE_WORD)
        self.stt_silence_threshold = stt_silence_threshold if stt_silence_threshold is not None else _config.get('STT_SILENCE_THRESHOLD', STT_SILENCE_THRESHOLD)
        self.whisper_model = _config.get('WHISPER_MODEL', WHISPER_MODEL)
        self.max_history_length = _config.get('MAX_HISTORY_LENGTH', MAX_HISTORY_LENGTH)
        self.low_power_mode = _config.get('LOW_POWER_MODE', LOW_POWER_MODE)
        self.dev_mode = _config.get('DEV_MODE', DEV_MODE)
        self.track_active_window = _config.get('TRACK_ACTIVE_WINDOW', TRACK_ACTIVE_WINDOW)
        # Ensure prompts_log.txt exists and is ready for logging
        import os
        os.makedirs(os.path.dirname("user_data/prompts_log.txt"), exist_ok=True)
        if not os.path.exists("user_data/prompts_log.txt"):
            open("user_data/prompts_log.txt", "w", encoding="utf-8").close()
        # Ensure user input log exists
        os.makedirs(os.path.dirname("user_data/user_inputs_log.txt"), exist_ok=True)
        if not os.path.exists("user_data/user_inputs_log.txt"):
            open("user_data/user_inputs_log.txt", "w", encoding="utf-8").close()
        self.active_window_poll_interval = _config.get('ACTIVE_WINDOW_POLL_INTERVAL', ACTIVE_WINDOW_POLL_INTERVAL)
        self.wake_word_sensitivity_threshold = _config.get('WAKE_WORD_SENSITIVITY_THRESHOLD', WAKE_WORD_SENSITIVITY_THRESHOLD)

        self.use_whisper = True # Vosk is removed, Whisper is the STT
        self.whisper_asr = None # Initialized in self.initialize_components

        self.intent_detector = None # Initialized later
        self.should_exit = threading.Event()
        self.is_listening = False
        self.is_processing = False
        self.is_speaking = False
        self.wake_word_detected = False
        self.last_tts_text = ""
        self.current_active_window = None
        self._active_window_thread = None
        self._stop_event_active_window = threading.Event()

        self.conversation_history = deque(maxlen=self.max_history_length)
        from audio_modules.tts_module import TTSModule  # Lazy import
        self.tts = TTSModule()
        
        # The old SpeechRecognizer instance (Vosk-based) is removed.
        # Audio input for wake word and commands will be handled by wakeword_detector and WhisperASR.

        self.modules = {}
        self.plugin_mod_times = {}
        self.auto_listen_after_tts = _config.get('AUTO_LISTEN_AFTER_TTS', AUTO_LISTEN_AFTER_TTS)

        self._plugin_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
        os.makedirs(self._plugin_folder, exist_ok=True)
        self._observer = Observer()
        
        class _Handler(FileSystemEventHandler):
            def __init__(self, outer_instance):
                self.outer = outer_instance
                self._last_event_time = {}
                self._debounce_interval = 1.0

            def _schedule_reload(self, path, action):
                event_key = (path, action)
                current_time = time.time()
                if event_key in self._last_event_time and (current_time - self._last_event_time[event_key]) < self._debounce_interval:
                    return 
                self._last_event_time[event_key] = current_time
                
                filename = os.path.basename(path)
                logger.info(f"Plugin file {action}: {filename}. Scheduling reload.")
                if self.outer.loop: 
                    self.outer.loop.call_soon_threadsafe(self.outer.load_plugins)
                else: 
                     self.outer.load_plugins()

            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith(".py") and "__pycache__" not in event.src_path:
                    self._schedule_reload(event.src_path, "modified")

            def on_created(self, event):
                if not event.is_directory and event.src_path.endswith(".py") and "__pycache__" not in event.src_path:
                    self._schedule_reload(event.src_path, "created")

            def on_deleted(self, event):
                if not event.is_directory and event.src_path.endswith(".py") and "__pycache__" not in event.src_path:
                    logger.info(f"Plugin file deleted: {os.path.basename(event.src_path)}. Scheduling check.")
                    if self.outer.loop:
                         self.outer.loop.call_soon_threadsafe(self.outer.load_plugins)
                    else:
                         self.outer.load_plugins() 

        handler = _Handler(self)
        self._observer.schedule(handler, self._plugin_folder, recursive=False)
        self._observer.daemon = True
        self._observer.start()

        self.load_plugins()
        self.loop = None 
        self.command_queue = command_queue
        self.manual_trigger_event = threading.Event() # For signaling manual listen to wakeword_detector        # Initialize daily briefing module
        self.daily_briefing = None
        self._init_daily_briefing()

        if self.track_active_window:
            self.start_active_window_tracker()
        
        self.initialize_components() # Initializes WhisperASR and other components
        logger.info("Assistant initialized.")
        # --- End of __init__ ---
    
    def initialize_components(self):
        """Initializes components that require hardware access or network."""
        logger.info("Initializing components...")
        
        # Initialize WhisperASR
        if self.use_whisper: # This will always be true now
            if not self.whisper_asr: 
                logger.info(f"Initializing WhisperASR with model: {self.whisper_model}")
                from audio_modules.whisper_asr import WhisperASR  # Lazy import
                self.whisper_asr = WhisperASR(model_size=self.whisper_model)
            
            logger.info("Warming up Whisper ASR model...")
            try:
                import numpy as np  # Lazy import
                sample_rate = 16000
                duration = 1
                num_samples = sample_rate * duration
                dummy_audio_np = np.zeros(num_samples, dtype=np.float32)
                self.whisper_asr.transcribe(dummy_audio_np, sample_rate=sample_rate) 
                logger.info("Whisper ASR model warmed up with test data.")
            except Exception as e:
                logger.error(f"Error warming up Whisper ASR model: {e}", exc_info=True)
        else: # Should not happen if Vosk is removed
            logger.warning("use_whisper is false, but Vosk is removed. STT will not function.")
            if self.whisper_asr:
                self.whisper_asr.unload()
                self.whisper_asr = None

        # Warm up TTS (existing logic)
        if hasattr(self.tts, 'warm_up'):
            try:
                logger.info("Warming up TTS model...")
                # If tts.warm_up() is an async function:
                # asyncio.run(self.tts.warm_up())
                # If it's synchronous, call directly:
                # self.tts.warm_up() 
                # Assuming it might be async based on previous logs, but needs confirmation.
                # For now, let's assume it can be called, and if it's async, it should be run in an event loop.
                # If called from __init__/initialize_components (sync context), it needs care.
                # If TTS warm-up is simple/fast sync, it's fine. If it's complex async, it might need a temporary loop.
                # Or, it's called from an async context later.
                # For safety, let's assume it's a synchronous call or handled internally by TTSModule.
                if inspect.iscoroutinefunction(self.tts.warm_up):
                    asyncio.run(self.tts.warm_up()) # This is problematic if called from a running loop.
                                                    # Better to ensure TTS warm-up is designed to be called from sync context
                                                    # or called from an async context.
                                                    # Let's call it directly and assume it's designed to be callable here.
                    logger.info("TTS warm-up called (actual execution depends on its implementation).")


                logger.info("TTS model warmed up (or warm-up process initiated).")
            except Exception as e:
                logger.error(f"Error warming up TTS model: {e}", exc_info=True)
        
        # Vosk model warm-up is removed.
        logger.info("Components initialized.")

    def start_active_window_tracker(self):
        if not self.track_active_window:
            return
        if self._active_window_thread and self._active_window_thread.is_alive():
            return # Already running
        
        self._stop_event_active_window.clear()
        self._active_window_thread = threading.Thread(target=self._track_active_window_loop, daemon=True)
        self._active_window_thread.start()
        logger.info("Active window tracker started.")

    def stop_active_window_tracker(self):
        if self._active_window_thread and self._active_window_thread.is_alive():
            self._stop_event_active_window.set()
            self._active_window_thread.join(timeout=self.active_window_poll_interval + 1)
            if self._active_window_thread.is_alive():
                logger.warning("Active window tracker thread did not stop in time.")
            else:
                logger.info("Active window tracker stopped.")
        self._active_window_thread = None

    def _track_active_window_loop(self):
        while not self._stop_event_active_window.is_set():
            try:
                current_title = get_active_window_title()
                if current_title != self.current_active_window:
                    logger.info(f"Active window changed from '{self.current_active_window}' to '{current_title}'")
                    self.current_active_window = current_title
                # Use the specific poll interval from config
                time.sleep(self.active_window_poll_interval)
            except Exception as e:
                logger.error(f"Error in active window tracking loop: {e}")
                # Avoid busy-looping on error, wait before retrying
                time.sleep(self.active_window_poll_interval) 

    def _init_daily_briefing(self):
        """Initialize the daily briefing module."""
        try:
            from daily_briefing_module import DailyBriefingModule
            from config import daily_briefing
            
            # Merge global daily_briefing config with user-specific settings
            briefing_config = _config.copy()
            self.daily_briefing = DailyBriefingModule(briefing_config)
            
            # Start scheduler if enabled
            if self.daily_briefing.scheduled_briefing:
                self.daily_briefing.start_scheduler(assistant_callback=self._deliver_scheduled_briefing)
            
            logger.info("Daily briefing module initialized")
        except Exception as e:
            logger.error(f"Failed to initialize daily briefing module: {e}", exc_info=True)
            self.daily_briefing = None

    async def _deliver_scheduled_briefing(self, briefing_text: str):
        """Callback for delivering scheduled briefings."""
        try:
            logger.info("Delivering scheduled daily briefing")
            await self.speak_and_maybe_listen(briefing_text, listen_after_tts=False, TextMode=False)
            logger.info("Scheduled daily briefing delivered successfully")
        except Exception as e:
            logger.error(f"Error delivering scheduled briefing: {e}", exc_info=True)

    async def check_daily_briefing(self):
        """Check if daily briefing should be delivered and deliver it if needed."""
        if not self.daily_briefing:
            return
        
        try:
            briefing_text = await self.daily_briefing.deliver_briefing()
            if briefing_text:
                logger.info("Delivering daily briefing")
                await self.speak_and_maybe_listen(briefing_text, listen_after_tts=False, TextMode=False)
                logger.info("Daily briefing delivered successfully")
        except Exception as e:
            logger.error(f"Error delivering daily briefing: {e}", exc_info=True)

    def reload_config_values(self):
        """Reloads configuration values from the config module."""
        logger.info("Reloading configuration values in Assistant...")
        load_config() # Crucial: refreshes _config and global config variables

        self.mic_device_id = _config.get('MIC_DEVICE_ID', MIC_DEVICE_ID)
        self.wake_word = _config.get('WAKE_WORD', WAKE_WORD)
        self.stt_silence_threshold = _config.get('STT_SILENCE_THRESHOLD', STT_SILENCE_THRESHOLD)
        
        new_whisper_model = _config.get('WHISPER_MODEL', WHISPER_MODEL)
        if self.whisper_model != new_whisper_model:
            logger.info(f"Whisper model changed from {self.whisper_model} to {new_whisper_model}. Re-initializing WhisperASR.")
            self.whisper_model = new_whisper_model
            if self.whisper_asr:
                # Assuming WhisperASR has an unload method or similar cleanup
                if hasattr(self.whisper_asr, 'unload_model'): # Check if unload_model exists
                    self.whisper_asr.unload_model()
                elif hasattr(self.whisper_asr, 'unload'): # Check for unload
                     self.whisper_asr.unload()
                self.whisper_asr = None # Force re-initialization
            
            if self.use_whisper: # This will be true                 self.whisper_asr = WhisperASR(model_size=self.whisper_model)
                 try:
                    import numpy as np  # Lazy import
                    logger.info(f"Warming up new Whisper ASR model: {self.whisper_model}")
                    sample_rate = 16000; duration = 1; num_samples = sample_rate * duration
                    dummy_audio_np = np.zeros(num_samples, dtype=np.float32)
                    # Ensure correct parameters for transcribe, especially if language needs to be dynamic
                    self.whisper_asr.transcribe(dummy_audio_np, sample_rate=sample_rate, language=_config.get("LANGUAGE", "en")[:2])
                    logger.info("New Whisper ASR model warmed up.")
                 except Exception as e:
                    logger.error(f"Error warming up new Whisper ASR model: {e}", exc_info=True)

        self.max_history_length = _config.get('MAX_HISTORY_LENGTH', MAX_HISTORY_LENGTH)
        # Re-create deque with new max length if it changed.
        if self.conversation_history.maxlen != self.max_history_length:
            self.conversation_history = deque(list(self.conversation_history), maxlen=self.max_history_length)
        
        self.low_power_mode = _config.get('LOW_POWER_MODE', LOW_POWER_MODE)
        self.dev_mode = _config.get('DEV_MODE', DEV_MODE)
        
        new_track_active_window = _config.get('TRACK_ACTIVE_WINDOW', TRACK_ACTIVE_WINDOW)
        if self.track_active_window != new_track_active_window:
            self.track_active_window = new_track_active_window
            if self.track_active_window:
                self.start_active_window_tracker()
            else:
                self.stop_active_window_tracker()
        
        self.active_window_poll_interval = _config.get('ACTIVE_WINDOW_POLL_INTERVAL', ACTIVE_WINDOW_POLL_INTERVAL)
        self.wake_word_sensitivity_threshold = _config.get('WAKE_WORD_SENSITIVITY_THRESHOLD', WAKE_WORD_SENSITIVITY_THRESHOLD)
        self.auto_listen_after_tts = _config.get('AUTO_LISTEN_AFTER_TTS', AUTO_LISTEN_AFTER_TTS)
        
        # Reload daily briefing configuration
        if self.daily_briefing:
            self._init_daily_briefing()
        
        global QUERY_REFINEMENT_ENABLED
        QUERY_REFINEMENT_ENABLED = False  # prompt refinement remains disabled for testing

        logger.info("Configuration values reloaded.")
        # Consider if wakeword_detector needs to be explicitly updated with new sensitivity or wake word.
        # Currently, run_async in Assistant passes these values when starting wakeword_detector.
        # If wakeword_detector runs persistently and needs dynamic updates, a different mechanism would be needed.

    @measure_performance # Add decorator
    def load_plugins(self):
        """Load all plugin modules from the modules folder."""
        # Load plugins differently when frozen (bundled) vs normal filesystem
        import sys, importlib
        plugins_state = load_plugins_state()
        new_modules = {}
        # Bundled: import plugin modules from package via pkgutil
        if getattr(sys, 'frozen', False):
            try:
                import pkgutil, modules as _plugin_pkg
                for _, name, ispkg in pkgutil.iter_modules(_plugin_pkg.__path__):
                    if not name.endswith('_module'):
                        continue
                    # Skip disabled plugins
                    state = plugins_state.get(name, {})
                    if state.get('enabled') is False:
                        continue
                    module_full_name = f"modules.{name}"
                    try:
                        if module_full_name in sys.modules:
                            module = importlib.reload(sys.modules[module_full_name])
                        else:
                            module = importlib.import_module(module_full_name)
                    except Exception as e:
                        logger.error(f"Błąd przy ładowaniu pluginu {name}: {e}", exc_info=True)
                        continue
                    if hasattr(module, 'register'):
                        try:
                            info = module.register()
                        except Exception as e:
                            logger.error(f"Błąd podczas register() pluginu {name}: {e}", exc_info=True)
                            continue
                        if isinstance(info, dict):
                            info['_module_name'] = name
                            cmd = info.get('command')
                            if cmd and isinstance(cmd, str):
                                new_modules[cmd] = info
                            else:
                                logger.warning(f"Plugin {name} missing 'command', skipping.")
                self.modules = new_modules
                logger.info("Plugins loaded: %s", list(self.modules.keys()))
                return
            except Exception:
                logger.error("Error loading bundled plugins.", exc_info=True)
        # Normal (filesystem) plugin loading
        # Determine plugin directory
        plugin_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
        os.makedirs(plugin_folder, exist_ok=True)
        # Clean up removed modules
        current_files = set(os.path.join(plugin_folder, f)
                            for f in os.listdir(plugin_folder)
                            if f.endswith('_module.py') and not f.startswith('__'))
        for old_path in list(self.plugin_mod_times.keys()):
            if old_path not in current_files:
                del self.plugin_mod_times[old_path]
        # Ensure modules package is importable
        if os.path.dirname(plugin_folder) not in sys.path:
            sys.path.insert(0, os.path.dirname(plugin_folder))
        old_modules = self.modules if hasattr(self, 'modules') else {}
        # Iterate plugin files
        for filename in os.listdir(plugin_folder):
            if not filename.endswith('_module.py') or filename.startswith('__'):
                continue
            filepath = os.path.join(plugin_folder, filename)
            mod_name = filename[:-3]
            state = plugins_state.get(mod_name, {})
            if state.get('enabled') is False:
                # disable tracking
                self.modules = {k: v for k, v in self.modules.items() if v.get('_module_name') != mod_name}
                self.plugin_mod_times.pop(filepath, None)
                continue
            # skip unchanged
            try:
                mtime = os.path.getmtime(filepath)
            except OSError:
                continue
            full_name = f"modules.{mod_name}"
            if filepath in self.plugin_mod_times and self.plugin_mod_times[filepath] == mtime and full_name in sys.modules:
                # reuse
                for k, v in self.modules.items():
                    if v.get('_module_name') == mod_name:
                        new_modules[k] = v
                continue
            # import or reload
            try:
                if full_name in sys.modules:
                    module = importlib.reload(sys.modules[full_name])
                else:
                    module = importlib.import_module(full_name)
                self.plugin_mod_times[filepath] = mtime
            except Exception as e:
                logger.error(f"Błąd przy ładowaniu pluginu {mod_name}: {e}", exc_info=True)
                self.plugin_mod_times.pop(filepath, None)
                continue
            # register
            if hasattr(module, 'register'):
                try:
                    info = module.register()
                except Exception as e:
                    logger.error(f"Błąd podczas register() pluginu {mod_name}: {e}", exc_info=True)
                    continue
                if isinstance(info, dict):
                    info['_module_name'] = mod_name
                    cmd = info.get('command')
                    if cmd and isinstance(cmd, str):
                        new_modules[cmd] = info
                    else:
                        logger.warning(f"Plugin {mod_name} missing 'command', skipping.")
        # update and log
        self.modules = new_modules
        added = set(new_modules) - set(old_modules)
        removed = set(old_modules) - set(new_modules)
        for cmd in added:
            logger.info("Plugin enabled: %s", cmd)
        for cmd in removed:
            logger.info("Plugin disabled/removed: %s", cmd)
        logger.info("Plugins loaded: %s", list(self.modules.keys()))


    # Removed async def monitor_plugins - Watchdog handles this now

    @measure_performance # Add decorator
    async def process_query(self, text_input: str, TextMode: bool = False):

        # --- Centralized process_query logic ---
        beep_sounds.MUTE = bool(TextMode)
        self.tts.mute = bool(TextMode)
        self.is_listening = False
        self.is_processing = True
        listen_after_tts = False
        # Use global flag to control prompt refinement (disabled by default for new testing approach)
        query_refinement_enabled = QUERY_REFINEMENT_ENABLED

        # 1. Language detection and query refinement
        lang_code, lang_conf = await detect_language_async(text_input)
        logger.info(f"Detected language: {lang_code} (confidence {lang_conf:.2f})")
        refined_query = refine_query(text_input, detected_language=lang_code) if query_refinement_enabled else text_input
        logger.info(f"Refined query: {refined_query}")

        # 2. Intent detection and logging
        import datetime
        intent, confidence = classify_intent(refined_query)
        logger.info(f"[INTENT] Interpreted intent: {intent} (confidence: {confidence:.2f}) for: '{refined_query}'")        
        try:
            with open("user_data/user_inputs_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().isoformat()} | {refined_query} | intent={intent} | conf={confidence:.2f}\n")
        except Exception as log_exc:
            logger.warning(f"[UserInputLog] Failed to log user input: {log_exc}")
        # Append user message to in-memory history and persist to DB
        self.conversation_history.append({
            "role": "user",
            "content": refined_query,
            "intent": intent,
            "confidence": confidence
        })
        try:
            from database_models import add_chat_message
            add_chat_message('user', refined_query)
        except Exception:
            logger.warning("Failed to save user message to history database.")

        # 3. Tool suggestion for LLM
        functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])
        tool_suggestion = None
        if intent and intent != "none":
            module_key = None
            if intent in self.modules:
                module_key = intent
            else:
                for k, info in self.modules.items():
                    if "aliases" in info and intent in [a.lower() for a in info["aliases"]]:
                        module_key = k
                        break
            if module_key:
                mod = self.modules[module_key]
                tool_suggestion = f"{module_key} - {mod.get('description','')}"        # 4. LLM response with function calling support
        # Check if function calling is enabled (default to True for OpenAI)
        use_function_calling = _config.get('USE_FUNCTION_CALLING', True)
        
        response_json_str = generate_response(
            list(self.conversation_history), # Pass a list copy
            tools_info=functions_info,
            system_prompt_override=None,
            detected_language=lang_code,
            language_confidence=lang_conf,
            active_window_title=self.current_active_window if self.track_active_window else None,
            track_active_window_setting=self.track_active_window,
            tool_suggestion=tool_suggestion,
            modules=self.modules if use_function_calling else None,
            use_function_calling=use_function_calling
        )        
        
        logger.info("AI response (raw JSON string): %s", response_json_str)
        
        # Log the raw API response 
        try:
            import datetime
            import json
            with open("user_data/prompts_log.txt", "a", encoding="utf-8") as f:
                api_response_msg = {"role": "assistant_api", "content": response_json_str}
                f.write(f"{datetime.datetime.now().isoformat()} | {json.dumps(api_response_msg, ensure_ascii=False)}\n")
        except Exception as log_exc:
            logger.warning(f"[API Log] Failed to log API response: {log_exc}")        # Check if function calling was used and functions were executed
        try:
            # Try to parse the response to check for function_calls_executed flag
            parsed_response = json.loads(response_json_str) if isinstance(response_json_str, str) else response_json_str
            if use_function_calling and parsed_response.get("function_calls_executed"):
                # Function calling handled the request completely
                logger.info("Function calling executed. Processing complete.")
                # Extract response text and speak it if available
                response_text = parsed_response.get("text", "")
                
                # Check for system listen command in response
                listen_after_tts = self.auto_listen_after_tts if not TextMode else False
                if "SYSTEM_LISTEN_AFTER_TTS:" in response_text:
                    # Extract listen flag from system response
                    if "SYSTEM_LISTEN_AFTER_TTS:True" in response_text:
                        listen_after_tts = True
                    elif "SYSTEM_LISTEN_AFTER_TTS:False" in response_text:
                        listen_after_tts = False
                    # Remove system command from response text
                    response_text = response_text.replace("SYSTEM_LISTEN_AFTER_TTS:True", "").replace("SYSTEM_LISTEN_AFTER_TTS:False", "").strip()
                
                if response_text:
                    await self.speak_and_maybe_listen(response_text, listen_after_tts, TextMode)
                return
        except (json.JSONDecodeError, TypeError) as e:            logger.debug(f"Response is not JSON or missing function_calls_executed flag: {e}")
            # Continue with traditional parsing only if function calling is disabled
        
        # Skip traditional command parsing if function calling is enabled
        if use_function_calling:
            logger.info("Function calling enabled but no functions were executed. Speaking AI response directly.")
            try:
                parsed_response = json.loads(response_json_str) if isinstance(response_json_str, str) else response_json_str
                response_text = parsed_response.get("text", response_json_str)
            except (json.JSONDecodeError, TypeError):
                response_text = response_json_str
            
            listen_after_tts = self.auto_listen_after_tts if not TextMode else False
            if response_text:
                await self.speak_and_maybe_listen(response_text, listen_after_tts, TextMode)
            return
        
        # Traditional command parsing approach (for backward compatibility when function calling is disabled)
        
        # parse_response handles json.loads and error cases
        structured_output = parse_response(response_json_str) 
        
        ai_command = structured_output.get("command")
        ai_params = structured_output.get("params", "")
        ai_response_text = structured_output.get("text", "") # Text LLM wants to say
        
        raw_listen_flag = structured_output.get("listen_after_tts")
        if isinstance(raw_listen_flag, str):
            listen_after_tts = raw_listen_flag.lower() == "true"
        elif isinstance(raw_listen_flag, bool):
            listen_after_tts = raw_listen_flag
        else:
            # Default if not specified by LLM or invalid type.
            # The original "good block" used False. Let's use self.auto_listen_after_tts for voice mode.
            listen_after_tts = self.auto_listen_after_tts if not TextMode else False
        logger.info(f"AI response parsed. Command: '{ai_command}', Params: '{ai_params}', Text: '{ai_response_text[:50]}...', Listen: {listen_after_tts}")

        # 5. Tool/module execution (single clear path)
        found_module_key = None
        module_info = None
        actual_params_for_handler = ai_params 
        target_command_name = ai_command.lower().strip() if ai_command else None
        
        if target_command_name:
            for m_key, info in self.modules.items():
                if target_command_name == m_key.lower():
                    found_module_key = m_key
                    module_info = info
                    break
                for alias in info.get('aliases', []):
                    if target_command_name == alias.lower():
                        found_module_key = m_key
                        module_info = info
                        break
                if found_module_key:
                    break
        
        if not found_module_key and target_command_name: # Check subcommands if direct/alias not found
            for m_key, info in self.modules.items():
                subs = info.get('sub_commands')
                if not subs: continue
                for sub_name, sub_info in subs.items(): # sub_info is not used in current logic but good for future
                    aliases = [a.lower() for a in sub_info.get('aliases', [])]
                    if target_command_name == sub_name.lower() or target_command_name in aliases:
                        found_module_key = m_key
                        module_info = info
                        actual_params_for_handler = {sub_name: ai_params if ai_params else refined_query}
                        logger.info(f"Subcommand '{sub_name}' for module '{found_module_key}' matched. Params: {actual_params_for_handler}")
                        break
                if found_module_key: break
        
        memory_keywords = ["pamiętasz", "przypomnij", "zapamiętałeś", "zapamiętaj", "czy pamiętasz", "przypomnij mi"]        
        if not found_module_key and (not ai_command or not target_command_name) and any(keyword in refined_query.lower() for keyword in memory_keywords):
            # Check for 'memory_module' then 'memory'
            for mem_key_candidate in ['memory_module', 'memory']: 
                if mem_key_candidate in self.modules:
                    found_module_key = mem_key_candidate
                    module_info = self.modules[mem_key_candidate]
                    actual_params_for_handler = refined_query
                    logger.info(f"Memory recall heuristic. Redirecting to '{found_module_key}' with query: '{actual_params_for_handler}'")
                    break
        
        if not found_module_key: # No module found - use AI response directly
            logger.info("No specific module found by LLM or heuristics. Using AI response directly.")
            # Don't fallback to core module - let AI response be used instead

        # 6. Execute module/tool if found
        if found_module_key and module_info:
            if not TextMode:
                asyncio.create_task(asyncio.to_thread(play_beep, 'action'))
            
            handler = module_info.get('handler')
            if not handler:
                logger.error(f"Module {found_module_key} has no handler function.")
                err_msg = f"Przepraszam, moduł {found_module_key} nie jest poprawnie skonfigurowany."
                await self.speak_and_maybe_listen(err_msg, listen_after_tts, TextMode)
                return

            kwargs = {}
            sig = inspect.signature(handler)
            if 'params' in sig.parameters: kwargs['params'] = actual_params_for_handler
            if 'conversation_history' in sig.parameters: kwargs['conversation_history'] = self.conversation_history
            if 'user_lang' in sig.parameters: kwargs['user_lang'] = lang_code
            if 'assistant' in sig.parameters: kwargs['assistant'] = self
            
            try:
                logger.info(f"Executing module: {found_module_key} with params: {actual_params_for_handler}")
                result = handler(**kwargs)
                if inspect.isawaitable(result):
                    result = await result
                
                module_response_text = None
                module_listen_override = None

                if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], bool):
                    module_response_text = str(result[0]) if result[0] is not None else ""
                    module_listen_override = result[1]
                elif result is not None:
                    module_response_text = str(result)

                # Prefer AI's natural response, only fallback to module response if AI didn't provide text
                text_to_speak = ai_response_text if ai_response_text and ai_response_text.strip() else (module_response_text if module_response_text is not None else "")
                final_listen_after_tts = module_listen_override if module_listen_override is not None else listen_after_tts
                
                if text_to_speak:
                    await self.speak_and_maybe_listen(text_to_speak, final_listen_after_tts, TextMode)
                elif final_listen_after_tts and not TextMode: # No text from module/LLM, but listen requested
                    logger.info(f"[ModuleContext][NoSpeak+Listen] Requested listen without text. Triggering.")
                    self.is_processing = False 
                    self.is_listening = True   
                    self.manual_trigger_event.set()

            except Exception as e:
                logger.error(f"Error executing command {found_module_key}: {e}", exc_info=True)
                err_msg = f"Przepraszam, wystąpił błąd podczas wykonywania komendy {found_module_key}."
                await self.speak_and_maybe_listen(err_msg, listen_after_tts, TextMode) # Fallback to LLM's listen preference on error
            return

        # 7. No module/tool found: just speak AI's general response
        logger.info("No specific module executed. Speaking AI's general response.")
        if ai_response_text:
            await self.speak_and_maybe_listen(ai_response_text, listen_after_tts, TextMode)
        elif listen_after_tts and not TextMode: # No AI text either, but listen requested
             logger.info(f"[NoModuleContext][NoSpeak+Listen] No module, no AI text. Triggering listen.")
             self.is_processing = False
             self.is_listening = True
             self.manual_trigger_event.set()
        return

    def start_interactive_mode(self):
        """Starts the interactive mode of the assistant."""
        # Old SpeechRecognizer initialization is removed.
        if not self.intent_detector: 
            from intent_system import IntentDetector 
            self.intent_detector = IntentDetector() 
        logger.info("Interactive mode started. Waiting for wake word or manual trigger...")
        # Wake word detection is started in run_async.

    async def run_async(self):
        """Main asynchronous loop for the assistant."""
        self.loop = asyncio.get_running_loop()
        logger.info(f"Assistant run_async loop started in thread: {threading.get_ident()}")

        if not self.whisper_asr and self.use_whisper:
             logger.warning("WhisperASR not initialized before starting wake word detection. Attempting to initialize.")
             self.initialize_components() 

        self.wakeword_thread = threading.Thread(
            target=run_wakeword_detection,
            args=(
                self.mic_device_id, 
                self.stt_silence_threshold, 
                self.wake_word,
                self.tts,
                self.process_query_from_audio, 
                self.loop,
                self.wake_word_sensitivity_threshold,
                self.whisper_asr,
                self.manual_trigger_event, # Pass the event for manual trigger
                self.should_exit # Pass the stop event for the detector
            ),
            daemon=True
        )
        self.wakeword_thread.start()
        logger.info("Wake word detection thread started.")

        # Check for daily briefing on startup
        await self.check_daily_briefing()

        try:
            while not self.should_exit.is_set():
                try:
                    command_data = await asyncio.to_thread(self.command_queue.get, timeout=0.1)
                    if command_data:
                        command_type = command_data.get("type")
                        command_payload = command_data.get("payload")
                        logger.debug(f"Command received from queue: {command_type}")

                        if command_type == "add_log":
                            pass 
                        elif command_type == "process_text_input":
                            if isinstance(command_payload, str):
                                await self.process_query(command_payload, TextMode=True)
                            else:
                                logger.warning(f"Invalid payload for process_text_input: {command_payload}")
                        elif command_type == "trigger_listen":
                            logger.info("Manual listen triggered via command queue.")
                            self.manual_trigger_event.set() # Signal wakeword_detector to listen
                        elif command_type == "reload_config":
                            self.reload_config_values()
                        elif command_type == "shutdown":
                            logger.info("Shutdown command received. Exiting...")
                            self.should_exit.set()
                            break 
                except queue.Empty:
                    await asyncio.sleep(0.01) 
                except Exception as e:
                    logger.error(f"Error in assistant main loop: {e}", exc_info=True)
                    await asyncio.sleep(0.1) 
        finally:
            logger.info("Assistant run_async loop stopping.")
            if self._observer:
                self._observer.stop()
                self._observer.join()
            if self._active_window_thread:
                self._stop_event_active_window.set()
                self._active_window_thread.join()
            if self.wakeword_thread and self.wakeword_thread.is_alive():
                # Signal wakeword_thread to stop (it should check self.should_exit)
                # For now, just joining with timeout. Proper shutdown for wakeword_thread is needed.
                self.should_exit.set() # Signal all threads
                self.manual_trigger_event.set() # Potentially unblock it if waiting on audio
                self.wakeword_thread.join(timeout=2)

            if self.whisper_asr:
                self.whisper_asr.unload()
            logger.info("Assistant cleaned up and stopped.")

    async def process_query_from_audio(self, command_text: str):
        """Callback for wakeword_detector. Processes transcribed text."""
        logger.info(f"Command received from wake word detector: {command_text}")
        if command_text and isinstance(command_text, str):
            await self.process_query(command_text.strip())
        else:
            logger.warning("Empty or invalid command received from wake word detector.")
            # Play a failure/timeout beep (optional)
            # play_beep("timeout")

    def trigger_manual_listen(self):
        """Manually triggers the assistant to listen for a command."""
        if self.is_listening or self.is_processing:
            logger.warning("Manual trigger ignored: Already listening or processing.")
            return
        logger.info("Manual listen triggered.")
        self.is_listening = True
        self.manual_trigger_event.set() # Signal the wakeword_detector to listen once

    @measure_performance
    async def shutdown(self):
        logger.info("Shutting down assistant...")
        self.should_exit.set() # Signal all loops and threads to exit

        # Stop daily briefing scheduler
        if self.daily_briefing:
            self.daily_briefing.stop_scheduler()

        # Stop active window tracker
        self.stop_active_window_tracker()

        # Stop plugin monitor
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=2)
            if self._observer.is_alive():
                logger.warning("Plugin monitor observer did not stop in time.")

        # Unload WhisperASR model if it was loaded
        if self.whisper_asr:
            logger.info("Unloading WhisperASR model...")
            try:
                if hasattr(self.whisper_asr, 'unload_model'):
                    self.whisper_asr.unload_model()
                elif hasattr(self.whisper_asr, 'unload'): # General unload method
                    self.whisper_asr.unload()
                logger.info("WhisperASR model unloaded.")
            except Exception as e:
                logger.error(f"Error unloading WhisperASR model: {e}", exc_info=True)
            self.whisper_asr = None
        
        # Add a sentinel to the command queue to unblock the run_async loop if it's waiting on queue.get()
        if self.command_queue:
            try:
                self.command_queue.put_nowait(None) # Signal run_async to exit
            except queue.Full:
                logger.warning("Command queue full during shutdown, run_async might not exit immediately.")

        # Wait for the wakeword thread to finish (it checks self.should_exit)
        if hasattr(self, 'wakeword_thread') and self.wakeword_thread and self.wakeword_thread.is_alive():
            logger.info("Waiting for wakeword detection thread to stop...")
            self.wakeword_thread.join(timeout=5) # Give it some time to stop
            if self.wakeword_thread.is_alive():
                logger.warning("Wakeword detection thread did not stop cleanly.")

        # Cancel all other running asyncio tasks in the current loop
        if self.loop and self.loop.is_running():
            tasks = [t for t in asyncio.all_tasks(self.loop) if t is not asyncio.current_task(self.loop)]
            if tasks:
                logger.info(f"Cancelling {len(tasks)} outstanding asyncio tasks...")
                for task in tasks:
                    task.cancel()
                try:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info("Outstanding asyncio tasks cancelled.")
                except asyncio.CancelledError:
                    logger.info("Asyncio tasks were cancelled as part of shutdown.")
                except Exception as e:
                    logger.error(f"Error cancelling asyncio tasks: {e}", exc_info=True)
        
        logger.info("Assistant shutdown sequence complete.")
        # Ensure the event loop is stopped
        if self.loop and self.loop.is_running():
            self.loop.stop()
            logger.info("Event loop stopped.")

        # Final check: ensure no lingering tasks before closing the loop
        if self.loop and asyncio.all_tasks(self.loop): # Check self.loop exists
            # Convert to list for a cleaner log, as set representation can be verbose
            lingering_tasks = list(asyncio.all_tasks(self.loop))
            if lingering_tasks: # Only log if there are actually lingering tasks
                logger.warning(f"Lingering tasks detected before closing loop: {lingering_tasks}")
            else:
                logger.info("No lingering tasks detected before closing loop.")
        elif self.loop: # If self.loop exists but no tasks found
             logger.info("No lingering tasks detected before closing loop.")


        if self.loop: # Check self.loop exists
            self.loop.close()
            logger.info("Event loop closed.")
        # Clear references to assist with garbage collection
        self.command_queue = None
        self.modules = None
        self.plugin_mod_times = None
        self.conversation_history = None
        self.tts = None
        self.whisper_asr = None
        self.intent_detector = None
        logger.info("Assistant resources cleared.")
        # Optionally, force garbage collection
        import gc
        gc.collect()
        logger.info("Garbage collection triggered.")
        # The check for lingering tasks has been moved to before loop.close()
        logger.info("Assistant shutdown sequence complete.")

    def _update_shared_state(self):
        """Update shared state file for Flask SSE endpoint"""
        try:
            from shared_state import save_assistant_state
            save_assistant_state(
                is_listening=self.is_listening,
                is_speaking=self.is_speaking,
                wake_word_detected=self.wake_word_detected,
                last_tts_text=self.last_tts_text,
                is_processing=self.is_processing
            )
        except Exception as e:
            logger.error(f"Failed to update shared state file: {e}")

    def set_listening_state(self, is_listening):
        """Set listening state and update shared state"""
        self.is_listening = is_listening
        self._update_shared_state()

    def set_speaking_state(self, is_speaking):
        """Set speaking state and update shared state"""
        self.is_speaking = is_speaking
        self._update_shared_state()

    def set_wake_word_detected(self, detected):
        """Set wake word detected state and update shared state"""
        self.wake_word_detected = detected
        self._update_shared_state()

    def set_processing_state(self, is_processing):
        """Set processing state and update shared state"""
        self.is_processing = is_processing
        self._update_shared_state()