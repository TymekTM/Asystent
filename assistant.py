import asyncio, json, logging, os, glob, importlib.util, re, subprocess
import ollama

# Import modułów audio z nowej lokalizacji
from audio_modules.tts_module import TTSModule
from audio_modules.speech_recognition import SpeechRecognizer
from audio_modules.beep_sounds import play_beep
from audio_modules.wakeword_detector import run_wakeword_detection

# Import funkcji AI z nowego modułu
from ai_module import refine_query, generate_response, parse_response, remove_chain_of_thought

from prompts import CONVERT_QUERY_PROMPT, SYSTEM_PROMPT
from config import (
    VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD,
    USE_WHISPER_FOR_COMMAND, WHISPER_MODEL
)

logger = logging.getLogger(__name__)
MAX_HISTORY_LENGTH = 20


class Assistant:
    def __init__(self, vosk_model_path: str, mic_device_id: int, wake_word: str, stt_silence_threshold: int = 600):
        self.wake_word = wake_word.lower()
        self.conversation_history = []
        self.tts = TTSModule()
        self.speech_recognizer = SpeechRecognizer(vosk_model_path, mic_device_id, stt_silence_threshold)
        self.modules = {}
        self.plugin_mod_times = {}  # słownik do przechowywania czasu modyfikacji plików pluginów
        self.load_plugins()
        self.loop = None
        self.use_whisper = USE_WHISPER_FOR_COMMAND
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

    async def monitor_plugins(self, interval: int = 30):
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
        self.conversation_history.append({"role": "user", "content": refined_query})

        # Przygotowanie listy dostępnych funkcji
        functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])

        # Generowanie odpowiedzi przy użyciu funkcji z ai_module
        response_text = generate_response(self.conversation_history, functions_info)
        logger.info("AI response: %s", response_text)

        structured_output = parse_response(response_text)

        # Jeśli AI zwróciło polecenie, wykonujemy je przez odpowiedni handler z pluginu
        if structured_output.get("command"):
            ai_command = structured_output["command"]
            ai_params = structured_output.get("params", "")
            feedback = f"Ok, processing command: {ai_params}"
            asyncio.create_task(self.tts.speak(feedback))
            handler = self.modules.get(ai_command, {}).get("handler")
            if handler:
                try:
                    result = await asyncio.to_thread(handler, ai_params)
                    self.conversation_history.append({"role": "assistant", "content": result})
                    asyncio.create_task(self.tts.speak(remove_chain_of_thought(result)))
                except Exception as e:
                    logger.error("Error executing AI-triggered command: %s", e)
                    error_text = f"Błąd wykonania komendy {ai_command}: {e}"
                    self.conversation_history.append({"role": "assistant", "content": error_text})
                    asyncio.create_task(self.tts.speak(error_text))
            else:
                logger.warning("Nie znaleziono handlera dla komendy: %s", ai_command)
            self.trim_conversation_history()
            return

        # Jeśli nie ma polecenia, przetwarzamy zwykłą odpowiedź
        ai_response = structured_output.get("text", response_text)
        if ai_response.strip():
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            asyncio.create_task(self.tts.speak(remove_chain_of_thought(ai_response)))
        else:
            logger.warning("AI did not generate a response.")
        self.trim_conversation_history()

    def trim_conversation_history(self):
        if len(self.conversation_history) > MAX_HISTORY_LENGTH:
            self.conversation_history = self.conversation_history[-MAX_HISTORY_LENGTH:]

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


if __name__ == "__main__":
    from config import VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD

    logging.basicConfig(
        level=logging.INFO,
        filename="assistant.log",
        filemode="a",
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    assistant = Assistant(VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD)
    try:
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant terminated by user.")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
