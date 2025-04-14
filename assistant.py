import asyncio, json, logging, os, glob, importlib.util, re, subprocess
import ollama
import inspect # Add inspect import

# Import modułów audio z nowej lokalizacji
from audio_modules.tts_module import TTSModule
from audio_modules.speech_recognition import SpeechRecognizer
from audio_modules.beep_sounds import play_beep
from audio_modules.wakeword_detector import run_wakeword_detection

# Import funkcji AI z nowego modułu
from ai_module import refine_query, generate_response, parse_response, remove_chain_of_thought

# Import specific config variables needed
from config import (
    VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD,
    USE_WHISPER_FOR_COMMAND, WHISPER_MODEL, MAX_HISTORY_LENGTH, PLUGIN_MONITOR_INTERVAL
)
from prompts import CONVERT_QUERY_PROMPT, SYSTEM_PROMPT


logger = logging.getLogger(__name__)
# MAX_HISTORY_LENGTH is now loaded from config

class Assistant:
    def __init__(self, vosk_model_path: str = VOSK_MODEL_PATH, mic_device_id: int = MIC_DEVICE_ID, wake_word: str = WAKE_WORD, stt_silence_threshold: int = STT_SILENCE_THRESHOLD):
        self.wake_word = wake_word.lower()
        self.conversation_history = []
        self.tts = TTSModule()
        self.speech_recognizer = SpeechRecognizer(vosk_model_path, mic_device_id, stt_silence_threshold)
        self.modules = {}
        self.plugin_mod_times = {}  # słownik do przechowywania czasu modyfikacji plików pluginów
        self.load_plugins()
        self.loop = None
        self.use_whisper = USE_WHISPER_FOR_COMMAND
        self.max_history_length = MAX_HISTORY_LENGTH # Use loaded config value
        self.plugin_monitor_interval = PLUGIN_MONITOR_INTERVAL # Use loaded config value
        if self.use_whisper:
            from audio_modules.whisper_asr import WhisperASR
            self.whisper_asr = WhisperASR(model_name=WHISPER_MODEL)

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
        # Używamy funkcji refine_query z ai_module
        refined_query = refine_query(text_input)
        logger.info("Refined query: %s", refined_query)
        # Add user message BEFORE calling the main model
        self.conversation_history.append({"role": "user", "content": refined_query})
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

    def process_audio(self):
        # Wywołujemy funkcję wykrywania wake word z nowego modułu
        run_wakeword_detection(
            speech_recognizer=self.speech_recognizer,
            wake_word=self.wake_word,
            tts=self.tts,
            use_whisper=self.use_whisper,
            process_query_callback=self.process_query,
            loop=self.loop,
            whisper_asr=self.whisper_asr if self.use_whisper else None
        )

    async def run_async(self):
        logger.info("Bot is starting...")
        self.loop = asyncio.get_running_loop()
        # Uruchomienie zadania monitorującego folder pluginów
        asyncio.create_task(self.monitor_plugins())
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
                await self.loop.run_in_executor(None, self.process_audio)
        except Exception as e:
            logger.error("Error in audio stream: %s", e)
        logger.info("Audio processing ended. Blocking main loop indefinitely.")
        await asyncio.Future()

    async def listen_and_process(self):
        """Main loop: waits for wake word, listens for command, processes it."""
        self.loop = asyncio.get_running_loop()
        logger.info("Bot is starting...")
        # Start plugin monitor in the background
        asyncio.create_task(self.monitor_plugins())

        while True:
            logger.info("Audio stream opened. Waiting for activation...")
            detected = await self.loop.run_in_executor(None, run_wakeword_detection, self.wake_word, self.speech_recognizer.stream, self.speech_recognizer.CHUNK)

            if detected:
                # Play keyword beep only once - ENSURE loop=False is passed
                play_beep("keyword", loop=False)
                logger.info("Listening for command using %s (dynamic recording)...", "Whisper" if self.use_whisper else "Vosk")

                if self.use_whisper:
                    command_text = await self.whisper_asr.listen_for_command_dynamic(self.speech_recognizer.p, self.speech_recognizer.stream, self.speech_recognizer.CHUNK, self.speech_recognizer.RATE, self.speech_recognizer.FORMAT)
                else:
                    command_text = await self.loop.run_in_executor(None, self.speech_recognizer.listen_for_command_dynamic)

                if command_text:
                    logger.info("Command: %s", command_text)
                    await self.process_query(command_text)
                else:
                    logger.info("No command detected or recognized.")
            else:
                # No need to log wake word not detected every time, maybe change level or remove?
                # logger.info("Wake word not detected clearly or timeout.")
                pass # Keep listening silently


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
    # Assistant now uses defaults from loaded config
    assistant = Assistant()
    try:
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant terminated by user.")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
