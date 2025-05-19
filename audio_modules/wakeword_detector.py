import asyncio
import os
import logging
import queue
import time
import threading # Added for manual_trigger_event
import numpy as np
import sounddevice as sd
from openwakeword.model import Model # Directly import Model
from .beep_sounds import play_beep
import sys # Added for PyInstaller path correction

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Constants for audio recording
SAMPLE_RATE = 16000  # Hz (openWakeWord and Whisper typically use 16kHz)
CHUNK_DURATION_MS = 50  # openWakeWord processes audio in chunks (adjust if oww expects different chunk size)
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000) # Samples per chunk for VAD and command recording
COMMAND_RECORD_TIMEOUT_SECONDS = 7 # Max duration for command recording
# SILENCE_THRESHOLD_MULTIPLIER = 1.5 # This was for Vosk's energy, not directly usable.
MIN_COMMAND_AUDIO_CHUNKS = 40 # Minimum audio chunks (2000ms) to ensure more time for command capture before silence detection
VAD_SILENCE_AMPLITUDE_THRESHOLD = 0.01 # Updated to legacy threshold for VAD (float32 audio).
# stt_silence_threshold (from config, in ms) is now used as duration of silence for VAD.

def record_command_audio(mic_device_id: int, vad_silence_duration_ms: int, stop_event: threading.Event) -> np.ndarray | None:
    """
    Records audio from the microphone until silence is detected or timeout.
    Uses a simple VAD based on amplitude.
    """
    logger.info(f"Recording command audio from device ID: {mic_device_id}...")
    audio_buffer = []
    
    # Calculate how many consecutive silent chunks constitute "silence" for VAD
    vad_silence_chunks_limit = max(1, vad_silence_duration_ms // CHUNK_DURATION_MS)
    silent_chunks_count = 0
    
    # Max command duration in chunks
    max_recording_chunks = COMMAND_RECORD_TIMEOUT_SECONDS * (1000 // CHUNK_DURATION_MS)

    try:
        # Using float32 for Whisper, ensure openWakeWord also handles it or convert if necessary.
        # openWakeWord's Model.predict() can take float32.
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                            device=mic_device_id, blocksize=CHUNK_SAMPLES) as stream:
            logger.info("Listening for command...")
            for _ in range(0, int(SAMPLE_RATE / CHUNK_SAMPLES * COMMAND_RECORD_TIMEOUT_SECONDS)): # Max recording duration
                if stop_event.is_set():
                    logger.debug("Stop event received during command recording.")
                    break
                audio_chunk, overflowed = stream.read(CHUNK_SAMPLES)
                if overflowed:
                    logger.warning("Input overflowed during command recording!")
                audio_buffer.append(audio_chunk)

                # Simple VAD: check RMS of the last few chunks
                if len(audio_buffer) > vad_silence_chunks_limit:
                    # Consider last 'vad_silence_chunks_limit' chunks for silence detection
                    current_segment = np.concatenate(audio_buffer[-vad_silence_chunks_limit:])
                    rms = np.sqrt(np.mean(current_segment**2))
                    # logger.debug(f"VAD RMS: {rms:.4f}") # Verbose
                    if rms < VAD_SILENCE_AMPLITUDE_THRESHOLD:
                        silent_chunks_count += 1
                    else:
                        silent_chunks_count = 0 # Reset on sound

                    if silent_chunks_count >= vad_silence_chunks_limit and len(audio_buffer) >= MIN_COMMAND_AUDIO_CHUNKS :
                        logger.info(f"Silence detected after {len(audio_buffer) * CHUNK_DURATION_MS / 1000:.2f}s of audio.")
                        break
                if len(audio_buffer) >= max_recording_chunks:
                    logger.info("Command recording reached maximum duration.")
                    break
    except sd.PortAudioError as pae:
        logger.error(f"PortAudio error during command recording: {pae}")
        if "Invalid input device" in str(pae):
            logger.error(f"Invalid microphone device ID: {mic_device_id}. Please check your configuration.")
        play_beep("error", loop=False) # Play error beep
        return None
    except Exception as e:
        logger.error(f"Error during command recording: {e}", exc_info=True)
        play_beep("error", loop=False) # Play error beep
        return None
    
    if not audio_buffer or len(audio_buffer) < MIN_COMMAND_AUDIO_CHUNKS / 2 : # Check if enough audio was captured (e.g. more than 1 second)
        logger.info("No valid command audio recorded (too short or empty).")
        # play_beep("timeout", loop=False) # Consider if a timeout beep is desired here
        return None

    recorded_audio = np.concatenate(audio_buffer, axis=0)
    logger.info(f"Command audio recorded: {len(recorded_audio)/SAMPLE_RATE:.2f} seconds.")
    # Log audio characteristics
    logger.debug(f"Command audio stats: Max amp={np.max(np.abs(recorded_audio)):.4f}, Mean amp={np.mean(np.abs(recorded_audio)):.4f}, dtype={recorded_audio.dtype}")
    return recorded_audio


def run_wakeword_detection(
    mic_device_id: int | None,
    stt_silence_threshold_ms: int, # Used for VAD in command recording
    wake_word_config_name: str, # Name of wake word from config (for logging)
    tts_module, 
    use_whisper_stt: bool, # Should always be True
    process_query_callback_async, 
    async_event_loop: asyncio.AbstractEventLoop,
    oww_sensitivity_threshold: float,
    whisper_asr_instance, 
    manual_listen_trigger_event: threading.Event,
    stop_detector_event: threading.Event
):
    """
    Listens for wake word using openWakeWord and handles command recording/transcription.
    """
    if mic_device_id is None:
        try:
            default_devices = sd.query_devices()
            default_input_device_index = None
            # Try to find the host API's default input device first
            for i, device_info in enumerate(default_devices):
                if device_info['max_input_channels'] > 0:
                    try:
                        host_api_info = sd.query_hostapis()[device_info['hostapi']]
                        if 'default_input_device_name' in host_api_info and device_info['name'] == host_api_info['default_input_device_name']:
                            default_input_device_index = i
                            logger.info(f"Found host API default input device: ID {i} ({device_info['name']})")
                            break
                    except KeyError:
                        # 'default_input_device_name' might not exist, or other keys might be missing
                        pass # Continue to next heuristic
            
            if default_input_device_index is None: # Fallback to sounddevice's default if host API default not found or error
                try:
                    default_sd_device = sd.default.device
                    if isinstance(default_sd_device, (list, tuple)) and len(default_sd_device) > 0:
                        # default_sd_device can be [input_idx, output_idx] or just input_idx
                        potential_default_idx = default_sd_device[0] if isinstance(default_sd_device, (list, tuple)) else default_sd_device
                        if default_devices[potential_default_idx]['max_input_channels'] > 0:
                            default_input_device_index = potential_default_idx
                            logger.info(f"Using sounddevice default input device: ID {default_input_device_index} ({default_devices[default_input_device_index]['name']})")
                except Exception as e_sd_default:
                    logger.warning(f"Could not determine sounddevice default input: {e_sd_default}. Will try first available.")

            if default_input_device_index is None: # Fallback to first available input device
                 for i, device in enumerate(default_devices):
                     if device['max_input_channels'] > 0:
                         default_input_device_index = i
                         logger.info(f"Using first available input device: ID {i} ({device['name']})")
                         break
            
            if default_input_device_index is not None:
                mic_device_id = default_input_device_index
                logger.info(f"No microphone device ID specified, using determined default input device: ID {mic_device_id} ({sd.query_devices(mic_device_id)['name']})")
            else:
                logger.error("Could not find any input audio device. Microphone device ID is required.")
                play_beep("error", loop=False)
                return
        except Exception as e:
            logger.error(f"Could not get default input device: {e}. Microphone device ID is required.", exc_info=True)
            play_beep("error", loop=False)
            return
    
    logger.info(f"Wake word detector will use microphone ID: {mic_device_id} ({sd.query_devices(mic_device_id)['name']})")

    # --- openWakeWord Model Initialization ---
    # Construct path to 'resources/openWakeWord'
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle
        # Assume 'resources' directory is at the same level as the executable
        base_dir = os.path.dirname(sys.executable) # Corrected: resources are next to the EXE
    else:
        # Running in a normal Python environment
        # Path relative to this script (audio_modules/wakeword_detector.py) -> up to Asystent/ then resources/
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Resolves to Asystent/
    model_dir = os.path.join(base_dir, 'resources', 'openWakeWord')
    
    if not os.path.isdir(model_dir):
        logger.error(f"openWakeWord model directory not found: {model_dir}")
        return

    try:
        # openwakeword.utils.download_models() # Avoid automatic downloads in production/controlled environments. Ensure models are pre-deployed.
        
        # List custom .onnx or .tflite models for the wake words themselves.
        # Exclude common preprocessor/embedding model names.
        keyword_model_files = [
            os.path.join(model_dir, f)
            for f in os.listdir(model_dir)
            if (f.endswith('.onnx') or f.endswith('.tflite')) and \
               f.lower() not in ('melspectrogram.onnx', 'melspectrogram.tflite', 
                                  'embedding_model.onnx', 'embedding_model.tflite')
        ]

        if not keyword_model_files:
            logger.error(f"No wake word model files (.onnx, .tflite) found in {model_dir} (excluding common preprocessor/embedding files).")
            return
        
        logger.info(f"Initializing openWakeWord with custom models from {model_dir}: {keyword_model_files}")
        
        # Specify paths for preprocessor and embedding models if they are in model_dir
        # This tells oww to use these specific files.
        oww_constructor_args = {'wakeword_models': keyword_model_files}

        # Consider inference_framework based on available files or let oww decide
        # If only .onnx files are present for keywords, can force 'onnx'
        # oww_constructor_args['inference_framework'] = 'onnx' # Example
        
        wakeword_model_instance = Model(**oww_constructor_args)

    except ImportError:
        logger.error("openwakeword library is required. Install via `pip install openwakeword`.")
        return
    except Exception as e:
        logger.error(f"Error initializing custom openWakeWord Model: {e}", exc_info=True)
        logger.warning("Falling back to default openWakeWord Model configuration.")
        try:
            # Try initializing default Model without custom args
            wakeword_model_instance = Model()
        except Exception as e2:
            logger.error(f"Failed to initialize default openWakeWord Model: {e2}", exc_info=True)
            return

    logger.info(f"Starting wake word detection for '{wake_word_config_name}' using openWakeWord.")
    logger.info("Asystent jest załadowany i nasłuchuje.") # <--- DODANO KOMUNIKAT
    
    # Queue for audio data from sounddevice callback to this thread
    audio_data_queue = queue.Queue()

    def sd_callback(indata, frames, time_info, status_flags):
        if status_flags:
            logger.warning(f"sounddevice InputStream status: {status_flags}")
        audio_data_queue.put(indata.copy()) # Put a copy

    # openWakeWord expects audio in chunks. CHUNK_SAMPLES should be what oww processes per call.
    # Common oww chunk size is 1280 samples for 80ms at 16kHz.
    # Let's use a chunk size that oww is happy with for its predict() method.
    # The CHUNK_SAMPLES defined earlier (for 50ms) might need to be adjusted if oww has strict input size.
    # However, oww's Model.predict() can typically handle varying chunk sizes by managing an internal buffer.
    # For simplicity, we'll feed it CHUNK_SAMPLES (50ms = 800 samples at 16kHz).
    
    try:
        audio_stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            device=mic_device_id,
            channels=1,
            dtype='int16', # openWakeWord examples often use int16 PCM
            blocksize=CHUNK_SAMPLES, 
            callback=sd_callback
        )
        with audio_stream:
            logger.info(f"Audio stream started on device ID {mic_device_id} for wake word detection.")
            while not stop_detector_event.is_set():
                try:
                    if manual_listen_trigger_event.is_set():
                        logger.info("Manual listen trigger activated.")
                        # Only play 'listening_start' if not just finishing listening
                        play_beep("listening_start", loop=False)  # Beep for manual/AI-triggered listen
                        if tts_module:
                            tts_module.cancel()
                        command_audio_data_np = record_command_audio(mic_device_id, stt_silence_threshold_ms, stop_detector_event)
                        manual_listen_trigger_event.clear()

                        if command_audio_data_np is not None and command_audio_data_np.size > 0:
                            if use_whisper_stt and whisper_asr_instance:
                                logger.info("Transcribing command with Whisper (manual trigger)...")
                                # Ensure audio is 1D for Whisper
                                audio_to_transcribe = command_audio_data_np.flatten()
                                logger.debug(f"Audio to Whisper (manual): Max amp={np.max(np.abs(audio_to_transcribe)):.4f}, Mean amp={np.mean(np.abs(audio_to_transcribe)):.4f}, dtype={audio_to_transcribe.dtype}, shape={audio_to_transcribe.shape}")
                                transcribed_text = whisper_asr_instance.transcribe(audio_to_transcribe, sample_rate=SAMPLE_RATE)
                                logger.info(f"Whisper transcription (manual): '{transcribed_text}'")
                                if transcribed_text:
                                    asyncio.run_coroutine_threadsafe(process_query_callback_async(transcribed_text), async_event_loop)
                                else:
                                    logger.warning("Whisper returned empty transcription (manual).")
                                    play_beep("error", loop=False)
                            else:
                                logger.error("Whisper STT not configured or ASR instance missing for manual trigger.")
                        else:
                            logger.warning("No audio recorded for manual trigger command.")
                        wakeword_model_instance.reset() # Reset oww state after manual trigger processing
                        continue

                    try:
                        audio_chunk_int16 = audio_data_queue.get(timeout=0.1) 
                    except queue.Empty:
                        if stop_detector_event.is_set(): break
                        continue

                    # oww Model.predict() takes a NumPy array of audio samples (int16 or float32).
                    # Debug: print shape and type
                    # log.debug(f"Audio chunk type: {type(audio_chunk_int16)}, shape: {audio_chunk_int16.shape}, dtype: {audio_chunk_int16.dtype}")
                    prediction_scores = wakeword_model_instance.predict(audio_chunk_int16.flatten())
                    # log.debug(f"Prediction scores: {prediction_scores}")

                    for model_name_key, score_value in prediction_scores.items():
                        if score_value >= oww_sensitivity_threshold:
                            logger.info(f"Wake word '{model_name_key}' detected with score: {score_value:.2f} (threshold: {oww_sensitivity_threshold:.2f})")
                            play_beep("listening_start", loop=False) # Added beep on wake word
                            if tts_module:
                                tts_module.cancel()
                            command_audio_data_np = record_command_audio(mic_device_id, stt_silence_threshold_ms, stop_detector_event)
                            if command_audio_data_np is not None and command_audio_data_np.size > 0:
                                if use_whisper_stt and whisper_asr_instance:
                                    logger.info("Transcribing command with Whisper after wake word...")
                                    # Log audio characteristics before sending to Whisper
                                    # Ensure audio is 1D for Whisper
                                    audio_to_transcribe = command_audio_data_np.flatten()
                                    logger.debug(f"Audio to Whisper: Max amp={np.max(np.abs(audio_to_transcribe)):.4f}, Mean amp={np.mean(np.abs(audio_to_transcribe)):.4f}, dtype={audio_to_transcribe.dtype}, shape={audio_to_transcribe.shape}")
                                    transcribed_text = whisper_asr_instance.transcribe(audio_to_transcribe, sample_rate=SAMPLE_RATE)
                                    logger.info(f"Whisper transcription: '{transcribed_text}'")
                                    if transcribed_text:
                                        asyncio.run_coroutine_threadsafe(process_query_callback_async(transcribed_text), async_event_loop)
                                    else:
                                        logger.warning("Whisper returned empty transcription after wake word.")
                                        play_beep("error", loop=False)
                                else:
                                    logger.error("Whisper STT not configured or ASR instance missing.")
                            else:
                                logger.warning("No audio recorded for command after wake word.")
                            

                            wakeword_model_instance.reset() 
                            break # Corrected from 'continue' to break from the inner for-loop after handling a wake word

                except Exception as e:
                    logger.error(f"Error in wake word detection loop: {e}", exc_info=True)
                    if stop_detector_event.is_set(): break
                    time.sleep(0.1) 
        
    except Exception as e:
        logger.error(f"Fatal error in run_wakeword_detection setup or stream: {e}", exc_info=True)
    finally:
        logger.info("Wake word detection thread finishing.")
        if 'audio_stream' in locals() and audio_stream and not audio_stream.closed:
            try:
                audio_stream.stop()
                audio_stream.close()
                logger.info("Audio stream closed.")
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}", exc_info=True)
    return None
