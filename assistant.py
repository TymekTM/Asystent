import asyncio
import json
import logging
import os
import glob
import importlib.util
from tts_module import TTSModule
from speech_recognition import SpeechRecognizer
import ollama

logger = logging.getLogger(__name__)

class Assistant:
    def __init__(self, vosk_model_path: str, mic_device_id: int, wake_word: str, stt_silence_threshold: int = 600):
        self.wake_word = wake_word.lower()
        self.conversation_history = []
        self.tts = TTSModule()
        self.speech_recognizer = SpeechRecognizer(vosk_model_path, mic_device_id, stt_silence_threshold)
        self.modules = {}
        self.load_plugins()
        self.loop = None

    def load_plugins(self):
        plugin_folder = "modules"
        if not os.path.exists(plugin_folder):
            os.makedirs(plugin_folder)
        for filepath in glob.glob(os.path.join(plugin_folder, "*.py")):
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "register"):
                plugin_info = module.register()
                command = plugin_info.get("command")
                if command:
                    self.modules[command] = plugin_info
                    logger.info("Loaded plugin: %s -> %s", command, plugin_info.get("description"))

    async def process_query(self, text_input: str):
        # Przerwij bieżący TTS
        self.tts.cancel()
        logger.info("User query received: %s", text_input)
        command = None
        params = ""
        lower_text = text_input.lower().strip()
        logger.debug("Lowercase text: %s", lower_text)

        # Wykrywanie komend – obsługa zarówno z wykrzyknikiem, jak i bez niego
        if lower_text.startswith("!"):
            parts = text_input.strip().split(maxsplit=1)
            command = parts[0]
            params = parts[1] if len(parts) > 1 else ""
            logger.info("Detected command with '!': %s, params: %s", command, params)
        elif lower_text.startswith("search ") or lower_text.startswith("wyszukaj "):
            command = "!search"
            params = text_input[len("search "):] if lower_text.startswith("search ") else text_input[len("wyszukaj "):]
            logger.info("Detected search command: %s, params: %s", command, params)
        elif lower_text.startswith("screenshot"):
            command = "!screenshot"
            params = text_input[len("screenshot"):].strip()
            logger.info("Detected screenshot command: %s, params: %s", command, params)

        # Jeśli użytkownik bezpośrednio wywołał komendę, wykonaj handler i zakończ działanie
        if command and command in self.modules:
            logger.debug("Found module for command: %s", command)
            handler = self.modules[command]["handler"]
            try:
                logger.info("Executing handler for command: %s", command)
                module_result = await asyncio.to_thread(handler, params)
                logger.info("Handler for command %s completed with result: %s", command, module_result)
            except Exception as e:
                logger.error("Error executing handler for %s: %s", command, e)
                module_result = f"Error executing command {command}: {e}"

            self.conversation_history.append({"role": "user", "content": text_input})
            if command == "!screenshot":
                confirm_text = f"Command {command} executed. Screenshot captured."
                self.conversation_history.append({"role": "assistant", "content": confirm_text})
                await self.tts.speak(confirm_text)
                # Drugi prompt – zawiera ścieżkę do pliku
                module_result_text = f"Screenshot file path: {module_result}"
            else:
                module_result_text = module_result

            # Budujemy prompt z wynikiem modułu
            prompt_with_module = (
                f"Based on the following data, provide an answer:\n\n{module_result_text}\n\n"
                "Answer briefly in no more than 2 sentences."
            )
            logger.info("Sending module result to AI prompt: %s", prompt_with_module)
            self.conversation_history.append({"role": "assistant", "content": prompt_with_module})
            try:
                functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])
                system_prompt = (
                    "Answer briefly in no more than 2 sentences. "
                    "To call a function, your input must start with its name preceded by an exclamation mark."
                )
                if functions_info:
                    system_prompt += " Available functions: " + functions_info
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(self.conversation_history)
                logger.debug("Sending messages to AI: %s", messages)
                response = ollama.chat(model="gemma3", messages=messages)
                ai_response = response["message"]["content"]
                logger.info("AI response after module call: %s", ai_response)
            except Exception as e:
                logger.error("Error communicating with AI: %s", e)
                ai_response = f"Error communicating with AI: {e}"

            self.conversation_history.append({"role": "assistant", "content": ai_response})
            await self.tts.speak(ai_response)
            return

        # Standardowa obsługa zapytań – przetwarzamy zapytanie przez AI
        try:
            response = ollama.chat(
                model="gemma3",
                messages=[
                    {"role": "system",
                     "content": "Convert the following query into a short, precise question without extra queries."},
                    {"role": "user", "content": text_input}
                ]
            )
            refined_query = response["message"]["content"].strip()
            logger.info("Refined query: %s", refined_query)
        except Exception as e:
            logger.error("Error processing query with Ollama: %s", e)
            refined_query = text_input

        self.conversation_history.append({"role": "user", "content": refined_query})
        try:
            functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])
            system_prompt = (
                "Answer briefly in no more than 2 sentences. "
                "To call a function, your input must start with its name preceded by an exclamation mark (e.g. !screenshot, !search)."
            )
            if functions_info:
                system_prompt += " Available functions: " + functions_info
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history)
            logger.debug("Sending messages to AI: %s", messages)
            response = ollama.chat(model="gemma3", messages=messages)
            ai_response = response["message"]["content"]
            logger.info("Initial AI response: %s", ai_response)
        except Exception as e:
            logger.error("Error communicating with AI: %s", e)
            ai_response = "Sorry, there was an error communicating with the AI."

        # Jeśli odpowiedź AI zaczyna się od tagu funkcji, wykonaj ją automatycznie
        trimmed = ai_response.strip()
        if trimmed.startswith("!"):
            parts = trimmed.split(maxsplit=1)
            ai_command = parts[0]
            ai_params = parts[1] if len(parts) > 1 else ""
            if ai_command in self.modules:
                logger.info("AI triggered module command: %s, params: %s", ai_command, ai_params)
                try:
                    module_result = await asyncio.to_thread(self.modules[ai_command]["handler"], ai_params)
                    logger.info("Module command %s executed with result: %s", ai_command, module_result)
                except Exception as e:
                    logger.error("Error executing module command triggered by AI: %s", e)
                    module_result = f"Error executing command {ai_command}: {e}"
                new_prompt = (
                    f"Based on the following data, provide an answer:\n\n{module_result}\n\n"
                    "Answer briefly in no more than 2 sentences."
                )
                logger.info("Sending new prompt to AI: %s", new_prompt)
                self.conversation_history.append({"role": "assistant", "content": new_prompt})
                try:
                    functions_info = ", ".join([f"{cmd} - {info['description']}" for cmd, info in self.modules.items()])
                    system_prompt = (
                        "Answer briefly in no more than 2 sentences. "
                        "To call a function, your input must start with its name preceded by an exclamation mark."
                    )
                    if functions_info:
                        system_prompt += " Available functions: " + functions_info
                    messages = [{"role": "system", "content": system_prompt}]
                    messages.extend(self.conversation_history)
                    logger.debug("Sending messages to AI for second prompt: %s", messages)
                    response2 = ollama.chat(model="gemma3", messages=messages)
                    new_ai_response = response2["message"]["content"]
                    logger.info("New AI response after module call: %s", new_ai_response)
                except Exception as e:
                    logger.error("Error communicating with AI after module call: %s", e)
                    new_ai_response = f"Error communicating with AI: {e}"
                self.conversation_history.append({"role": "assistant", "content": new_ai_response})
                await self.tts.speak(new_ai_response)
                return

        # Jeśli odpowiedź nie wywołuje funkcji, kontynuujemy normalnie
        if ai_response.strip():
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            await self.tts.speak(ai_response)
        else:
            logger.warning("AI did not generate a response.")

    def process_audio(self):
        logger.info("Starting audio processing loop.")
        from vosk import KaldiRecognizer
        recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)
        while True:
            try:
                data = self.speech_recognizer.audio_q.get()
            except Exception as e:
                logger.error("Error getting audio data: %s", e)
                continue
            try:
                partial_result = json.loads(recognizer.PartialResult())
                partial_text = partial_result.get("partial", "").lower()
            except Exception as e:
                logger.error("Error processing partial result: %s", e)
                partial_text = ""
            if self.wake_word in partial_text:
                logger.info("Wake word detected in partial result.")
                command_text = self.speech_recognizer.listen_command()
                if command_text:
                    logger.info("Detected command: %s", command_text)
                    asyncio.run_coroutine_threadsafe(self.process_query(command_text), self.loop)
                else:
                    logger.warning("No command detected from partial result.")
                recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)
                continue
            if recognizer.AcceptWaveform(data):
                try:
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").lower()
                except Exception as e:
                    logger.error("Error processing full result: %s", e)
                    text = ""
                if self.wake_word in text:
                    logger.info("Wake word detected in full result.")
                    command_text = self.speech_recognizer.listen_command()
                    if command_text:
                        logger.info("Detected command: %s", command_text)
                        asyncio.run_coroutine_threadsafe(self.process_query(command_text), self.loop)
                    else:
                        logger.warning("No command detected from full result.")
                else:
                    logger.debug("Speech detected but wake word not found.")
                recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)

    async def run_async(self):
        self.loop = asyncio.get_running_loop()
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
            ) as stream:
                logger.info("Audio stream opened. Waiting for activation...")
                await self.loop.run_in_executor(None, self.process_audio)
        except Exception as e:
            logger.error("Error in audio stream: %s", e)
        logger.info("Audio processing ended. Blocking main loop indefinitely.")
        await asyncio.Future()  # Block forever

if __name__ == "__main__":
    from config import VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD
    assistant = Assistant(VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD)
    try:
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant terminated by user.")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
