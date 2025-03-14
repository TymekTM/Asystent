# assistant.py

import asyncio
import json
import logging
from tts_module import TTSModule
from search_module import SearchModule
from speech_recognition import SpeechRecognizer
import ollama

logger = logging.getLogger(__name__)

class Assistant:
    def __init__(self, vosk_model_path: str, mic_device_id: int, wake_word: str, stt_silence_threshold: int = 600):
        self.wake_word = wake_word.lower()
        self.conversation_history = []
        self.tts = TTSModule()
        self.search_module = SearchModule()
        self.speech_recognizer = SpeechRecognizer(vosk_model_path, mic_device_id, stt_silence_threshold)
        self.loop = None

    async def process_query(self, text_input: str):
        # Natychmiast przerwij obecny TTS przy wywołaniu nowej komendy
        self.tts.cancel()
        logger.info("Zapytanie użytkownika: %s", text_input)
        if text_input.lower().startswith("wyszukaj"):
            query = text_input[len("wyszukaj"):].strip()
            summary = await self.search_module.search_and_summarize(query)
            self.conversation_history.append({"role": "user", "content": text_input})
            self.conversation_history.append({"role": "assistant", "content": summary})
            await self.tts.speak(summary)
            return

        try:
            response = ollama.chat(
                model="gemma3",
                messages=[
                    {"role": "system", "content": "Przekształć poniższe zapytanie w krótkie, precyzyjne pytanie, bez dodatkowych pytań."},
                    {"role": "user", "content": text_input}
                ]
            )
            refined_query = response["message"]["content"].strip()
        except Exception as e:
            logger.error("Błąd przetwarzania zapytania: %s", e)
            refined_query = text_input
        self.conversation_history.append({"role": "user", "content": refined_query})
        try:
            messages = [{"role": "system", "content": "Odpowiadaj krótko, nie więcej niż 2 zdania."}]
            messages.extend(self.conversation_history)
            response = ollama.chat(model="gemma3", messages=messages)
            ai_response = response["message"]["content"]
        except Exception as e:
            logger.error("Błąd komunikacji z AI: %s", e)
            ai_response = "Przepraszam, wystąpił problem z komunikacją z AI."
        if ai_response.strip():
            self.conversation_history.append({"role": "assistant", "content": ai_response})
            await self.tts.speak(ai_response)
        else:
            logger.warning("AI nie wygenerowało odpowiedzi.")

    def process_audio(self):
        logger.info("Powiedz '%s', aby rozpocząć rozmowę.", self.wake_word.capitalize())
        from vosk import KaldiRecognizer
        recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)
        while True:
            try:
                data = self.speech_recognizer.audio_q.get()
            except Exception as e:
                logger.error("Błąd odbierania audio: %s", e)
                continue
            try:
                partial_result = json.loads(recognizer.PartialResult())
                partial_text = partial_result.get("partial", "").lower()
            except Exception:
                partial_text = ""
            if self.wake_word in partial_text:
                logger.info("Wykryto słowo kluczowe (częściowy wynik)!")
                command_text = self.speech_recognizer.listen_command()
                if command_text:
                    asyncio.run_coroutine_threadsafe(self.process_query(command_text), self.loop)
                else:
                    logger.warning("Nie wykryto komendy.")
                recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)
                continue
            if recognizer.AcceptWaveform(data):
                try:
                    result = json.loads(recognizer.Result())
                    text = result.get("text", "").lower()
                except Exception:
                    text = ""
                if self.wake_word in text:
                    logger.info("Wykryto słowo kluczowe!")
                    command_text = self.speech_recognizer.listen_command()
                    if command_text:
                        asyncio.run_coroutine_threadsafe(self.process_query(command_text), self.loop)
                    else:
                        logger.warning("Nie wykryto komendy.")
                else:
                    logger.debug("Mowa wykryta, ale brak słowa kluczowego.")
                recognizer = KaldiRecognizer(self.speech_recognizer.model, 16000)

    async def run_async(self):
        self.loop = asyncio.get_running_loop()
        self.speech_recognizer.audio_q.queue.clear()
        import sounddevice as sd
        with sd.RawInputStream(
            samplerate=16000,
            blocksize=8000,
            dtype="int16",
            channels=1,
            device=self.speech_recognizer.mic_device_id,
            callback=self.speech_recognizer.audio_callback
        ):
            logger.info("Oczekiwanie na aktywację...")
            await self.loop.run_in_executor(None, self.process_audio)
