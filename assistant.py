import asyncio, json, logging, os, glob, importlib.util, re, subprocess, multiprocessing, time
import ollama
import inspect # Add inspect import
import queue # Import queue for Empty exception

# Import modułów audio z nowej lokalizacji
from audio_modules.tts_module import TTSModule
from audio_modules.speech_recognition import SpeechRecognizer
from audio_modules.beep_sounds import play_beep
from audio_modules.wakeword_detector import run_wakeword_detection

# Import funkcji AI z nowego modułu
from ai_module import refine_query, generate_response, parse_response, remove_chain_of_thought

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
# MAX_HISTORY_LENGTH is now loaded from config

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
        new_modules = {}
        # Przechodzimy przez wszystkie pliki z rozszerzeniem .py w folderze pluginów
        for filepath in glob.glob(os.path.join(plugin_folder, "*.py")):
            mod_time = os.path.getmtime(filepath)
            self.plugin_mod_times[filepath] = mod_time
            module_name = os.path.splitext(os.path.basename(filepath))[0]
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
        # Intent classification (new layer)
        intent = IntentClassifier().classify(refined_query)
        logger.info("Intent classified as: %s", intent)
        # Add user message BEFORE calling the main model
        self.conversation_history.append({"role": "user", "content": refined_query, "intent": intent})
        self.trim_conversation_history() # Trim history *before* sending to model

        # Przygotowanie listy dostępnych funkcji (tool descriptions)
        # This could be enhanced for MCP with JSON schema descriptions
        functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])

        # Generowanie odpowiedzi przy użyciu funkcji z ai_module
        # Pass current history and function descriptions
        response_text = generate_response(self.conversation_history, functions_info)
        logger.info("AI response: %s", response_text)

        structured_output = parse_response(response_text)

        # Extract potential command and parameters
        ai_command = structured_output.get("command")
        ai_params = structured_output.get("params", "")
        ai_response_text = structured_output.get("text", "") # Text AI wants to say *before* or *instead* of tool use

        # --- Tool Execution Logic ---
        if ai_command and ai_command in self.modules:
            plugin_info = self.modules[ai_command]
            handler = plugin_info.get("handler")

            # Speak the AI's preliminary text if provided, before running the tool
            if ai_response_text:
                 # Add AI's preliminary text to history
                 self.conversation_history.append({"role": "assistant", "content": ai_response_text})
                 self.trim_conversation_history()
                 asyncio.create_task(self.tts.speak(remove_chain_of_thought(ai_response_text)))
                 # Optional: Add a small delay so TTS can start before tool runs
                 await asyncio.sleep(0.5)

            if handler:
                try:
                    # Prepare context for the tool handler
                    tool_context = {
                        "params": ai_params,
                        "conversation_history": self.conversation_history,
                        # Pass the main system prompt, tools can use/ignore it
                        "system_prompt": SYSTEM_PROMPT,
                        # Optionally add tool-specific prompt if defined in register()
                        "tool_prompt": plugin_info.get("prompt")
                    }

                    # Check handler signature and call appropriately
                    sig = inspect.signature(handler)
                    args_to_pass = {}
                    if 'params' in sig.parameters:
                         args_to_pass['params'] = ai_params
                    if 'conversation_history' in sig.parameters:
                         args_to_pass['conversation_history'] = self.conversation_history
                    # Add more checks if needed (e.g., for system_prompt)

                    # Check if the handler is async or sync
                    if inspect.iscoroutinefunction(handler):
                        # Await async handler directly
                        if args_to_pass:
                             tool_result = await handler(**args_to_pass)
                        else: # Handle case where async handler takes no expected args
                             tool_result = await handler() # Or adjust based on expected signature
                    else:
                        # Run sync handler in a thread
                        if args_to_pass:
                            tool_result = await asyncio.to_thread(handler, **args_to_pass)
                        else: # Handle case where sync handler takes no expected args
                            tool_result = await asyncio.to_thread(handler) # Or adjust

                    # Add tool result to history (as assistant response)
                    if tool_result:
                        # Ensure result is string before adding/speaking
                        tool_result_str = str(tool_result)
                        self.conversation_history.append({"role": "assistant", "content": tool_result_str})
                        self.trim_conversation_history()
                        # Speak the final result from the tool
                        # Ensure TTS gets the final string result
                        asyncio.create_task(self.tts.speak(remove_chain_of_thought(tool_result_str)))
                    else:
                        logger.warning(f"Handler for command '{ai_command}' returned no result.")

                except Exception as e:
                    logger.error(f"Error executing command '{ai_command}': {e}", exc_info=True)
                    error_text = f"Przepraszam, wystąpił błąd podczas wykonywania komendy {ai_command}."
                    self.conversation_history.append({"role": "assistant", "content": error_text})
                    self.trim_conversation_history()
                    asyncio.create_task(self.tts.speak(error_text))
            else:
                logger.warning(f"No handler found for command: {ai_command}")
                # Speak the AI text even if handler is missing
                if ai_response_text:
                     # Already added to history and spoken above
                     pass
                else: # If AI only returned a command but no text and handler is missing
                     fallback_text = f"Nie wiem jak wykonać komendę {ai_command}."
                     self.conversation_history.append({"role": "assistant", "content": fallback_text})
                     self.trim_conversation_history()
                     asyncio.create_task(self.tts.speak(fallback_text))

        # --- No Tool Execution ---
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
        """Processes commands received from the web UI queue."""
        if not self.command_queue:
            logger.info("No command queue provided, skipping queue processing task.")
            return
        logger.info("Starting command queue processing task...")
        while True:
            try:
                if not self.command_queue.empty():
                    command_data = self.command_queue.get_nowait()
                    action = command_data.get("action")
                    logger.info(f"Received command from queue: {action}")
                    if action == "activate":
                        self.trigger_manual_listen()
                    elif action == "config_updated":
                        logger.warning("Configuration updated via web UI. Initiating assistant restart.")
                        # Stop the main loop to allow the process to exit cleanly
                        if self.loop:
                            self.loop.stop()
                        # No need to call reload_config_values() here, restart will load fresh config
                        break # Exit the queue processing loop
                    # Add more actions as needed
                await asyncio.sleep(1) # Check queue periodically
            except queue.Empty:
                 await asyncio.sleep(1) # Wait if queue is empty
            except Exception as e:
                logger.error(f"Error processing command queue: {e}", exc_info=True)
                await asyncio.sleep(5) # Wait longer after an error
        logger.info("Command queue processing task stopped.")

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

# Remove the old listen_and_process method if it exists, run_async is the main entry point now.

if __name__ == "__main__":
    # Config is loaded automatically when config.py is imported
    # No need to import specific variables here unless overriding defaults for testing
    # from config import VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD

    logging.basicConfig(
        level=logging.INFO,
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
