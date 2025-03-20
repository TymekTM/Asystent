import asyncio, json, logging, os, glob, importlib.util, re, subprocess, inspect
import ollama
from sympy.codegen import Print

from tts_module import TTSModule
from speech_recognition import SpeechRecognizer
from prompts import CONVERT_QUERY_PROMPT, SYSTEM_PROMPT
from config import (
    VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD,
    USE_WHISPER_FOR_COMMAND, WHISPER_MODEL, STT_MODEL, MAIN_MODEL, DEEP_MODEL
)

logger = logging.getLogger(__name__)
MAX_HISTORY_LENGTH = 20

def remove_chain_of_thought(text: str) -> str:
    pattern = r"<think>.*?</think>|<\|begin_of_thought\|>.*?<\|end_of_thought\|>|<\|begin_of_solution\|>.*?<\|end_of_solution\|>|<\|end\|>"
    return re.sub(pattern, "", text, flags=re.DOTALL)

def extract_json(text: str) -> str:
    """
    Próbuje wyekstrahować fragment JSON z tekstu.
    Usuwa znaczniki kodu (np. ```json) oraz inne otoczenia, jeśli występują.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
        text = "\n".join(lines).strip()
    match = re.search(r'({.*})', text, re.DOTALL)
    if match:
        return match.group(1)
    return text

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
            from whisper_asr import WhisperASR
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
        try:
            response = ollama.chat(
                model=STT_MODEL,
                messages=[
                    {"role": "system", "content": CONVERT_QUERY_PROMPT},
                    {"role": "user", "content": text_input}
                ]
            )
            refined_query = response["message"]["content"].strip()
            logger.info("Refined query: %s", refined_query)
        except Exception as e:
            logger.error("Error refining query: %s", e)
            refined_query = text_input

        self.conversation_history.append({"role": "user", "content": refined_query})
        try:
            functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])
            system_prompt = SYSTEM_PROMPT + (" Dostępne funkcje: " + functions_info if functions_info else "")
            messages = [{"role": "system", "content": system_prompt}] + self.conversation_history
            logger.debug("Sending messages: %s", messages)
            response = ollama.chat(model=MAIN_MODEL, messages=messages)
            ai_response = response["message"]["content"]
            logger.info("AI response: %s", ai_response)
        except Exception as e:
            logger.error("Error communicating with AI: %s", e)
            ai_response = '{"command": "", "params": "", "text": "Przepraszam, wystąpił błąd podczas komunikacji z AI."}'

        ai_response_extracted = extract_json(ai_response)
        try:
            structured_output = json.loads(ai_response_extracted)
        except json.JSONDecodeError:
            structured_output = None

        if structured_output and isinstance(structured_output, dict):
            if "command" in structured_output and structured_output["command"]:
                ai_command = structured_output["command"]
                ai_params = structured_output.get("params", "")
                feedback = f"Ok, processing command: {ai_params}"
                asyncio.create_task(self.tts.speak(feedback))
                handler = self.modules[ai_command]["handler"]
                try:
                    result = await asyncio.to_thread(handler, ai_params)
                    self.conversation_history.append({"role": "assistant", "content": result})
                    asyncio.create_task(self.tts.speak(remove_chain_of_thought(result)))
                except Exception as e:
                    logger.error("Error executing AI-triggered command: %s", e)
                    error_text = f"Błąd wykonania komendy {ai_command}: {e}"
                    self.conversation_history.append({"role": "assistant", "content": error_text})
                    asyncio.create_task(self.tts.speak(error_text))
                self.trim_conversation_history()
                return
            if "text" in structured_output:
                ai_response = structured_output["text"]
            else:
                ai_response = ""
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
        from vosk import KaldiRecognizer
        recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)
        while True:
            try:
                data = self.speech_recognizer.audio_q.get()
            except Exception as e:
                logger.error("Error getting audio data: %s", e)
                continue
            try:
                partial = json.loads(recognizer.PartialResult()).get("partial", "").lower()
            except Exception as e:
                logger.error("Error processing partial result: %s", e)
                partial = ""
            if self.wake_word in partial:
                logger.info("Wake word detected (partial).")
                self.tts.cancel()
                subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "beep.mp3"])
                if self.use_whisper:
                    audio_command = self.speech_recognizer.record_dynamic_command_audio()
                    import soundfile as sf
                    temp_filename = "temp_command.wav"
                    sf.write(temp_filename, audio_command, 16000)
                    command_text = self.whisper_asr.transcribe(temp_filename)
                    os.remove(temp_filename)
                else:
                    command_text = self.speech_recognizer.listen_command()
                if command_text:
                    logger.info("Command: %s", command_text)
                    asyncio.run_coroutine_threadsafe(self.process_query(command_text), self.loop)
                else:
                    logger.warning("No command detected (partial).")
                recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)
                continue
            if recognizer.AcceptWaveform(data):
                try:
                    result = json.loads(recognizer.Result()).get("text", "").lower()
                except Exception as e:
                    logger.error("Error processing full result: %s", e)
                    result = ""
                if self.wake_word in result:
                    logger.info("Wake word detected (full).")
                    self.tts.cancel()
                    subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "beep.mp3"])
                    if self.use_whisper:
                        audio_command = self.speech_recognizer.record_dynamic_command_audio()
                        import soundfile as sf
                        temp_filename = "temp_command.wav"
                        sf.write(temp_filename, audio_command, 16000)
                        command_text = self.whisper_asr.transcribe(temp_filename)
                        os.remove(temp_filename)
                    else:
                        command_text = self.speech_recognizer.listen_command()
                    if command_text:
                        logger.info("Command: %s", command_text)
                        asyncio.run_coroutine_threadsafe(self.process_query(command_text), self.loop)
                    else:
                        logger.warning("No command detected (full).")
                else:
                    logger.debug("Speech detected, wake word not found.")
                recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)

    async def run_async(self):
        logger.info("Bot is starting...")  # log przy starcie bota
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
