__version__ = "1.1.0" # Updated version

import asyncio, json, logging, os, glob, importlib, time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import ollama
import inspect # Add inspect import back
import queue # Import queue for Empty exception
import threading
import logging.handlers # Add this import
from collections import deque # Import deque for conversation history

# Import modułów audio z nowej lokalizacji
from audio_modules.tts_module import TTSModule
from audio_modules.speech_recognition import SpeechRecognizer
from audio_modules.beep_sounds import play_beep
import audio_modules.beep_sounds as beep_sounds
from audio_modules.wakeword_detector import run_wakeword_detection

# Import funkcji AI z nowego modułu
from ai_module import refine_query, generate_response, parse_response, remove_chain_of_thought, detect_language
from intent_system import classify_intent, handle_intent

# Import performance monitor
from performance_monitor import measure_performance

# Import specific config variables needed
from config import (
    load_config, # Import load_config function
    # Default values for direct use if needed
    VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD,
    USE_WHISPER_FOR_COMMAND, WHISPER_MODEL, MAX_HISTORY_LENGTH, # Removed PLUGIN_MONITOR_INTERVAL
    LOW_POWER_MODE, DEV_MODE # Import LOW_POWER_MODE and DEV_MODE directly
)
from config import _config
QUERY_REFINEMENT_ENABLED = _config.get("query_refinement", {}).get("enabled", True)
# Update imports to use the new prompt_builder functions - REMOVING as they are no longer directly used
# from prompt_builder import (
#     build_system_prompt,
#     build_language_info_prompt,
#     build_tools_prompt,
#     build_full_system_prompt
# )

logger = logging.getLogger(__name__)
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
    def __init__(self, vosk_model_path: str = None, mic_device_id: int = None, wake_word: str = None, stt_silence_threshold: int = None, command_queue: queue.Queue = None): # Type hint for command_queue
        # Load initial config
        self.config = load_config()

        # Use provided args or fall back to config values
        self.vosk_model_path = vosk_model_path if vosk_model_path is not None else self.config.get('VOSK_MODEL_PATH', VOSK_MODEL_PATH) # Use default from import if not in JSON
        self.mic_device_id = mic_device_id if mic_device_id is not None else self.config.get('MIC_DEVICE_ID', MIC_DEVICE_ID)
        self.wake_word = (wake_word if wake_word is not None else self.config.get('WAKE_WORD', WAKE_WORD)).lower()
        self.stt_silence_threshold = stt_silence_threshold if stt_silence_threshold is not None else self.config.get('STT_SILENCE_THRESHOLD', STT_SILENCE_THRESHOLD)
        self.use_whisper = self.config.get('USE_WHISPER_FOR_COMMAND', USE_WHISPER_FOR_COMMAND)
        self.whisper_model = self.config.get('WHISPER_MODEL', WHISPER_MODEL)
        self.max_history_length = self.config.get('MAX_HISTORY_LENGTH', MAX_HISTORY_LENGTH)
        # self.plugin_monitor_interval = self.config.get('PLUGIN_MONITOR_INTERVAL', PLUGIN_MONITOR_INTERVAL) # Removed, monitor_plugins is gone

        # Use deque for efficient history management
        self.conversation_history = deque(maxlen=self.max_history_length)
        self.tts = TTSModule()
        # Adaptive sample rate: lower for low power environments
        # from config import LOW_POWER_MODE # Moved import to top
        sample_rate = 8000 if LOW_POWER_MODE else 16000
        self.speech_recognizer = SpeechRecognizer(
            self.vosk_model_path,
            self.mic_device_id,
            self.stt_silence_threshold,
            sample_rate=sample_rate
        )
        self.modules = {}
        self.plugin_mod_times = {}
        self.auto_listen_after_tts = self.config.get('AUTO_LISTEN_AFTER_TTS', False) # Add this line
        # REMOVED: self.current_query_should_re_listen = False
        # Start file watcher for plugin changes with debounce
        self._plugin_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
        os.makedirs(self._plugin_folder, exist_ok=True)
        self._observer = Observer()
        class _Handler(FileSystemEventHandler):
            def __init__(self, outer):
                self.outer = outer
                self._timer = None
            def _schedule_reload(self, path, action):
                # Debounce rapid file events
                if self._timer:
                    self._timer.cancel()
                logger.info(f"Scheduling plugin reload due to {action} on {path}")
                self._timer = threading.Timer(0.5, self.outer.load_plugins)
                self._timer.daemon = True
                self._timer.start()
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith('.py') and os.path.dirname(event.src_path) == self.outer._plugin_folder:
                    self._schedule_reload(event.src_path, 'modification')
            def on_created(self, event):
                if not event.is_directory and event.src_path.endswith('.py') and os.path.dirname(event.src_path) == self.outer._plugin_folder:
                    self._schedule_reload(event.src_path, 'creation')
            def on_deleted(self, event):
                if not event.is_directory and event.src_path.endswith('.py') and os.path.dirname(event.src_path) == self.outer._plugin_folder:
                    self._schedule_reload(event.src_path, 'deletion')
        handler = _Handler(self)
        self._observer.schedule(handler, self._plugin_folder, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        # Initial plugin load
        self.load_plugins()
        self.loop = None
        self.command_queue = command_queue
        # self.manual_listen_triggered = False # Flag for manual activation - Replaced by queue signal logic

        # Long-term memory loading deferred until first query to improve startup speed

        if self.use_whisper:
            from audio_modules.whisper_asr import WhisperASR
            self.whisper_asr = WhisperASR(model_name=self.whisper_model)
        else:
            self.whisper_asr = None # Ensure it's defined even if not used

    def reload_config_values(self):
        """Reloads configuration from file and updates relevant instance variables."""
        logger.info("Reloading configuration...")
        try:
            self.config = load_config()
            # Update relevant attributes, falling back to original defaults if keys are missing
            self.wake_word = self.config.get('WAKE_WORD', WAKE_WORD).lower()
            self.mic_device_id = self.config.get('MIC_DEVICE_ID', MIC_DEVICE_ID) # Note: Changing mic might require restart
            self.stt_silence_threshold = self.config.get('STT_SILENCE_THRESHOLD', STT_SILENCE_THRESHOLD)
            self.use_whisper = self.config.get('USE_WHISPER_FOR_COMMAND', USE_WHISPER_FOR_COMMAND)
            self.whisper_model = self.config.get('WHISPER_MODEL', WHISPER_MODEL)
            self.max_history_length = self.config.get('MAX_HISTORY_LENGTH', MAX_HISTORY_LENGTH)
            # self.plugin_monitor_interval = self.config.get('PLUGIN_MONITOR_INTERVAL', PLUGIN_MONITOR_INTERVAL) # Removed
            self.auto_listen_after_tts = self.config.get('AUTO_LISTEN_AFTER_TTS', False) # Add this line

            # Update deque maxlen if history length changed
            if self.conversation_history.maxlen != self.max_history_length:
                logger.info(f"Updating conversation history max length to {self.max_history_length}")
                new_deque = deque(maxlen=self.max_history_length)
                new_deque.extend(self.conversation_history) # Keep existing history
                self.conversation_history = new_deque

            # Re-initialize components that depend on config if necessary
            # Example: Re-init WhisperASR if model changed (might be complex)
            if self.use_whisper and (not self.whisper_asr or self.whisper_asr.model_name != self.whisper_model):
                 logger.info(f"Whisper model changed to {self.whisper_model}. Re-initializing...")
                 from audio_modules.whisper_asr import WhisperASR
                 self.whisper_asr = WhisperASR(model_name=self.whisper_model)
            elif not self.use_whisper:
                 self.whisper_asr = None

            # Update speech recognizer if mic or threshold changed (might need restart)
            # self.speech_recognizer = SpeechRecognizer(self.vosk_model_path, self.mic_device_id, self.stt_silence_threshold)
            logger.warning("Some configuration changes (like Mic ID) might require a full application restart to take effect.")
            logger.info("Configuration reloaded.")
            return True
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}", exc_info=True)
            return False

    @measure_performance # Add decorator
    def load_plugins(self):
        """Load all plugin modules from the modules folder."""
        # Determine plugin directory
        plugin_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
        os.makedirs(plugin_folder, exist_ok=True)
        plugins_state = load_plugins_state()
        # Clean up stale modification times for removed modules
        current_files = set(os.path.join(plugin_folder, f) for f in os.listdir(plugin_folder)
                            if f.endswith('_module.py') and not f.startswith('__'))
        for old_path in list(self.plugin_mod_times.keys()):
            if old_path not in current_files:
                del self.plugin_mod_times[old_path]
        # Keep track of current modules to diff changes
        old_modules = self.modules if hasattr(self, 'modules') else {}
        new_modules = {}
        # Ensure modules package is importable
        import sys # Moved import here as it's only used here now
        if os.path.dirname(plugin_folder) not in sys.path:
            sys.path.insert(0, os.path.dirname(plugin_folder))
        # Iterate over plugin files
        for filename in os.listdir(plugin_folder):
            if not filename.endswith('_module.py') or filename.startswith('__'): # Skip __init__.py etc.
                continue
            filepath = os.path.join(plugin_folder, filename)
            module_name = filename[:-3]
            # Skip disabled plugins
            state = plugins_state.get(module_name, {})
            if state.get('enabled') is False:
                logger.info(f"Plugin {module_name} jest wyłączony - pomijam ładowanie.")
                # Remove any previous registration for this module
                for cmd, info in list(self.modules.items()):
                    if info.get('_module_name') == module_name:
                        del self.modules[cmd]
                # Clean up modification tracking
                if filepath in self.plugin_mod_times:
                    del self.plugin_mod_times[filepath]
                continue
            # Check modification time to skip unchanged plugins
            mod_time = os.path.getmtime(filepath)
            module_full_name = f"modules.{module_name}"
            if filepath in self.plugin_mod_times and self.plugin_mod_times[filepath] == mod_time and module_full_name in sys.modules:
                logger.debug(f"No changes in plugin {module_name}, reusing existing plugin info.")
                # Reuse existing plugin info without re-importing or re-registering
                for cmd, info in self.modules.items():
                    if info.get('_module_name') == module_name:
                        new_modules[cmd] = info
                continue
            else:
                try:
                    if module_full_name in sys.modules:
                        # Reload the module if it exists
                        module = importlib.reload(sys.modules[module_full_name])
                        logger.debug(f"Reloaded module: {module_full_name}")
                    else:
                        # Import the module for the first time
                        module = importlib.import_module(module_full_name)
                        logger.debug(f"Imported module: {module_full_name}")
                    # Update modification time after successful load/reload
                    self.plugin_mod_times[filepath] = mod_time
                except Exception as e:
                    logger.error("Błąd przy ładowaniu/przeładowaniu pluginu %s: %s", module_name, e, exc_info=True)
                    # Remove any previous registration for this module
                    for cmd, info in list(self.modules.items()):
                        if info.get('_module_name') == module_name:
                            del self.modules[cmd]
                    # Clean up modification tracking
                    if filepath in self.plugin_mod_times:
                        del self.plugin_mod_times[filepath]
                    continue
            # Register plugin if valid
            if hasattr(module, 'register'):
                try:
                    plugin_info = module.register()  # Should return a dict
                    if not isinstance(plugin_info, dict):
                        logger.error(f"Plugin {module_name} register() did not return a dictionary.")
                        continue
                    # Tag plugin with its source module for change tracking
                    plugin_info['_module_name'] = module_name
                except Exception as e:
                    logger.error("Błąd podczas register() pluginu %s: %s", module_name, e, exc_info=True)
                    continue
                command = plugin_info.get('command')
                if command and isinstance(command, str):
                    # Register valid plugin
                    new_modules[command] = plugin_info
                else:
                    logger.warning("Plugin %s missing 'command' key or command is not a string, skipping.", module_name)
            else:
                logger.debug("Plugin file %s has no register(), skipping.", filename)
        # Determine plugin changes
        old_keys = set(old_modules.keys())
        new_keys = set(new_modules.keys())
        added = new_keys - old_keys
        removed = old_keys - new_keys
        # Atomically update modules
        self.modules = new_modules
        # Log changes
        for cmd in added:
            info = new_modules.get(cmd, {})
            logger.info("Plugin enabled: %s -> %s", cmd, info.get('description', ''))
        for cmd in removed:
            logger.info("Plugin disabled/removed: %s", cmd)
        logger.info("Plugins loaded: %s", list(self.modules.keys()))


    # Removed async def monitor_plugins - Watchdog handles this now

    @measure_performance # Add decorator
    async def process_query(self, text_input: str, TextMode: bool = False):
        # Mute beep sounds and TTS when in chat/text mode
        beep_sounds.MUTE = bool(TextMode)
        # Disable TTS in text/chat mode
        self.tts.mute = bool(TextMode)
        local_current_query_should_re_listen: bool # Define local variable

        if TextMode == True:
            query_refinement_enabled = False # Disable refinement in text mode
            local_current_query_should_re_listen = False # Reset for text mode
        else:
            query_refinement_enabled = True
            # Default to False for voice mode; AI response will update this.
            local_current_query_should_re_listen = False
            

        # Query refinement can be toggled in config
        if query_refinement_enabled:
            # detect_language now returns (lang_code, lang_conf)
            lang_code, lang_conf = detect_language(text_input) # Use initial text_input for language detection before refinement
            logger.info(f"Detected language for refinement: {lang_code} (confidence {lang_conf:.2f})")
            # Pass detected language to refine_query if it accepts it, assuming refine_query handles it
            # For now, assuming refine_query might use it or it's passed to a model that needs it.
            # Based on ai_module.py, refine_query takes detected_language as an argument.
            refined_query = refine_query(text_input, detected_language=lang_code) 
            logger.info("Refined query: %s", refined_query)
        else:
            refined_query = text_input
            logger.info("Query refinement disabled, using raw input: %s", refined_query)
            # Detect language on the raw input if refinement is off
            lang_code, lang_conf = detect_language(refined_query)
            logger.info(f"Detected language: {lang_code} (confidence {lang_conf:.2f})")

        # Log intent interpretation after refinement
        intent, confidence = classify_intent(refined_query)
        logger.info(f"[INTENT] Interpreted intent: {intent} (confidence: {confidence:.2f}) for: '{refined_query}'")

        # Language detection is now done above, before or after refinement block.
        # The lang_code and lang_conf from that detection will be used.

        # Intent classification (new layer)
        # intent, confidence = classify_intent(refined_query) # This is duplicated, remove one.
        # logger.info("Intent classified as: %s (%.2f)", intent, confidence) # Duplicated log
        # Add user message BEFORE calling the main model
        # Deque handles maxlen automatically
        self.conversation_history.append({
            "role": "user", 
            "content": refined_query, 
            "intent": intent,
            "confidence": confidence
        })
        # self.trim_conversation_history() # No longer needed, deque handles it

        # Przygotowanie listy dostępnych funkcji (tool descriptions)
        functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])

        # Generowanie odpowiedzi przy użyciu funkcji z ai_module
        # Pass lang_code and lang_conf to generate_response
        response_text = generate_response(
            self.conversation_history,
            tools_info=functions_info,
            system_prompt_override=None, # Let ai_module.generate_response handle default system prompt assembly
            detected_language=lang_code,
            language_confidence=lang_conf
        )
        logger.info("AI response: %s", response_text)

        structured_output = parse_response(response_text)

        # Extract potential command and parameters
        ai_command = structured_output.get("command")
        ai_params = structured_output.get("params", "") # Default to "" if missing
        ai_response_text = structured_output.get("text", "") # Text AI wants to say
        # ADDED: Get the listen_after_tts flag from the AI's response
        raw_listen_flag = structured_output.get("listen_after_tts") # Get raw value, or None if key is missing
        if isinstance(raw_listen_flag, str):
            local_current_query_should_re_listen = raw_listen_flag.lower() == "true" # Assign to local variable
        elif isinstance(raw_listen_flag, bool):
            local_current_query_should_re_listen = raw_listen_flag # Assign to local variable
        else:
            # Default to False if it's None (key missing) or some other unexpected type
            # If TextMode is True, it's already False. If voice mode, this ensures it's False if AI doesn't specify.
            if not TextMode: # Only override if not in TextMode (where it's definitively False)
                 local_current_query_should_re_listen = False

        logger.info(f"AI response parsed. local_current_query_should_re_listen flag is: {local_current_query_should_re_listen} (type: {type(local_current_query_should_re_listen).__name__})")


        # --- Tool Execution Logic ---
        target_command_name = ai_command.lower().strip() if ai_command else None
        found_module_key = None
        module_info = None
        actual_params_for_handler = "" 

        # Find the module by checking command name and aliases
        if target_command_name:
            for module_key, info in self.modules.items():
                # top-level module match (command itself)
                if target_command_name == module_key.lower():
                    found_module_key = module_key
                    module_info = info
                    break
                # otherwise check module aliases (if any)
                for alias in info.get('aliases', []):
                    if target_command_name == alias.lower():
                        found_module_key = module_key
                        module_info = info
                        break
                if found_module_key:
                    break

        # Prepare parameters based on expected type
        if isinstance(ai_params, dict):
            # If AI provides a 'query', extract it
            if 'query' in ai_params and isinstance(ai_params['query'], str):
                actual_params_for_handler = ai_params['query']
            else:
                actual_params_for_handler = ai_params
        elif isinstance(ai_params, str):
            actual_params_for_handler = ai_params
        else:
            actual_params_for_handler = ai_params

        # Fallback: map subcommand names to modules with sub_commands
        if not found_module_key and target_command_name:
            for module_key, info in self.modules.items():
                subs = info.get('sub_commands')
                if not subs:
                    continue
                for sub_name, sub_info in subs.items():
                    aliases = [a.lower() for a in sub_info.get('aliases', [])]
                    if target_command_name == sub_name.lower() or target_command_name in aliases:
                        found_module_key = module_key
                        module_info = info
                        # wrap params for subcommand handler
                        actual_params_for_handler = {sub_name: actual_params_for_handler}
                        break
                if found_module_key:
                    break

        # Additional fallback: detect core subcommands in free text
        if not found_module_key and 'core' in self.modules:
            core_info = self.modules['core']
            subs = core_info.get('sub_commands', {})
            if isinstance(refined_query, str) and refined_query:
                parts = refined_query.split()
                key = parts[0]
                # match primary or alias
                if key in subs or any(key in sc.get('aliases', []) for sc in subs.values()):
                    found_module_key = 'core'
                    module_info = core_info
                    # param is rest of string or empty
                    actual_params_for_handler = {key: ' '.join(parts[1:])}

        # Execute found module commands
        if found_module_key and module_info:
            if module_info.get('sub_commands') and module_info.get('handler') == module_info['handler']: # Core-like plugin
                handler = module_info['handler']
                # Only play sound in voice mode, skip in chat/text mode
                if not TextMode:
                    asyncio.create_task(asyncio.to_thread(play_beep, 'action'))
                try:
                    result = handler(actual_params_for_handler, self.conversation_history)
                    if inspect.isawaitable(result):
                        result = await result
                except Exception as e:
                    logger.error(f"Error executing core handler: {e}", exc_info=True)
                    err_msg = f"Przepraszam, wystąpił błąd podczas wykonywania komendy core."
                    self.conversation_history.append({"role":"assistant","content":err_msg})
                    if local_current_query_should_re_listen: # SIMPLIFIED CONDITION
                        logger.info(f"[Core Error Path] AI requested listen. Speaking and awaiting: '{err_msg}'")
                        await self.tts.speak(err_msg)
                        logger.info("[Core Error Path] TTS for error finished. Triggering manual listen.")
                        self.trigger_manual_listen()
                    else:
                        logger.info(f"[Core Error Path] Speaking error (no re-listen): '{err_msg}'")
                        asyncio.create_task(self.tts.speak(err_msg))
                    return
            else: # Direct module handler
                handler = module_info.get('handler')
                # Prepare call for standard handler signatures
                kwargs = {}
                # If handler expects params
                sig = inspect.signature(handler)
                if 'params' in sig.parameters:
                    kwargs['params'] = actual_params_for_handler
                # Optionally pass conversation_history
                if 'conversation_history' in sig.parameters:
                    kwargs['conversation_history'] = self.conversation_history
                if 'user_lang' in sig.parameters:
                    kwargs['user_lang'] = lang_code
                
                # Only play sound in voice mode
                if not TextMode:
                    asyncio.create_task(asyncio.to_thread(play_beep, 'action'))
                try:
                    result = handler(**kwargs)
                    if inspect.isawaitable(result):
                        result = await result
                except Exception as e:
                    logger.error(f"Error executing command {found_module_key}: {e}", exc_info=True)
                    err_msg = f"Przepraszam, wystąpił błąd podczas wykonywania komendy {found_module_key}."
                    self.conversation_history.append({"role":"assistant","content":err_msg})
                    if local_current_query_should_re_listen: # SIMPLIFIED CONDITION
                        logger.info(f"[Module Error Path] AI requested listen for {found_module_key}. Speaking and awaiting: '{err_msg}'")
                        await self.tts.speak(err_msg)
                        logger.info(f"[Module Error Path] TTS for error finished. Triggering manual listen for {found_module_key}.")
                        self.trigger_manual_listen()
                    else:
                        logger.info(f"[Module Error Path] Speaking error for {found_module_key} (no re-listen): '{err_msg}'")
                        asyncio.create_task(self.tts.speak(err_msg))
                    return
            
            # Handle and speak result from successful command
            result_text = '' if result is None else str(result[0] if isinstance(result, tuple) else result)
            if result_text:
                self.conversation_history.append({"role":"assistant","content":result_text})
                if local_current_query_should_re_listen: # SIMPLIFIED CONDITION
                    logger.info(f"[Command Success Path] Command '{found_module_key}' successful, AI requested listen. Speaking and awaiting: '{result_text[:100]}...'")
                    await self.tts.speak(result_text)
                    logger.info(f"[Command Success Path] TTS for command result finished. Triggering manual listen for '{found_module_key}'.")
                    self.trigger_manual_listen()
                else:
                    logger.info(f"[Command Success Path] Command '{found_module_key}' successful. Speaking (no re-listen): '{result_text[:100]}...'")
                    asyncio.create_task(self.tts.speak(result_text))
            else:
                # Command executed but produced no speakable result.
                # If AI provided initial text (ai_response_text) and wanted to listen, that should be handled.
                # This case might need to fall through to the "No command executed" logic if ai_response_text is to be used.
                # For now, if a command runs and has no text, and AI wanted to listen, what happens?
                # Let's assume if a command runs, its output (or lack thereof) is the primary focus.
                # If ai_response_text was important, it should perhaps be part of the command's logic or a separate step.
                # If listen_after_tts is true but result_text is empty, we might still want to speak ai_response_text if available.
                # This part is tricky. The current structure implies if a command is found, ai_response_text is secondary.
                # Let's ensure if result_text is empty but ai_response_text exists and listen is true, we speak ai_response_text and listen.
                if not result_text and ai_response_text and local_current_query_should_re_listen: # SIMPLIFIED CONDITION
                    logger.info(f"[Command Success Path - No Result] Command '{found_module_key}' had no output, AI requested listen. Speaking initial AI text and awaiting: '{ai_response_text[:100]}...'")
                    self.conversation_history.append({"role": "assistant", "content": ai_response_text}) # Add to history if speaking it
                    await self.tts.speak(ai_response_text)
                    logger.info(f"[Command Success Path - No Result] TTS for initial AI text finished. Triggering manual listen.")
                    self.trigger_manual_listen()
                elif not result_text and ai_response_text: # No result, but initial text, no re-listen
                     logger.info(f"[Command Success Path - No Result] Command '{found_module_key}' had no output. Speaking initial AI text (no re-listen): '{ai_response_text[:100]}...'")
                     self.conversation_history.append({"role": "assistant", "content": ai_response_text})
                     asyncio.create_task(self.tts.speak(ai_response_text))

            return # End of found_module_key and module_info block

        # --- Heurystyka: (This block was complex, ensure TTS logic is consistent) ---
        # This heuristic block is effectively another type of command execution.
        # Let's simplify by assuming if it runs, it will set a text_to_speak and then the final TTS block handles it.
        # For now, I will apply the same pattern directly within its old structure.
        memory_keywords = ["pamiętasz", "przypomnij", "zapamiętałeś", "zapamiętać", "zapomniałeś", "a poza tym", "co jeszcze", "co miałeś zapamiętać"]
        if not found_module_key and any(kw in refined_query.lower() for kw in memory_keywords):
            # Heurystyczne wywołanie narzędzia pamięci - domyślnie pobranie wspomnień
            found_module_key = 'memory'
            module_info = self.modules.get('memory')
            # ustaw puste params, by wywołać domyślną subkomendę 'get'
            ai_params = {}

            if found_module_key and module_info:
                # Choose handler: if AI provided 'action', defer to module's main handler
                handler = None
                description = module_info.get('description', '')
                sub_action = None
                # AI returned structured params with 'action' key: use module handler
                if isinstance(ai_params, dict) and 'action' in ai_params and module_info.get('handler'):
                    handler = module_info['handler']
                    # pass full params dict to handler (it will interpret 'action' internally)
                    actual_params_for_handler = ai_params
                # Handle modules with sub_commands directly when no top-level 'action'
                elif 'sub_commands' in module_info:
                    # Determine sub-command key
                    if isinstance(ai_params, dict) and ai_params:
                        sub_action = next(iter(ai_params.keys()))
                    # Default to 'get' if none provided
                    if not sub_action:
                        sub_action = 'get'
                    sub_info = module_info['sub_commands'].get(sub_action)
                    if sub_info:
                        handler = sub_info['function']
                        description = sub_info.get('description', description)
                        # extract params for this sub-command
                        if isinstance(ai_params, dict):
                            # param under sub_action key or full dict
                            actual_params_for_handler = ai_params.get(sub_action, ai_params)
            else:
                handler = module_info.get('handler')
                description = module_info.get('description', description)
            if handler:
                logger.info(f"Executing command: {found_module_key} (sub: {sub_action}) with params type: {type(actual_params_for_handler)}")
                # Play beep asynchronously in voice mode only
                if not TextMode:
                    asyncio.create_task(asyncio.to_thread(play_beep, "action"))
                # Parameter injection based on handler signature
                sig = inspect.signature(handler)
                sig_params = list(sig.parameters.keys())
                call_params = {}

                # Determine how to pass parameters based on signature
                if 'params' in sig_params:
                    call_params['params'] = actual_params_for_handler
                elif len(sig.parameters) > 0 and list(sig.parameters.keys())[0] not in ['conversation_history', 'user_lang', 'user']:
                    # If the first param is not a special one, assume it takes the main parameter directly
                    first_param_name = list(sig.parameters.keys())[0]
                    # Check if the handler expects a dict and we have one
                    if sig.parameters[first_param_name].annotation == dict and isinstance(actual_params_for_handler, dict):
                         call_params = actual_params_for_handler # Pass the dict directly
                    elif isinstance(actual_params_for_handler, dict) and 'query' in actual_params_for_handler:
                         # If handler expects a string but we have a dict with 'query'
                         call_params[first_param_name] = actual_params_for_handler.get('query', '')
                    elif isinstance(actual_params_for_handler, str):
                         call_params[first_param_name] = actual_params_for_handler
                    else:
                         # Fallback or log warning if types mismatch significantly
                         logger.warning(f"Parameter mismatch for handler {found_module_key}. Expected {sig.parameters[first_param_name].annotation}, got {type(actual_params_for_handler)}. Trying to pass as string.")
                         call_params[first_param_name] = str(actual_params_for_handler)

                # Inject context parameters if handler expects them
                if 'conversation_history' in sig_params:
                    # Pass a copy or allow modification? Currently passing the deque directly.
                    call_params['conversation_history'] = self.conversation_history
                if 'user_lang' in sig_params:
                    call_params['user_lang'] = lang_code
                if 'user' in sig_params:
                    # Assuming 'assistant' context for now, might need refinement
                    call_params['user'] = 'assistant'

                # Speak initial AI response before command asynchronously
                if ai_response_text and not TextMode: # TextMode check still relevant for initial AI text before command
                    logger.info(f"Speaking initial AI response before command: {ai_response_text}")
                    asyncio.create_task(self.tts.speak(ai_response_text)) # Non-blocking

                try:
                    # Execute handler
                    call_result = None
                    if asyncio.iscoroutinefunction(handler):
                        # If handler is async def, await it directly
                        logger.debug(f"Awaiting async handler {found_module_key}...")
                        call_result = await handler(**call_params)
                    else:
                        # If handler is sync def, run it in a thread
                        logger.debug(f"Running sync handler {found_module_key} in thread...")
                        call_result = await asyncio.to_thread(handler, **call_params)

                    # Check if the result itself is awaitable (in case a sync function returned a coroutine)
                    if inspect.isawaitable(call_result):
                        logger.warning(f"Handler {found_module_key} returned an awaitable. Awaiting it now.")
                        result = await call_result
                    else:
                        result = call_result

                    # Unpack tuple results if needed, ensure result_text is a string
                    result_text = None
                    if isinstance(result, tuple) and len(result) >= 1:
                        result_text = str(result[0]) # Ensure it's a string
                    elif isinstance(result, str):
                        result_text = result
                    elif result is not None: # Handle non-string, non-tuple results
                        logger.warning(f"Command '{found_module_key}' returned non-string/non-tuple result: {type(result)}. Converting to string.")
                        result_text = str(result)

                    # Speak and record result (only if result_text is not None or empty)
                    if result_text: # Check if result_text has content
                        logger.info(f"Command '{found_module_key}' executed successfully. Result: '{result_text[:100]}...'") # Log snippet
                        self.conversation_history.append({"role": "assistant", "content": result_text}) # Add string result to history (deque handles maxlen)
                        # self.trim_conversation_history() # No longer needed
                        # Speak result asynchronously without blocking
                        asyncio.create_task(self.tts.speak(result_text)) # TTS task
                        # Check for re-listen after TTS
                        if local_current_query_should_re_listen: # SIMPLIFIED CONDITION
                            await asyncio.sleep(0.1) # Small delay to ensure TTS starts
                            while self.tts.is_speaking(): # Wait for TTS to finish
                                await asyncio.sleep(0.1)
                            self.trigger_manual_listen()
                    else:
                         logger.info(f"Command '{found_module_key}' executed but produced no speakable result.")

                except Exception as e:
                    logger.error(f"Error executing command {found_module_key}: {e}", exc_info=True)
                    error_message = f"Przepraszam, wystąpił błąd podczas wykonywania komendy {found_module_key}."
                    self.conversation_history.append({"role": "assistant", "content": error_message}) # Deque handles maxlen
                    # self.trim_conversation_history() # No longer needed
                    if local_current_query_should_re_listen: # SIMPLIFIED CONDITION
                        logger.info(f"[Command Error Path] AI requested listen. Speaking error and awaiting: '{error_message}'")
                        await self.tts.speak(error_message)
                        logger.info(f"[Command Error Path] TTS for error finished. Triggering manual listen.")
                        self.trigger_manual_listen()
                    else:
                        logger.info(f"[Command Error Path] Speaking error (no re-listen): '{error_message}'")
                        asyncio.create_task(self.tts.speak(error_message))

        else:
            # Command not found or not specified by AI
            if ai_response_text:
                logger.info("No command executed. Speaking AI response text.")
                self.conversation_history.append({"role": "assistant", "content": ai_response_text}) # Deque handles maxlen
                # self.trim_conversation_history() # No longer needed
                if local_current_query_should_re_listen: # SIMPLIFIED CONDITION
                    logger.info(f"[No Command Path] AI requested listen. Speaking and awaiting: '{ai_response_text}'")
                    await self.tts.speak(ai_response_text)
                    logger.info("[No Command Path] TTS finished. Triggering manual listen.")
                    self.trigger_manual_listen()
                else:
                    logger.info(f"[No Command Path] Speaking (no re-listen or TextMode): '{ai_response_text}'") # TextMode note still relevant for logging context
                    asyncio.create_task(self.tts.speak(ai_response_text))
            else:
                # Fallback if AI provides neither text nor command
                logger.warning("AI provided no command and no text response.")
                fallback_response = "Nie rozumiem polecenia lub nie wiem, jak odpowiedzieć."
                self.conversation_history.append({"role": "assistant", "content": fallback_response}) # Deque handles maxlen
                # self.trim_conversation_history() # No longer needed
                if local_current_query_should_re_listen: # SIMPLIFIED CONDITION
                    logger.info(f"[Fallback Path] AI requested listen. Speaking and awaiting: '{fallback_response}'")
                    await self.tts.speak(fallback_response)
                    logger.info("[Fallback Path] TTS finished. Triggering manual listen.")
                    self.trigger_manual_listen()
                else:
                    logger.info(f"[Fallback Path] Speaking (no re-listen): '{fallback_response}'")
                    asyncio.create_task(self.tts.speak(fallback_response))

    # Removed trim_conversation_history method

    def trigger_manual_listen(self):
        # Signal the audio processing thread to re-enter listening mode
        if self.speech_recognizer and self.speech_recognizer.audio_q is not None:
            logger.info("Triggering manual listen...")
            # Put a sentinel value in the queue to wake up the audio processing
            try:
                self.speech_recognizer.audio_q.put_nowait("__MANUAL_TRIGGER__")
            except Exception as e:
                logger.error(f"Error sending relisten signal: {e}")
        else:
            logger.warning("Speech recognizer or its audio_q is not available. Cannot trigger manual listen signal via audio_q.")

    async def process_command_queue(self):
        while True:
            # Retrieve command from multiprocessing queue in executor, retry on interruption
            while True:
                try:
                    command = await self.loop.run_in_executor(None, self.command_queue.get)
                    break
                except InterruptedError:
                    logger.info("Interrupted while getting command, retrying...")
                    continue
            # Check for sentinel value to stop processing
            if command is None:
                logger.info("Stopping command queue processing.")
                return
            logger.info(f"Processing command from queue: {command}")
            # Process the command (this is where the main logic happens)
            try:
                await self.process_query(command)
            except Exception as e:
                logger.error(f"Error processing command '{command}': {e}", exc_info=True)
                # continue processing further commands

    def process_audio(self):
        """
        Main audio loop: handles wake word detection and manual trigger requests.
        Uses the audio queue signal ('__MANUAL_TRIGGER__') for interruption.
        NOTE: This runs in a separate thread via run_in_executor.
        Consider using asyncio.Event for cleaner coordination if refactoring further.
        """
        logger.info("Starting audio processing loop in executor thread...")
        wake_word_task_future = None # To hold the future from run_in_executor

        while True: # This loop runs synchronously within the executor thread
            # --- Check for Manual Trigger Signal in Queue ---
            manual_trigger_received = False
            try:
                # Check the queue non-blockingly for the signal
                signal = self.speech_recognizer.audio_q.get_nowait()
                if signal == "__MANUAL_TRIGGER__":
                    logger.info("Manual trigger signal received from audio queue.")
                    manual_trigger_received = True
                    # Consume any other pending audio data to clear the way
                    while not self.speech_recognizer.audio_q.empty():
                        try: self.speech_recognizer.audio_q.get_nowait()
                        except queue.Empty: break
                else:
                    # Put other data back if it wasn't the signal (shouldn't happen often)
                    logger.warning("Unexpected item found in audio queue during signal check. Item: %s", signal)
                    # self.speech_recognizer.audio_q.put(signal) # Careful about re-queuing
            except queue.Empty:
                pass # No signal, continue normally
            except Exception as e:
                 logger.error(f"Error checking audio queue for signal: {e}", exc_info=True)


            # --- Handle Manual Trigger ---
            if manual_trigger_received:
                logger.info("Processing manual trigger...")
                # Cancel any ongoing wake word detection if it's running
                # This cancellation mechanism depends on how run_wakeword_detection handles it.
                # If it checks a flag or uses asyncio cancellation, it needs to be triggered.
                # For now, we rely on the fact that it consumes the queue and might see the signal.
                # A more robust method would use asyncio.Event or task cancellation.

                play_beep("keyword", loop=False) # Blocking call within the thread is okay here
                command_text = None
                try:
                    if self.use_whisper and self.whisper_asr:
                        logger.info("Recording audio for Whisper command (manual trigger)...")
                        audio_command = self.speech_recognizer.record_dynamic_command_audio() # Blocking call
                        if audio_command is not None:
                            logger.info("Transcribing Whisper command (manual trigger)...")
                            command_text = self.whisper_asr.transcribe(audio_command, self.speech_recognizer.sample_rate) # Blocking call
                        else:
                            logger.warning("Failed to record audio for Whisper command (manual trigger).")
                    else:
                        logger.info("Listening for command with Vosk (manual trigger)...")
                        command_text = self.speech_recognizer.listen_command() # Blocking call

                    if command_text:
                        logger.info("Command (manual trigger): %s", command_text)
                        # Schedule process_query to run in the main event loop
                        asyncio.run_coroutine_threadsafe(self.process_query(command_text, False), self.loop)
                    else:
                        logger.info("No command detected after manual trigger.")
                except Exception as e:
                    logger.error(f"Error during manually triggered listen/process: {e}", exc_info=True)

                logger.info("Manual listening block finished.")
                # Reset state and continue the loop to potentially restart wake word detection
                wake_word_task_future = None # Ensure wake word restarts if it was running


            # --- Manage Wake Word Task ---
            # Check if wake word detection should be running
            if wake_word_task_future is None or wake_word_task_future.done():
                if wake_word_task_future and wake_word_task_future.done():
                    try:
                        # Check result/exception of the completed task
                        result = wake_word_task_future.result()
                        logger.info(f"Wake word task finished with result: {result}")
                        # If wake word was detected, run_wakeword_detection should have called process_query already.
                        # If it was interrupted by manual trigger signal, it might return a specific value.
                        if result == "MANUAL_TRIGGER_REQUESTED":
                             logger.info("Wake word task confirmed interruption by signal.")
                             # Manual trigger logic above already handled it.
                        elif result == "WAKE_WORD_DETECTED":
                             logger.info("Wake word detected and command processed by run_wakeword_detection.")
                        elif result == "NO_COMMAND":
                             logger.info("Wake word detected but no command followed.") 
                        elif result == "ERROR":
                            logger.error("Wake word detection task reported an error.")


                    except asyncio.CancelledError:
                        logger.info("Wake word detection task was cancelled.")
                    except Exception as e:
                        logger.error(f"Wake word detection task failed: {e}", exc_info=True)
                        # time.sleep(2) # Blocking sleep in thread before retrying

                # Start/Restart the wake word detection task in the main event loop's executor
                logger.info("Starting/Restarting wake word detection task...")
                # We pass the synchronous process_audio method's context (self)
                # and the necessary components to run_wakeword_detection.
                # run_wakeword_detection itself needs to handle calling process_query via run_coroutine_threadsafe.
                wake_word_task_future = asyncio.run_coroutine_threadsafe(
                    run_wakeword_detection( # This should be an async function now
                        self.speech_recognizer,
                        self.wake_word,
                        self.tts,
                        self.use_whisper,
                        self.process_query, # Pass the async coroutine
                        self.loop, # Pass the loop for scheduling back
                        self.whisper_asr
                    ), self.loop
                )
                logger.info("Wake word detection task submitted to event loop.")


            # --- Wait / Yield ---
            # Short sleep within the synchronous thread loop to prevent high CPU usage
            # while waiting for queue signals or task completion.
            time.sleep(0.1) # Use time.sleep here as we are in a sync thread

    async def run_async(self):
        logger.info("Bot is starting...")
        if not self.loop:
             self.loop = asyncio.get_running_loop()
        # Removed plugin monitor task - Watchdog handles it
        # asyncio.create_task(self.monitor_plugins())
        # Start the command queue processing task
        asyncio.create_task(self.process_command_queue())

        # Clear queue before starting
        while not self.speech_recognizer.audio_q.empty():
            try: self.speech_recognizer.audio_q.get_nowait()
            except queue.Empty: break
        logger.info("Audio queue cleared.")

        import sounddevice as sd # Keep import local to where it's needed
        audio_thread_future = None # Define audio_thread_future to ensure it's available in finally
        try:
            # Use a context manager for the audio stream
            with sd.RawInputStream(
                    samplerate=self.speech_recognizer.sample_rate,
                    blocksize=8000, # Consider adjusting blocksize based on performance/latency needs
                    dtype="int16",
                    channels=1,
                    device=self.speech_recognizer.mic_device_id,
                    callback=self.speech_recognizer.audio_callback # Feeds the queue
            ):
                logger.info(f"Audio stream opened on device {self.speech_recognizer.mic_device_id}. Starting audio processing thread...")
                # Run the synchronous process_audio loop in a separate thread
                audio_thread_future = self.loop.run_in_executor(None, self.process_audio)

                logger.info("Assistant run_async setup complete. Waiting for tasks...")
                # Keep the main async loop running
                await asyncio.Future() # Keep running indefinitely until stopped externally

        except sd.PortAudioError as pae:
             logger.error(f"PortAudio error opening stream: {pae}")
             logger.error("Please check your microphone device ID and ensure it's available.")
             # Consider specific error handling or shutdown
        except Exception as e:
            logger.error("Fatal error in assistant run_async: %s", e, exc_info=True)
            # Optionally try to clean up
            if audio_thread_future and not audio_thread_future.done():
                 audio_thread_future.cancel() # Attempt to cancel the audio thread
        finally:
            logger.info("Assistant run_async loop finished or encountered an error.")
            # Ensure observer is stopped if loop exits
            if self._observer.is_alive():
                 self._observer.stop()
                 self._observer.join()
                 logger.info("Watchdog observer stopped.")

            # Unload models only if not in DEV_MODE
            if not DEV_MODE:
                logger.info("DEV_MODE is False, unloading models...")
                if self.speech_recognizer:
                    self.speech_recognizer.unload()
                if self.whisper_asr:
                    self.whisper_asr.unload()
            else:
                logger.info("DEV_MODE is True, skipping model unloading.")

            # Stop TTS regardless of DEV_MODE
            if self.tts:
                self.tts.stop()
                logger.info("TTS stopped.")

            logger.info("Assistant cleanup complete.")

    def stop(self):
        logger.info("Stopping Assistant...")
        if self._observer and self._observer.is_alive(): # Check if observer is alive before stopping
            self._observer.stop()
            self._observer.join()
            logger.info("Watchdog observer stopped.")
        else:
            logger.info("Watchdog observer was not running or already stopped.")

        if self.speech_recognizer:
            self.speech_recognizer.stop() # Ensure recognizer resources are cleaned up
            logger.info("Speech recognizer stopped.")


        # Signal the main loop to stop if it's running
        if self.loop and self.loop.is_running():
            logger.info("Requesting main event loop to stop...")
            self.loop.call_soon_threadsafe(self.loop.stop)
        else:
            logger.info("Main event loop was not running or already stopped.")
        
        # Stop TTS, ensure it's done after other cleanup that might use it.
        if self.tts:
            self.tts.stop() # Ensure TTS is stopped
            logger.info("TTS stopped.")

        logger.info("Assistant stop sequence complete.")

# Example usage (typically called from main.py)
