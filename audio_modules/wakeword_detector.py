import asyncio
import json
import os
import subprocess
import logging
from vosk import KaldiRecognizer
from .beep_sounds import play_beep

logger = logging.getLogger(__name__)

def run_wakeword_detection(speech_recognizer, wake_word, tts, use_whisper, process_query_callback, loop, whisper_asr=None):
    recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
    while True:
        try:
            data = speech_recognizer.audio_q.get()
        except Exception as e:
            logger.error("Error getting audio data: %s", e)
            continue
        try:
            partial = json.loads(recognizer.PartialResult()).get("partial", "").lower()
        except Exception as e:
            logger.error("Error processing partial result: %s", e)
            partial = ""
        if wake_word in partial:
            logger.info("Wake word detected (partial).")
            tts.cancel()
            play_beep("keyword", loop=False)  # Ensure beep plays only once
            if use_whisper:
                audio_command = speech_recognizer.record_dynamic_command_audio()
                import soundfile as sf
                temp_filename = "temp_command.wav"
                sf.write(temp_filename, audio_command, 16000)
                command_text = whisper_asr.transcribe(temp_filename)
                os.remove(temp_filename)
            else:
                command_text = speech_recognizer.listen_command()
            if command_text:
                logger.info("Command: %s", command_text)
                asyncio.run_coroutine_threadsafe(process_query_callback(command_text), loop)
            else:
                logger.warning("No command detected (partial).")
            recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
            continue
        if recognizer.AcceptWaveform(data):
            try:
                result = json.loads(recognizer.Result()).get("text", "").lower()
            except Exception as e:
                logger.error("Error processing full result: %s", e)
                result = ""
            if wake_word in result:
                logger.info("Wake word detected (full).")
                tts.cancel()
                play_beep("keyword", loop=False)  # Ensure beep plays only once
                if use_whisper:
                    audio_command = speech_recognizer.record_dynamic_command_audio()
                    import soundfile as sf
                    temp_filename = "temp_command.wav"
                    sf.write(temp_filename, audio_command, 16000)
                    command_text = whisper_asr.transcribe(temp_filename)
                    os.remove(temp_filename)
                else:
                    command_text = speech_recognizer.listen_command()
                if command_text:
                    logger.info("Command: %s", command_text)
                    asyncio.run_coroutine_threadsafe(process_query_callback(command_text), loop)
                else:
                    logger.warning("No command detected (full).")
            else:
                logger.debug("Speech detected, wake word not found.")
            recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
