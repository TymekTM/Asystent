import asyncio
import json
import os
import subprocess
import logging
import queue # Import queue module for Empty exception
from vosk import KaldiRecognizer
from .beep_sounds import play_beep

logger = logging.getLogger(__name__)

def run_wakeword_detection(speech_recognizer, wake_word, tts, use_whisper, process_query_callback, loop, whisper_asr=None):
    """
    Listens for the wake word using Vosk. Can be interrupted by a special queue message.
    Returns "MANUAL_TRIGGER_REQUESTED" if interrupted, None otherwise or on error.
    """
    recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
    logger.info(f"Starting wake word detection for '{wake_word}'...")
    while True:
        try:
            data = speech_recognizer.audio_q.get(timeout=0.2) # Timeout in seconds
            if data == "__MANUAL_TRIGGER__":
                logger.info("Manual trigger signal received in wake word detector.")
                tts.cancel()
                play_beep("keyword", loop=False)
                recognizer.FinalResult()
                command_text = None
                try:
                    if use_whisper and whisper_asr:
                        logger.info("Recording audio for Whisper command (manual trigger)...")
                        audio_command = speech_recognizer.record_dynamic_command_audio()
                        if audio_command is not None:
                            logger.info("Transcribing command with Whisper (manual trigger)...")
                            command_text = whisper_asr.transcribe(audio_command, sample_rate=16000)
                        else:
                            logger.warning("Failed to record audio for Whisper command (manual trigger).")
                    else:
                        logger.info("Listening for command with Vosk (manual trigger)...")
                        command_text = speech_recognizer.listen_command()
                    if command_text:
                        logger.info("Command (manual trigger): %s", command_text)
                        asyncio.run_coroutine_threadsafe(process_query_callback(command_text), loop)
                    else:
                        logger.warning("No command detected after manual trigger.")
                except Exception as cmd_e:
                    logger.error(f"Error during command listening/processing after manual trigger: {cmd_e}", exc_info=True)
                recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
                continue
        except queue.Empty:
            continue
        except Exception as e:
            logger.error("Error getting audio data from queue: %s", e)
            asyncio.sleep(0.1)
            continue

        # Wake word logic
        try:
            partial = json.loads(recognizer.PartialResult()).get("partial", "").lower()
            if wake_word in partial:
                logger.info("Wake word detected (partial).")
                tts.cancel()
                play_beep("keyword", loop=False)
                recognizer.FinalResult()
                command_text = None
                try:
                    if use_whisper and whisper_asr:
                        logger.info("Recording audio for Whisper command...")
                        audio_command = speech_recognizer.record_dynamic_command_audio()
                        if audio_command is not None:
                            logger.info("Transcribing command with Whisper...")
                            command_text = whisper_asr.transcribe(audio_command, sample_rate=16000)
                        else:
                            logger.warning("Failed to record audio for Whisper command.")
                    else:
                        logger.info("Listening for command with Vosk...")
                        command_text = speech_recognizer.listen_command()
                    if command_text:
                        logger.info("Command: %s", command_text)
                        asyncio.run_coroutine_threadsafe(process_query_callback(command_text), loop)
                    else:
                        logger.warning("No command detected after wake word (partial).")
                except Exception as cmd_e:
                    logger.error(f"Error during command listening/processing after partial detection: {cmd_e}", exc_info=True)
                recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
                continue
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result()).get("text", "").lower()
                if wake_word in result:
                    logger.info("Wake word detected (full).")
                    tts.cancel()
                    play_beep("keyword", loop=False)
                    command_text = None
                    try:
                        if use_whisper and whisper_asr:
                            logger.info("Recording audio for Whisper command...")
                            audio_command = speech_recognizer.record_dynamic_command_audio()
                            if audio_command is not None:
                                logger.info("Transcribing command with Whisper...")
                                command_text = whisper_asr.transcribe(audio_command, sample_rate=16000)
                            else:
                                logger.warning("Failed to record audio for Whisper command.")
                        else:
                            logger.info("Listening for command with Vosk...")
                            command_text = speech_recognizer.listen_command()
                        if command_text:
                            logger.info("Command: %s", command_text)
                            asyncio.run_coroutine_threadsafe(process_query_callback(command_text), loop)
                        else:
                            logger.warning("No command detected after wake word (full).")
                    except Exception as cmd_e:
                        logger.error(f"Error during command listening/processing after full detection: {cmd_e}", exc_info=True)
                    recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
                    continue
        except json.JSONDecodeError:
            recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
        except Exception as e:
            logger.error("Error during wake word recognition: %s", e, exc_info=True)
            recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
            asyncio.sleep(0.1)

    logger.warning("Wake word detection loop exited unexpectedly.")
    return None
