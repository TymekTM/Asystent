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
from audio_modules.wakeword_detector import run_wakeword_detection

# Import funkcji AI z nowego modułu
from ai_module import refine_query, generate_response, parse_response, remove_chain_of_thought, detect_language

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
from prompts import CONVERT_QUERY_PROMPT, SYSTEM_PROMPT


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

class IntentClassifier:
    """Simple intent classifier using LLM or rules."""
    def __init__(self, provider=None):
        self.provider = provider

    def classify(self, text: str) -> str:
        # For demo: use simple rules, or call LLM for intent
        text_l = text.lower()
        if any(x in text_l for x in ["pogoda", "jaka temperatura", "czy będzie padać"]):
            return "weather_query"
        if any(x in text_l for x in ["kim jesteś", "opowiedz o sobie", "co potrafisz"]):
            return "about_assistant"
        if any(x in text_l for x in ["zrób zdjęcie", "screenshot"]):
            return "screenshot"
        if any(x in text_l for x in ["wyszukaj", "znajdź", "search"]):
            return "search"
        # Fallback: ask LLM (optional, not implemented here)
        return "general"

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
        # Load plugins and start file watcher for changes
        self.load_plugins()
        self._plugin_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))
        os.makedirs(self._plugin_folder, exist_ok=True)
        self._observer = Observer()
        class _Handler(FileSystemEventHandler):
            def __init__(self, outer):
                self.outer = outer
            def on_modified(self, event):
                # Reload only if a python file in the modules folder is modified
                if event.src_path.endswith('.py') and os.path.dirname(event.src_path) == self.outer._plugin_folder:
                     logger.info(f"Detected change in {event.src_path}, reloading plugins.")
                     # Consider adding debounce logic here if rapid changes cause issues
                     self.outer.load_plugins() # Reload plugins on modification
        handler = _Handler(self)
        self._observer.schedule(handler, self._plugin_folder, recursive=False) # Watch only the modules folder
        self._observer.daemon = True
        self._observer.start()
        self.loop = None
        self.command_queue = command_queue
        # self.manual_listen_triggered = False # Flag for manual activation - Replaced by queue signal logic

        # --- Load all memories for assistant user at startup ---
        # --- Load all memories for assistant user at startup ---
        try:
            from modules.memory_module import retrieve_memories
            # Use correct parameter name 'query' instead of 'params'
            result, success = retrieve_memories(query="", user="assistant")
            if success and result.strip():
                logger.info(f"Loaded assistant long-term memory at startup:\n{result}")
            else:
                logger.info("No long-term memory found for assistant at startup.")
        except Exception as e:
            logger.error(f"Failed to load assistant long-term memory at startup: {e}")

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
            # Update mod time only if loading succeeds
            # self.plugin_mod_times[filepath] = mod_time # Moved update after successful load
            module_name = filename[:-3]
            # Skip disabled plugins
            state = plugins_state.get(module_name, {})
            if state.get('enabled') is False:
                logger.info(f"Plugin {module_name} jest wyłączony - pomijam ładowanie.")
                if module_name in self.modules: # Remove if previously loaded
                    del self.modules[module_name]
                continue
            module_full_name = f"modules.{module_name}"
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
                self.plugin_mod_times[filepath] = os.path.getmtime(filepath)
            except Exception as e:
                logger.error("Błąd przy ładowaniu/przeładowaniu pluginu %s: %s", module_name, e, exc_info=True)
                # Optionally remove the module from tracking if load fails
                if module_name in self.modules:
                    del self.modules[module_name]
                if filepath in self.plugin_mod_times:
                    del self.plugin_mod_times[filepath]
                continue
            # Register plugin if valid
            if hasattr(module, 'register'):
                try:
                    plugin_info = module.register() # Should return a dict
                    if not isinstance(plugin_info, dict):
                         logger.error(f"Plugin {module_name} register() did not return a dictionary.")
                         continue
                except Exception as e:
                    logger.error("Błąd podczas register() pluginu %s: %s", module_name, e, exc_info=True)
                    continue
                command = plugin_info.get('command')
                if command and isinstance(command, str):
                    # TODO: Validate plugin_info structure further (e.g., handler exists)
                    new_modules[command] = plugin_info
                    logger.info("Loaded plugin: %s -> %s", command, plugin_info.get('description', 'No description'))
                else:
                    logger.warning("Plugin %s missing 'command' key or command is not a string, skipping.", module_name)
            else:
                logger.debug("Plugin file %s has no register(), skipping.", filename)
        # Update the modules dictionary atomically
        self.modules = new_modules
        logger.info(f"Plugins loaded: {list(self.modules.keys())}")


    # Removed async def monitor_plugins - Watchdog handles this now

    @measure_performance # Add decorator
    async def process_query(self, text_input: str, TextMode: bool = False):
        if TextMode == True:
            QUERY_REFINEMENT_ENABLED = False # Disable refinement in text mode
        else:
            QUERY_REFINEMENT_ENABLED = True
            
        # Query refinement can be toggled in config
        if QUERY_REFINEMENT_ENABLED:
            refined_query = refine_query(text_input)
            logger.info("Refined query: %s", refined_query)
        else:
            refined_query = text_input
            logger.info("Query refinement disabled, using raw input: %s", refined_query)

        # --- Language Detection Layer (langid) ---
        lang_code, lang_conf, lang_prompt = detect_language(refined_query)
        logger.info(f"Detected language: {lang_code} (confidence {lang_conf:.2f})")

        # Intent classification (new layer)
        intent = IntentClassifier().classify(refined_query)
        logger.info("Intent classified as: %s", intent)
        # Add user message BEFORE calling the main model
        # Deque handles maxlen automatically
        self.conversation_history.append({"role": "user", "content": refined_query, "intent": intent})
        # self.trim_conversation_history() # No longer needed, deque handles it

        # Przygotowanie listy dostępnych funkcji (tool descriptions)
        functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])

        # --- Inject language context into system prompt ---
        # Combine original prompt, langid's suggestion, and explicit lang info
        system_prompt = f"{SYSTEM_PROMPT}\\n{lang_prompt}" # Keep langid's prompt for now

        # Generowanie odpowiedzi przy użyciu funkcji z ai_module
        # Pass lang_code and lang_conf to generate_response
        response_text = generate_response(
            self.conversation_history,
            functions_info,
            system_prompt_override=system_prompt,
            detected_language=lang_code,
            language_confidence=lang_conf
        )
        logger.info("AI response: %s", response_text)

        structured_output = parse_response(response_text)

        # Extract potential command and parameters
        ai_command = structured_output.get("command")
        ai_params = structured_output.get("params", "") # Default to "" if missing
        ai_response_text = structured_output.get("text", "") # Text AI wants to say

        # --- Tool Execution Logic ---
        target_command_name = ai_command.lower().strip() if ai_command else None
        found_module_key = None
        module_info = None
        actual_params_for_handler = "" # Default to empty string for handlers expecting string

        # --- Parameter Sanitization Placeholder ---
        # TODO: Implement robust sanitization for ai_params based on expected types
        # This is crucial to prevent injection attacks if params are used in shell commands, file paths etc.
        # Example (very basic): if isinstance(ai_params, str): ai_params = re.sub(r'[^\w\s\-]', '', ai_params)
        logger.debug(f"Raw AI params: {ai_params}") # Log raw params before potential sanitization

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
            # For modules with sub_commands (e.g., core, memory), use their handler to dispatch
            if module_info.get('sub_commands') and module_info.get('handler') == module_info['handler']:
                # Core-like plugin: dispatch via its main handler, passing conversation history
                handler = module_info['handler']
                asyncio.create_task(asyncio.to_thread(play_beep, 'action'))
                try:
                    # Pass conversation_history for subcommands that require context
                    result = handler(actual_params_for_handler, self.conversation_history)
                    if inspect.isawaitable(result):
                        result = await result
                except Exception as e:
                    logger.error(f"Error executing core handler: {e}", exc_info=True)
                    err = f"Przepraszam, wystąpił błąd podczas wykonywania komendy core."
                    self.conversation_history.append({"role":"assistant","content":err})
                    asyncio.create_task(self.tts.speak(err))
                    return
            else:
                # Direct module handler (no sub_commands)
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
                # Play action beep
                asyncio.create_task(asyncio.to_thread(play_beep, 'action'))
                try:
                    result = handler(**kwargs)
                    if inspect.isawaitable(result):
                        result = await result
                except Exception as e:
                    logger.error(f"Error executing command {found_module_key}: {e}", exc_info=True)
                    err = f"Przepraszam, wystąpił błąd podczas wykonywania komendy {found_module_key}."
                    self.conversation_history.append({"role":"assistant","content":err})
                    asyncio.create_task(self.tts.speak(err))
                    return
            # Handle and speak result
            result_text = '' if result is None else str(result[0] if isinstance(result, tuple) else result)
            if result_text:
                self.conversation_history.append({"role":"assistant","content":result_text})
                asyncio.create_task(self.tts.speak(result_text))
            return

        # --- Heurystyka: jeśli AI nie wywołało narzędzia, a pytanie użytkownika zawiera słowa kluczowe pamięci ---
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
                # Play beep asynchronously
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
                if ai_response_text and not TextMode:
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
                        asyncio.create_task(self.tts.speak(result_text))
                    else:
                         logger.info(f"Command '{found_module_key}' executed but produced no speakable result.")

                except Exception as e:
                    logger.error(f"Error executing command {found_module_key}: {e}", exc_info=True)
                    error_message = f"Przepraszam, wystąpił błąd podczas wykonywania komendy {found_module_key}."
                    self.conversation_history.append({"role": "assistant", "content": error_message}) # Deque handles maxlen
                    # self.trim_conversation_history() # No longer needed
                    asyncio.create_task(self.tts.speak(error_message)) # Non-blocking

        else:
            # Command not found or not specified by AI
            if ai_response_text:
                logger.info("No command executed. Speaking AI response text.")
                self.conversation_history.append({"role": "assistant", "content": ai_response_text}) # Deque handles maxlen
                # self.trim_conversation_history() # No longer needed
                asyncio.create_task(self.tts.speak(ai_response_text)) # Non-blocking
            else:
                # Fallback if AI provides neither text nor command
                logger.warning("AI provided no command and no text response.")
                fallback_response = "Nie rozumiem polecenia lub nie wiem, jak odpowiedzieć."
                self.conversation_history.append({"role": "assistant", "content": fallback_response}) # Deque handles maxlen
                # self.trim_conversation_history() # No longer needed
                asyncio.create_task(self.tts.speak(fallback_response)) # Non-blocking

        # History trimming is handled by deque automatically

    # Removed trim_conversation_history method

    def trigger_manual_listen(self):
        """Puts a special marker onto the audio queue to trigger manual listening."""
        logger.info("Manual listen trigger requested. Sending signal to audio queue.")
        try:
            # Put a special marker onto the audio queue to interrupt the detector
            # Use put_nowait to avoid blocking if the queue is somehow full
            self.speech_recognizer.audio_q.put_nowait("__MANUAL_TRIGGER__")
            logger.info("Signal sent to audio queue.")
        except queue.Full:
             logger.error("Audio queue is full, cannot send manual trigger signal.")
        except Exception as e:
            logger.error(f"Failed to put manual trigger signal onto audio queue: {e}")

    async def process_command_queue(self):
        """Processes commands from the web UI or other sources."""
        logger.info("Starting command queue processing task...")
        while True:
            try:
                # Use get_nowait() and handle Empty exception to avoid blocking the loop
                command_data = self.command_queue.get_nowait()
                action = command_data.get("action")
                logger.info(f"Received command from queue: {action}")

                if action == "activate":
                    # Trigger manual listen via the audio queue signal mechanism
                    self.trigger_manual_listen()
                elif action == "config_updated":
                    logger.warning("Configuration updated via web UI. Reloading config...")
                    if self.reload_config_values():
                         logger.info("Config reloaded successfully.")
                         # Optionally notify user or perform other actions
                    else:
                         logger.error("Failed to reload config after update signal.")
                    # Restart is handled by main.py based on web UI interaction now
                    # if self.loop:
                    #     self.loop.stop() # Stopping the loop here might be too abrupt
                    # break
                elif action == "reload_plugins":
                     logger.info("Plugin reload requested via queue.")
                     self.load_plugins()
                # Add other command actions here if needed
                else:
                     logger.warning(f"Unknown action received in command queue: {action}")

            except queue.Empty:
                # Queue is empty, wait asynchronously before checking again
                await asyncio.sleep(0.5) # Wait for 0.5 seconds
            except Exception as e:
                logger.error(f"Error in assistant command queue processing: {e}", exc_info=True)
                await asyncio.sleep(1) # Wait a bit longer after an error

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
                    logger.warning("Unexpected item found in audio queue during signal check.")
                    # self.speech_recognizer.audio_q.put(signal) # Careful about re-queuing
            except queue.Empty:
                pass # No signal, continue normally
            except Exception as e:
                 logger.error(f"Error checking audio queue for signal: {e}")


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

    # Remove the old listen_and_process method if it exists, run_async is the main entry point now.
