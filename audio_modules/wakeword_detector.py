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
            # Get data from queue with a timeout to allow interruption check
            data = speech_recognizer.audio_q.get(timeout=0.2) # Timeout in seconds

            # Check for the manual trigger signal
            if data == "__MANUAL_TRIGGER__":
                logger.info("Manual trigger signal received in wake word detector.")
                # Zamiast tylko return, uruchom pełną ścieżkę: dźwięk + STT
                tts.cancel()
                play_beep("keyword", loop=False)
                recognizer.FinalResult()
                command_text = None
                try:
                    if use_whisper and whisper_asr:
                        logger.info("Recording audio for Whisper command (manual trigger)...")
                        audio_command = speech_recognizer.record_dynamic_command_audio()
                        if audio_command is not None:
                            import soundfile as sf
                            import io
                            buffer = io.BytesIO()
                            sf.write(buffer, audio_command, 16000, format='WAV')
                            buffer.seek(0)
                            logger.info("Transcribing command with Whisper (manual trigger)...")
                            command_text = whisper_asr.transcribe(buffer)
                            buffer.close()
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
            # Timeout occurred, no data received, just continue the loop
            continue
        except Exception as e:
            logger.error("Error getting audio data from queue: %s", e)
            # Optional: Add a small delay or break if errors persist
            asyncio.sleep(0.1) # Use asyncio.sleep if this function becomes async
            continue # Continue listening

        # --- Existing Wake Word Logic ---
        try:
            # Process partial results for faster detection
            partial = json.loads(recognizer.PartialResult()).get("partial", "").lower()
            if wake_word in partial:
                logger.info("Wake word detected (partial).")
                tts.cancel()
                play_beep("keyword", loop=False)
                # Clear the recognizer state before listening for command
                recognizer.FinalResult()
                # --- Command Listening (moved from original code block) ---
                command_text = None
                try:
                    if use_whisper and whisper_asr:
                        logger.info("Recording audio for Whisper command...")
                        audio_command = speech_recognizer.record_dynamic_command_audio()
                        if audio_command is not None:
                            import soundfile as sf
                            import io
                            buffer = io.BytesIO()
                            sf.write(buffer, audio_command, 16000, format='WAV')
                            buffer.seek(0)
                            logger.info("Transcribing command with Whisper...")
                            command_text = whisper_asr.transcribe(buffer)
                            buffer.close()
                        else:
                             logger.warning("Failed to record audio for Whisper command.")
                    else: # Use Vosk
                        logger.info("Listening for command with Vosk...")
                        # Corrected method name based on traceback
                        command_text = speech_recognizer.listen_command() # Use correct method

                    if command_text:
                        logger.info("Command: %s", command_text)
                        # Ensure the callback is awaited correctly if it's async
                        # Assuming process_query_callback is async
                        asyncio.run_coroutine_threadsafe(process_query_callback(command_text), loop)
                    else:
                        logger.warning("No command detected after wake word (partial).")
                except Exception as cmd_e:
                     logger.error(f"Error during command listening/processing after partial detection: {cmd_e}", exc_info=True)
                # --- End Command Listening ---
                # Reset recognizer for next wake word detection cycle
                recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
                continue # Go back to start of loop

            # Process final results if wake word wasn't in partial
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result()).get("text", "").lower()
                if wake_word in result:
                    logger.info("Wake word detected (full).")
                    tts.cancel()
                    play_beep("keyword", loop=False)
                    # --- Command Listening (moved from original code block) ---
                    command_text = None
                    try:
                        if use_whisper and whisper_asr:
                            logger.info("Recording audio for Whisper command...")
                            audio_command = speech_recognizer.record_dynamic_command_audio()
                            if audio_command is not None:
                                import soundfile as sf
                                import io
                                buffer = io.BytesIO()
                                sf.write(buffer, audio_command, 16000, format='WAV')
                                buffer.seek(0)
                                logger.info("Transcribing command with Whisper...")
                                command_text = whisper_asr.transcribe(buffer)
                                buffer.close()
                            else:
                                logger.warning("Failed to record audio for Whisper command.")
                        else: # Use Vosk
                            logger.info("Listening for command with Vosk...")
                            # Corrected method name based on traceback
                            command_text = speech_recognizer.listen_command() # Use correct method

                        if command_text:
                            logger.info("Command: %s", command_text)
                            # Ensure the callback is awaited correctly if it's async
                            # Assuming process_query_callback is async
                            asyncio.run_coroutine_threadsafe(process_query_callback(command_text), loop)
                        else:
                            logger.warning("No command detected after wake word (full).")
                    except Exception as cmd_e:
                        logger.error(f"Error during command listening/processing after full detection: {cmd_e}", exc_info=True)
                    # --- End Command Listening ---
                    # Reset recognizer for next wake word detection cycle
                    recognizer = KaldiRecognizer(speech_recognizer.model, 16000)
                    continue # Go back to start of loop
                # else: # Optional: Log if speech detected but not wake word
                #     if result: logger.debug(f"Speech detected, wake word not found: '{result}'")

        except json.JSONDecodeError:
            logger.debug("Vosk returned non-JSON result (likely silence or empty).")
            # Reset recognizer state if needed, or just continue
            recognizer = KaldiRecognizer(speech_recognizer.model, 16000) # Reset on decode error
        except Exception as e:
            logger.error("Error during wake word recognition: %s", e, exc_info=True)
            # Consider resetting recognizer or adding delay
            recognizer = KaldiRecognizer(speech_recognizer.model, 16000) # Reset on general error
            asyncio.sleep(0.1) # Small delay after error

    # This part should ideally not be reached if the loop is infinite,
    # but added for completeness in case of future changes.
    logger.warning("Wake word detection loop exited unexpectedly.")
    return None
