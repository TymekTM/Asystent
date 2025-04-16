import asyncio, json, logging, os, glob, importlib.util, re, subprocess, multiprocessing, time
import ollama
import inspect # Add inspect import
import queue # Import queue for Empty exception
import threading
import logging.handlers  # Add this import

# Import modułów audio z nowej lokalizacji
from audio_modules.tts_module import TTSModule
from audio_modules.speech_recognition import SpeechRecognizer
from audio_modules.beep_sounds import play_beep
from audio_modules.wakeword_detector import run_wakeword_detection

# Import funkcji AI z nowego modułu
from ai_module import refine_query, generate_response, parse_response, remove_chain_of_thought, detect_language

# Import specific config variables needed
from config import (
    load_config, # Import load_config function
    VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD,
    USE_WHISPER_FOR_COMMAND, WHISPER_MODEL, MAX_HISTORY_LENGTH, PLUGIN_MONITOR_INTERVAL
)
from config import _config
QUERY_REFINEMENT_ENABLED = _config.get("query_refinement", {}).get("enabled", True)
from prompts import CONVERT_QUERY_PROMPT, SYSTEM_PROMPT


logger = logging.getLogger(__name__)
# Usuwamy konfigurację handlerów, polegamy na main.py

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
    def __init__(self, vosk_model_path: str = None, mic_device_id: int = None, wake_word: str = None, stt_silence_threshold: int = None, command_queue: multiprocessing.Queue = None):
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
        self.plugin_monitor_interval = self.config.get('PLUGIN_MONITOR_INTERVAL', PLUGIN_MONITOR_INTERVAL)

        self.conversation_history = []
        self.tts = TTSModule()
        self.speech_recognizer = SpeechRecognizer(self.vosk_model_path, self.mic_device_id, self.stt_silence_threshold)
        self.modules = {}
        self.plugin_mod_times = {}
        self.load_plugins()
        self.loop = None
        self.command_queue = command_queue
        self.manual_listen_triggered = False # Flag for manual activation

        # --- Load all memories for assistant user at startup ---
        try:
            from modules.memory_module import retrieve_memories
            result, success = retrieve_memories(params="", user="assistant")
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
            self.plugin_monitor_interval = self.config.get('PLUGIN_MONITOR_INTERVAL', PLUGIN_MONITOR_INTERVAL)

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

    def load_plugins(self):
        plugin_folder = "modules"
        os.makedirs(plugin_folder, exist_ok=True)
        plugins_state = load_plugins_state()
        new_modules = {}
        for filepath in glob.glob(os.path.join(plugin_folder, "*_module.py")):
            mod_time = os.path.getmtime(filepath)
            self.plugin_mod_times[filepath] = mod_time
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            # Sprawdź, czy plugin jest włączony
            if plugins_state and module_name in plugins_state and not plugins_state[module_name].get('enabled', True):
                logger.info(f"Plugin {module_name} jest wyłączony - pomijam ładowanie.")
                continue
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                logger.error("Błąd przy ładowaniu pluginu %s: %s", module_name, e)
                continue
            if hasattr(module, "register"):
                plugin_info = module.register()
                command = plugin_info.get("command")
                if command:
                    new_modules[command] = plugin_info
                    logger.info("Loaded plugin: %s -> %s", command, plugin_info.get("description"))
                else:
                    logger.warning("Plugin %s missing 'command' key, skipping.", module_name)
            else:
                logger.debug("File %s does not have register() function, skipping.", filepath)
        self.modules = new_modules

    async def monitor_plugins(self, interval: int = None): # Allow override, default to config
        if interval is None:
            interval = self.plugin_monitor_interval
        plugin_folder = "modules"
        while True:
            updated = False
            for filepath in glob.glob(os.path.join(plugin_folder, "*.py")):
                try:
                    mod_time = os.path.getmtime(filepath)
                except Exception:
                    continue
                if filepath not in self.plugin_mod_times or self.plugin_mod_times[filepath] != mod_time:
                    updated = True
                    self.plugin_mod_times[filepath] = mod_time
            if updated:
                logger.info("Detected changes in plugins. Reloading plugins...")
                self.load_plugins()
            await asyncio.sleep(interval)

    async def process_query(self, text_input: str):
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
        self.conversation_history.append({"role": "user", "content": refined_query, "intent": intent})
        self.trim_conversation_history() # Trim history *before* sending to model

        # Przygotowanie listy dostępnych funkcji (tool descriptions)
        functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])

        # --- Inject language context into system prompt ---
        system_prompt = lang_prompt + "\n" + SYSTEM_PROMPT

        # Generowanie odpowiedzi przy użyciu funkcji z ai_module
        response_text = generate_response(self.conversation_history, functions_info, system_prompt_override=system_prompt)
        logger.info("AI response: %s", response_text)

        structured_output = parse_response(response_text)

        # Extract potential command and parameters
        ai_command = structured_output.get("command")
        ai_params = structured_output.get("params", "")
        ai_response_text = structured_output.get("text", "") # Text AI wants to say *before* or *instead* of tool use

        # --- Tool Execution Logic ---
        main_command = None
        sub_command_key = None
        actual_params = ai_params

        if ai_command and ' ' in ai_command:
            parts = ai_command.split(' ', 1)
            main_command = parts[0]
            sub_command_key = parts[1]
        elif ai_command:
            main_command = ai_command

        # --- Heurystyka: jeśli AI nie wywołało narzędzia, a pytanie użytkownika zawiera słowa kluczowe pamięci ---
        memory_keywords = ["pamiętasz", "przypomnij", "zapamiętałeś", "zapamiętać", "zapomniałeś", "a poza tym", "co jeszcze", "co miałeś zapamiętać"]
        if not main_command and any(kw in refined_query.lower() for kw in memory_keywords):
            main_command = "memory"
            sub_command_key = "get"
            actual_params = ""
            logger.info("Heurystyka: automatyczne wywołanie memory get na podstawie pytania użytkownika.")

        if main_command and main_command in self.modules:
            plugin_info = self.modules[main_command]
            handler = None
            is_sub_command = False

            if sub_command_key and "sub_commands" in plugin_info and sub_command_key in plugin_info["sub_commands"]:
                handler = plugin_info["sub_commands"][sub_command_key].get("function")
                is_sub_command = True
                logger.info(f"Identified sub-command: {main_command} {sub_command_key}")
            elif not is_sub_command and "handler" in plugin_info:
                handler = plugin_info.get("handler")
                logger.info(f"Identified top-level command: {main_command}")
            else:
                logger.warning(f"No valid handler found for command '{ai_command}' (main: '{main_command}', sub: '{sub_command_key}')")

            tool_result_str = ""
            success = True
            if handler:
                logger.info(f"Attempting to execute handler: {getattr(handler, '__name__', str(handler))} for command '{ai_command}' with params: '{actual_params}'")
                try:
                    import inspect
                    sig = inspect.signature(handler)
                    args_to_pass = {}
                    if 'params' in sig.parameters:
                        args_to_pass['params'] = actual_params
                    if 'conversation_history' in sig.parameters:
                        args_to_pass['conversation_history'] = self.conversation_history
                    if 'user_lang' in sig.parameters:
                        args_to_pass['user_lang'] = lang_code
                    if 'user' in sig.parameters:
                        args_to_pass['user'] = 'assistant'
                    tool_result = None
                    if inspect.iscoroutinefunction(handler):
                        tool_result = await handler(**args_to_pass)
                    else:
                        tool_result = await asyncio.to_thread(handler, **args_to_pass)
                    logger.info(f"Handler {getattr(handler, '__name__', str(handler))} returned: {tool_result}")
                    if isinstance(tool_result, tuple) and len(tool_result) == 2:
                        tool_result_str = str(tool_result[0])
                        success = bool(tool_result[1])
                    elif tool_result is not None:
                        tool_result_str = str(tool_result)
                        success = bool(tool_result_str)
                    else:
                        success = False
                except Exception as e:
                    logger.error(f"Error executing command '{ai_command}': {e}", exc_info=True)
                    tool_result_str = f"Przepraszam, wystąpił błąd podczas wykonywania komendy {ai_command}."
                    success = False
            # --- ZAWSZE wypowiedz tylko wynik narzędzia jeśli istnieje ---
            if tool_result_str:
                self.conversation_history.append({"role": "assistant", "content": tool_result_str})
                self.trim_conversation_history()
                asyncio.create_task(self.tts.speak(remove_chain_of_thought(tool_result_str)))
            elif ai_response_text:
                self.conversation_history.append({"role": "assistant", "content": ai_response_text})
                self.trim_conversation_history()
                asyncio.create_task(self.tts.speak(remove_chain_of_thought(ai_response_text)))
        else:
            # If AI response text exists and no valid command was issued
            if ai_response_text:
                self.conversation_history.append({"role": "assistant", "content": ai_response_text})
                self.trim_conversation_history()
                asyncio.create_task(self.tts.speak(remove_chain_of_thought(ai_response_text)))
            else:
                # Handle cases where AI might return empty response or invalid command format
                logger.warning("AI did not generate a valid text response or command.")
                fallback_text = "Przepraszam, nie zrozumiałem."
                # Avoid adding empty assistant messages to history
                # self.conversation_history.append({"role": "assistant", "content": fallback_text})
                # self.trim_conversation_history()
                asyncio.create_task(self.tts.speak(fallback_text))

        # History trimming is now done within the branches after adding messages

    def trim_conversation_history(self):
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]

    def trigger_manual_listen(self):
        """Puts a special marker onto the audio queue to trigger manual listening."""
        logger.info("Manual listen trigger requested via queue. Sending signal.")
        try:
            # Put a special marker onto the audio queue to interrupt the detector
            self.speech_recognizer.audio_q.put("__MANUAL_TRIGGER__")
        except Exception as e:
            logger.error(f"Failed to put manual trigger signal onto audio queue: {e}")
        # self.manual_listen_triggered = True # Flag is no longer needed

    async def process_command_queue(self):
        logger.info("Starting command queue processing task...")
        while True:
            try:
                if not self.command_queue.empty():
                    command_data = self.command_queue.get_nowait()
                    action = command_data.get("action")
                    logger.info(f"Received command from queue: {action}")
                    if action == "activate":
                        # Manual activation: natychmiast uruchom ścieżkę aktywacji (dźwięk + STT)
                        self.tts.cancel()
                        play_beep("keyword", loop=False)
                        command_text = None
                        try:
                            if self.use_whisper and self.whisper_asr:
                                logger.info("Recording audio for Whisper command (manual trigger)...")
                                audio_command = self.speech_recognizer.record_dynamic_command_audio()
                                if audio_command is not None:
                                    # Przekazujemy numpy.ndarray bezpośrednio do transcribe
                                    command_text = self.whisper_asr.transcribe(audio_command)
                                else:
                                    logger.warning("Failed to record audio for Whisper command (manual trigger).")
                            else:
                                logger.info("Listening for command with Vosk (manual trigger)...")
                                command_text = self.speech_recognizer.listen_command()
                            if command_text:
                                logger.info("Command (manual trigger): %s", command_text)
                                # process_query_callback musi być przekazany do Assistant, tu uproszczone:
                                if hasattr(self, 'process_query_callback'):
                                    asyncio.create_task(self.process_query_callback(command_text))
                                else:
                                    logger.warning("No process_query_callback set on Assistant instance!")
                            else:
                                logger.warning("No command detected after manual trigger.")
                        except Exception as cmd_e:
                            logger.error(f"Error during command listening/processing after manual trigger: {cmd_e}", exc_info=True)
                        continue
                    elif action == "config_updated":
                        logger.warning("Configuration updated via web UI. Initiating assistant restart.")
                        if self.loop:
                            self.loop.stop()
                        break
                    # ...existing code...
                await asyncio.sleep(1)
            except queue.Empty:
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in assistant command queue: {e}")

    def process_audio(self):
        """
        Główna pętla audio: obsługuje zarówno wake word, jak i ręczne wywołanie nasłuchu.
        Refactored logic for handling manual trigger interruption.
        """
        wake_word_task = None
        perform_manual_listen = False # Flag to indicate manual listen needed after task check

        while True:
            # --- Check for Manual Trigger Request ---
            if self.manual_listen_triggered:
                logger.info("Manual trigger flag is set.")
                self.manual_listen_triggered = False # Reset flag immediately
                perform_manual_listen = True # Set flag to perform listen below

                # If wake word task is running, attempt to interrupt it
                if wake_word_task and not wake_word_task.done():
                    logger.info("Attempting to interrupt running wake word task...")
                    try:
                        # Use put_nowait to avoid blocking if queue is full (shouldn't happen here)
                        self.speech_recognizer.audio_q.put_nowait("__MANUAL_TRIGGER__")
                        logger.info("Sent interruption signal to wake word detector queue.")
                        # Give it a moment to potentially stop or process the signal
                        time.sleep(0.3)
                    except queue.Full:
                         logger.error("Audio queue is full, cannot send interruption signal.")
                    except Exception as q_err:
                        logger.error(f"Failed to send interruption signal: {q_err}")
                else:
                    logger.info("Wake word task not running or already done when manual trigger checked.")


            # --- Check Wake Word Task Status ---
            # Check if task exists and is done
            if wake_word_task and wake_word_task.done():
                logger.info("Wake word task has finished.")
                interrupted_by_signal = False
                try:
                    result = wake_word_task.result() # Get result or raise exception if task failed
                    if result == "MANUAL_TRIGGER_REQUESTED":
                        logger.info("Wake word task confirmed interruption via signal.")
                        interrupted_by_signal = True
                        # If manual trigger wasn't already requested externally, set the flag now
                        if not perform_manual_listen:
                             logger.warning("Wake word task interrupted but manual flag wasn't set? Performing listen anyway.")
                             perform_manual_listen = True
                    # else: # Task finished normally (e.g., after processing a command)
                    #     logger.debug("Wake word task finished without manual trigger signal.")
                except Exception as e:
                    logger.error(f"Wake word detection task failed with exception: {e}", exc_info=True)
                    time.sleep(2) # Delay before restart after error

                wake_word_task = None # Reset task so it restarts later in the loop if needed

            # --- Perform Manual Listen (if flagged) ---
            if perform_manual_listen:
                logger.info("Proceeding with manual listen block.")
                perform_manual_listen = False # Reset flag for next iteration

                play_beep("keyword", loop=False)
                command_text = None
                try:
                    if self.use_whisper and self.whisper_asr:
                        logger.info("Recording audio for Whisper command (manual trigger)...")
                        # NOTE: This still requires record_dynamic_command_audio() to be implemented
                        # in SpeechRecognizer for Whisper to work on manual trigger.
                        try:
                            # TODO: Implement record_dynamic_command_audio in SpeechRecognizer
                            # audio_command = self.speech_recognizer.record_dynamic_command_audio() # Assuming this exists
                            # For now, log error as it's not implemented
                            logger.error("Whisper manual trigger failed: 'record_dynamic_command_audio' method not found in SpeechRecognizer.")
                            audio_command = None # Explicitly set to None

                            if audio_command is not None:
                                import soundfile as sf
                                import io
                                buffer = io.BytesIO()
                                sf.write(buffer, audio_command, 16000, format='WAV')
                                buffer.seek(0)
                                logger.info("Transcribing command with Whisper (manual trigger)...")
                                command_text = self.whisper_asr.transcribe(buffer)
                                buffer.close()
                            # else: # Already logged warning/error above
                            #    logger.warning("Failed to record audio for Whisper command (manual trigger).")
                        except AttributeError:
                             logger.error("Whisper manual trigger failed: 'record_dynamic_command_audio' method not found in SpeechRecognizer.")
                             # Fallback or inform user? For now, just log error.

                    else: # Use Vosk
                        logger.info("Listening for command with Vosk after manual trigger...")
                        # Corrected method name here based on traceback
                        command_text = self.speech_recognizer.listen_command()

                    # Process the command if recognized
                    if command_text:
                        logger.info("Command (after manual trigger): %s", command_text)
                        # Schedule the async process_query in the event loop
                        asyncio.run_coroutine_threadsafe(self.process_query(command_text), self.loop)
                    else:
                        logger.info("No command detected after manual trigger.")

                except Exception as e:
                    logger.error(f"Error during manually triggered listen execution: {e}", exc_info=True)

                logger.info("Manual listening block finished.")
                # Loop will continue and restart wake word task if wake_word_task is None


            # --- Start Wake Word Task (if needed) ---
            # Check if task is None (meaning it finished or never started)
            if wake_word_task is None:
                # Ensure we don't restart immediately after manual listen if wake word task was already running
                # This check might be redundant with the perform_manual_listen logic above, but adds safety
                if not perform_manual_listen:
                    logger.info("Starting/Restarting wake word detection task...")
                    # Run wake word detection in an executor thread
                    wake_word_task = self.loop.run_in_executor(
                        None, # Use default executor
                        run_wakeword_detection,
                        self.speech_recognizer,
                        self.wake_word,
                        self.tts,
                        self.use_whisper,
                        self.process_query, # Pass the async function directly
                        self.loop,
                        self.whisper_asr
                    )
                    # logger.info("Wake word detection task submitted to executor.")


            # --- Wait / Yield ---
            # Prevent tight loop; allow other asyncio tasks and checks to run
            time.sleep(0.1) # Small sleep in the main sync loop

    async def run_async(self):
        logger.info("Bot is starting...")
        self.loop = asyncio.get_running_loop()
        # Uruchomienie zadania monitorującego folder pluginów
        asyncio.create_task(self.monitor_plugins())
        # Start the command queue processing task
        asyncio.create_task(self.process_command_queue())

        self.speech_recognizer.audio_q.queue.clear()
        import sounddevice as sd
        try:
            with sd.RawInputStream(
                    samplerate=16000,
                    blocksize=8000,
                    dtype="int16",
                    channels=1,
                    device=self.speech_recognizer.mic_device_id,
                    callback=self.speech_recognizer.audio_callback
            ):
                logger.info("Audio stream opened. Waiting for activation...")
                # Run process_audio which now includes the manual trigger check
                await self.loop.run_in_executor(None, self.process_audio)
        except Exception as e:
            logger.error("Error in audio stream: %s", e)
        logger.info("Audio processing ended. Blocking main loop indefinitely.")
        await asyncio.Future() # Keep running

    def get_all_memories_for_user(self, user: str = "assistant") -> list:
        """
        Zwraca wszystkie treści wspomnień dla danego użytkownika (bez metadanych).
        """
        from modules.memory_module import retrieve_memories
        result, success = retrieve_memories(params="", user=user)
        if not success:
            return []
        return [line for line in result.split("\n") if line.strip()]

# Remove the old listen_and_process method if it exists, run_async is the main entry point now.

if __name__ == "__main__":
    # Config is loaded automatically when config.py is imported
    # No need to import specific variables here unless overriding defaults for testing
    # from config import VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD

    logging.basicConfig(
        level=logging.WARNING, # Zmieniono z INFO na WARNING
        filename="assistant.log",
        filemode="a",
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    # Example of running standalone (without web ui queue)
    assistant = Assistant()
    try:
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant terminated by user.")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
