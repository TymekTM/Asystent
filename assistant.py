import asyncio
import json
import logging
import os
import glob
import importlib.util
import re

import ollama  # Zakładamy, że ollama jest używane do komunikacji z modelem

from tts_module import TTSModule
from speech_recognition import SpeechRecognizer
from prompts import (
    CONVERT_QUERY_PROMPT, SYSTEM_PROMPT,
)
from config import STT_MODEL, MAIN_MODEL, DEEP_MODEL  # <-- import modeli

logger = logging.getLogger(__name__)

# Ustalona liczba wiadomości przechowywanych w historii
MAX_HISTORY_LENGTH = 20

def remove_chain_of_thought(text: str) -> str:
    """
    Usuwa zawartość (wraz z tagami) dla wszystkich poniższych par:
      - <think>...</think>
      - <|begin_of_thought|>...</|end_of_thought|>
      - <|begin_of_solution|>...</|end_of_solution|>
    """
    pattern = r"<think>.*?</think>|<\|begin_of_thought\|>.*?<\|end_of_thought\|>|<\|begin_of_solution\|>.*?<\|end_of_solution\|>|<\|end\|>"
    # DOTALL sprawia, że kropka `.` łapie także znaki nowej linii
    return re.sub(pattern, "", text, flags=re.DOTALL)

class Assistant:
    def __init__(
            self,
            vosk_model_path: str,
            mic_device_id: int,
            wake_word: str,
            stt_silence_threshold: int = 600
    ):
        self.wake_word = wake_word.lower()
        self.conversation_history = []
        self.tts = TTSModule()
        self.speech_recognizer = SpeechRecognizer(
            vosk_model_path,
            mic_device_id,
            stt_silence_threshold
        )
        self.modules = {}  # Tu załadujemy pluginy
        self.load_plugins()
        self.loop = None  # Pętla asynchroniczna

    def load_plugins(self):
        """
        Przeszukuje folder modules/ i ładuje każdy plik .py, który
        posiada funkcję register().
        """
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
                    logger.info(
                        "Loaded plugin: %s -> %s",
                        command, plugin_info.get("description")
                    )
                else:
                    logger.warning("Plugin %s nie zawiera klucza 'command'. Pomijam.", module_name)
            else:
                logger.debug("Plik %s nie zawiera funkcji register(). Pomijam.", filepath)

    def _detect_command(self, text_input: str):
        """
        Dynamicznie wykrywa, czy text_input zawiera jakąś komendę (zarówno z '!' jak i aliasy).
        Zwraca (command, params) lub (None, "") jeśli brak dopasowania.
        """
        lower_text = text_input.lower().strip()

        # 1. Sprawdź, czy tekst zaczyna się od "!"
        if lower_text.startswith("!"):
            parts = text_input.strip().split(maxsplit=1)
            possible_cmd = parts[0]  # np. "!search"
            params = parts[1] if len(parts) > 1 else ""
            if possible_cmd in self.modules:
                logger.info("Detected command with '!': %s, params: %s", possible_cmd, params)
                return (possible_cmd, params)

        # 2. Sprawdź aliasy – iteruj po wczytanych modułach
        for cmd, plugin_info in self.modules.items():
            aliases = plugin_info.get("aliases", [])
            for alias in aliases:
                alias_lower = alias.lower()
                if lower_text == alias_lower:
                    # np. user wpisał samo "search"
                    logger.info("Detected alias command: %s -> real command: %s (no params)", alias, cmd)
                    return (cmd, "")
                if lower_text.startswith(alias_lower + " "):
                    params = text_input[len(alias):].strip()
                    logger.info("Detected alias command: %s -> real command: %s, params: %s", alias, cmd, params)
                    return (cmd, params)

        # 3. Brak dopasowania
        return (None, "")

    async def process_query(self, text_input: str):
        """
        Główna logika przetwarzania poleceń:
          - Jeśli wykryjemy komendę (!coś) to używamy modułu
          - W innym wypadku normalna obsługa przez model AI
            * Najpierw refine zapytania przez model STT_MODEL
            * Potem finalna odpowiedź przez MAIN_MODEL
        """
        # 1. Spróbuj dynamicznie wykryć komendę
        command, params = self._detect_command(text_input)

        # 2. Jeśli to komenda, wołamy odpowiedni moduł
        if command and command in self.modules:
            handler = self.modules[command]["handler"]
            try:
                module_result = await asyncio.to_thread(handler, params)
                logger.info("Handler for command %s completed with result: %s", command, module_result)
            except Exception as e:
                logger.error("Error executing handler for %s: %s", command, e)
                module_result = f"Błąd wykonania komendy {command}: {e}"

            # Dodaj do historii
            self.conversation_history.append({"role": "user", "content": text_input})
            self.conversation_history.append({"role": "assistant", "content": module_result})

            # CHANGED: przed TTS usuwamy <think>...</think>
            to_speak = remove_chain_of_thought(module_result)
            await self.tts.speak(to_speak)

            self.trim_conversation_history()
            return

        # --- 3. Jeśli nie wykryto żadnej komendy, standardowa obsługa przez AI ---
        # Najpierw "czyszczenie" (CONVERT_QUERY_PROMPT) -> model STT_MODEL
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
            logger.error("Error processing query with Ollama (refine): %s", e)
            refined_query = text_input

        self.conversation_history.append({"role": "user", "content": refined_query})

        # Następnie właściwe zapytanie do MAIN_MODEL
        try:
            # Zbuduj system prompt z listą dostępnych funkcji
            functions_info = ", ".join([
                f"{cmd} - {info['description']}"
                for cmd, info in self.modules.items()
            ])
            system_prompt = SYSTEM_PROMPT
            if functions_info:
                system_prompt += " Dostępne funkcje: " + functions_info

            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(self.conversation_history)

            logger.debug("Sending messages to AI: %s", messages)
            response = ollama.chat(model=MAIN_MODEL, messages=messages)
            ai_response = response["message"]["content"]
            logger.info("Initial AI response: %s", ai_response)
        except Exception as e:
            logger.error("Error communicating with AI (final): %s", e)
            ai_response = "Przepraszam, wystąpił błąd podczas komunikacji z AI."

        # 4. Jeśli AI zwraca polecenie typu "!search", wywołaj je
        trimmed = ai_response.strip()
        if trimmed.startswith("!"):
            parts = trimmed.split(maxsplit=1)
            ai_command = parts[0]
            ai_params = parts[1] if len(parts) > 1 else ""
            if ai_command in self.modules:
                logger.info("AI triggered module command: %s, params: %s", ai_command, ai_params)
                try:
                    module_result = await asyncio.to_thread(self.modules[ai_command]["handler"], ai_params)
                    self.conversation_history.append({"role": "assistant", "content": module_result})

                    # CHANGED: usuwamy <think> z module_result
                    to_speak = remove_chain_of_thought(module_result)
                    await self.tts.speak(to_speak)

                except Exception as e:
                    logger.error("Error executing module command triggered by AI: %s", e)
                    error_text = f"Błąd wykonania komendy {ai_command}: {e}"
                    self.conversation_history.append({"role": "assistant", "content": error_text})
                    await self.tts.speak(error_text)

                self.trim_conversation_history()
                return

        # 5. W przeciwnym razie odczytujemy zwykłą odpowiedź
        if ai_response.strip():
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            # CHANGED: usuwamy <think> przed odczytem
            to_speak = remove_chain_of_thought(ai_response)
            await self.tts.speak(to_speak)
        else:
            logger.warning("AI did not generate a response.")

        self.trim_conversation_history()

    def _build_messages_for_screenshot(self, user_prompt: str):
        """
        Buduje listę wiadomości do AI w kontekście screenshotu.
        Możesz dostosować np. dodać minimalną historię, albo większą.
        """
        system_prompt = (
            "Odpowiedz maksymalnie w 2 zdaniach. Możesz nawiązywać do poprzednich wiadomości, "
            "jeśli zawierają kontekst."
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def trim_conversation_history(self):
        """
        Usuwa najstarsze wiadomości, jeśli jest ich za dużo.
        """
        if len(self.conversation_history) > MAX_HISTORY_LENGTH:
            self.conversation_history = self.conversation_history[-MAX_HISTORY_LENGTH:]

    def process_audio(self):
        """
        Główna pętla przetwarzania audio (blokująca, uruchamiana w wątku).
        """
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

            # Wykrycie wake word w partial
            if self.wake_word in partial_text:
                logger.info("Wake word detected in partial result.")
                self.tts.cancel()  # przerwij TTS
                command_text = self.speech_recognizer.listen_command()
                if command_text:
                    logger.info("Detected command: %s", command_text)
                    asyncio.run_coroutine_threadsafe(self.process_query(command_text), self.loop)
                else:
                    logger.warning("No command detected from partial result.")
                recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)
                continue

            # Jeśli mamy pełny wynik do sprawdzenia
            if recognizer.AcceptWaveform(data):
                try:
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").lower()
                except Exception as e:
                    logger.error("Error processing full result: %s", e)
                    text = ""

                if self.wake_word in text:
                    logger.info("Wake word detected in full result.")
                    self.tts.cancel()  # przerwij TTS
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
        """
        Główna metoda asynchroniczna – tworzy stream audio, uruchamia pętlę rozpoznawania mowy
        i czeka w nieskończoność.
        """
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
            ):
                logger.info("Audio stream opened. Waiting for activation...")
                await self.loop.run_in_executor(None, self.process_audio)
        except Exception as e:
            logger.error("Error in audio stream: %s", e)

        logger.info("Audio processing ended. Blocking main loop indefinitely.")
        await asyncio.Future()  # Nie kończ – czekaj w nieskończoność


if __name__ == "__main__":
    from config import VOSK_MODEL_PATH, MIC_DEVICE_ID, WAKE_WORD, STT_SILENCE_THRESHOLD

    logging.basicConfig(
        level=logging.INFO,
        filename="assistant.log",
        filemode="a",
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    assistant = Assistant(
        VOSK_MODEL_PATH,
        MIC_DEVICE_ID,
        WAKE_WORD,
        STT_SILENCE_THRESHOLD
    )
    try:
        asyncio.run(assistant.run_async())
    except KeyboardInterrupt:
        logger.info("Assistant terminated by user.")
    except Exception as e:
        logger.error("Unexpected error: %s", e)
