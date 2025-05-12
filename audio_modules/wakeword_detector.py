import asyncio
import os
import logging
import queue  # Import queue module for Empty exception
import time
import numpy as np
# Model import will be loaded dynamically inside the function to avoid static analysis errors
from .beep_sounds import play_beep

logger = logging.getLogger(__name__)

def run_wakeword_detection(speech_recognizer, wake_word, tts, use_whisper, process_query_callback, loop, sensitivity_threshold, whisper_asr=None):
    """
    Listens for the wake word using Porcupine open wake word engine. Can be interrupted by a special queue message.
    Returns None or exits on error.
    """
    # Prepare model directory before initializing openWakeWord
    model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'openWakeWord'))
    # Initialize openWakeWord engine with local model files
    try:
        # Ensure default preprocessor resources exist in package path
        import openwakeword
        import shutil
        openwakeword.utils.download_models()
        pkg_models = os.path.join(os.path.dirname(openwakeword.__file__), 'resources', 'models')
        os.makedirs(pkg_models, exist_ok=True)
        # Copy local model files (preprocessor and embedding) into package if missing
        for fname in ('melspectrogram.onnx', 'melspectrogram.tflite', 'embedding_model.onnx', 'embedding_model.tflite'):
            src = os.path.join(model_dir, fname)
            dst = os.path.join(pkg_models, fname)
            if os.path.isfile(src) and not os.path.isfile(dst):
                shutil.copy(src, dst)
        # Override preprocessor and embedding model paths
        import openwakeword.utils as ow_utils
        ow_utils.MELSPECTROGRAM_ONNX_PATH = os.path.join(model_dir, 'melspectrogram.onnx')
        ow_utils.MELSPECTROGRAM_TFLITE_PATH = os.path.join(model_dir, 'melspectrogram.tflite')
        # If embedding models provided locally, override their paths if the files exist
        emb_onnx = os.path.join(model_dir, 'embedding_model.onnx')
        if os.path.isfile(emb_onnx):
            try:
                ow_utils.EMBEDDING_MODEL_ONNX_PATH = emb_onnx
            except AttributeError:
                # attribute may not exist in this version
                pass
        emb_tflite = os.path.join(model_dir, 'embedding_model.tflite')
        if os.path.isfile(emb_tflite):
            try:
                ow_utils.EMBEDDING_MODEL_TFLITE_PATH = emb_tflite
            except AttributeError:
                # attribute may not exist in this version
                pass
        from openwakeword.model import Model
    except ImportError:
        raise ImportError("openwakeword library is required for wake word detection. Install via `pip install openwakeword`.")
    # List all .tflite and .onnx model files in the resource directory
    # Collect keyword detection models (exclude preprocessor files)
    keyword_paths = [os.path.join(model_dir, f)
                     for f in os.listdir(model_dir)
                     if (f.endswith('.tflite') or f.endswith('.onnx'))
                        and f.lower() not in ('melspectrogram.onnx', 'melspectrogram.tflite')]
    if not keyword_paths:
        logger.error("No wake word model files found in %s", model_dir)
        return None
    # If TFLite runtime is unavailable, filter to ONNX models only
    try:
        # Check for TFLite runtime availability via importlib to avoid static import errors
        import importlib
        importlib.import_module('tflite_runtime.interpreter')
    except ImportError:
        logger.warning("TFLite runtime not found; using ONNX models only")
        keyword_paths = [p for p in keyword_paths if p.lower().endswith('.onnx')]
        if not keyword_paths:
            logger.error("No ONNX keyword model files found after filtering in %s", model_dir)
            return None
    # Instantiate openWakeWord model
    logger.info("Initializing openWakeWord with models: %s", keyword_paths)
    try:
        wakeword_model = Model(wakeword_models=keyword_paths)
    except Exception as e:
        err = str(e)
        # Handle missing embedding model file: fail fast by propagating exception
        if 'embedding_model.onnx' in err or 'embedding_model.tflite' in err:
            logger.error("Missing embedding model files. Please ensure embedding_model.onnx and/or embedding_model.tflite exist in %s", model_dir)
            raise FileNotFoundError(f"Embedding model not found in {model_dir}")
        # Other initialization failures
        logger.error("openWakeWord Model initialization failed: %s", err)
        logger.error(
            "Ensure you have the required model files (melspectrogram) and a compatible runtime. "
            "On Windows install TensorFlow (`pip install tensorflow`) for TFLite support, or place ONNX models under openWakeWord resources."
        )
        raise
    logger.info("Starting open wake word detection using openWakeWord for '%s'", wake_word)
    while True:
        try:
            data = speech_recognizer.audio_q.get(timeout=0.2)
        except queue.Empty:
            continue
        except Exception as e:
            logger.error("Error getting audio data from queue: %s", e)
            time.sleep(0.1)
            continue
        # Handle manual trigger
        if data == "__MANUAL_TRIGGER__":
            logger.info("Manual trigger signal received.")
            tts.cancel()
            play_beep("keyword", loop=False)
            # Listen or transcribe command
            try:
                if use_whisper and whisper_asr:
                    logger.info("Recording audio for Whisper command (manual trigger)...")
                    audio_cmd = speech_recognizer.record_dynamic_command_audio()
                    if audio_cmd is not None:
                        logger.info("Transcribing command with Whisper (manual trigger)...")
                        logger.debug(f"Audio data length for Whisper (manual trigger): {len(audio_cmd)} bytes")
                        cmd_text = whisper_asr.transcribe(audio_cmd, sample_rate=16000)
                        logger.info(f"Whisper transcription result (manual trigger): '{cmd_text}'")
                    else:
                        logger.warning("No audio recorded for Whisper command (manual trigger).")
                else:
                    logger.info("Listening for command...")
                    cmd_text = speech_recognizer.listen_command()
                if cmd_text:
                    logger.info(f"Command text received (manual trigger): '{cmd_text}'")
                    asyncio.run_coroutine_threadsafe(process_query_callback(cmd_text), loop)
                else:
                    logger.warning("No command text obtained after manual trigger (either not detected or Whisper returned empty).")
            except Exception as cmd_e:
                logger.error(f"Error processing command after manual trigger: {cmd_e}", exc_info=True)
            continue
        # Wake word detection using openWakeWord
        try:
            pcm = np.frombuffer(data, dtype=np.int16)
            # Predict confidence scores for each model
            predictions = wakeword_model.predict(pcm) # Returns a dict e.g. {"model_name": score_float}
            
            action_on_detection = False # Flag to trigger actions if wake word is detected
            
            # Iterate through models in the order they were provided in keyword_paths
            for current_model_idx, model_path_in_keyword_list in enumerate(keyword_paths):
                # Derive the model name key (e.g., "Gaja" from "Gaja.onnx")
                model_name_as_key = os.path.splitext(os.path.basename(model_path_in_keyword_list))[0]
                
                actual_score_value_float = predictions.get(model_name_as_key) # Get the float score
                
                if actual_score_value_float is not None and actual_score_value_float >= sensitivity_threshold:
                    logger.info("Wake word detected by openWakeWord (index %d, model %s, score %.2f, threshold %.2f)",
                                current_model_idx, model_path_in_keyword_list, actual_score_value_float, sensitivity_threshold)
                    action_on_detection = True
                    break # Stop on the first detected model
            
            if action_on_detection:
                tts.cancel()
                play_beep("keyword", loop=False)
                # Listen or transcribe command
                try:
                    if use_whisper and whisper_asr:
                        logger.info("Recording audio for Whisper command...")
                        audio_cmd = speech_recognizer.record_dynamic_command_audio()
                        if audio_cmd is not None:
                            logger.info("Transcribing command with Whisper...")
                            logger.debug(f"Audio data length for Whisper: {len(audio_cmd)} bytes")
                            cmd_text = whisper_asr.transcribe(audio_cmd, sample_rate=16000)
                            logger.info(f"Whisper transcription result: '{cmd_text}'")
                        else:
                            logger.warning("No audio recorded for Whisper command.")
                    else:
                        logger.info("Listening for command...")
                        cmd_text = speech_recognizer.listen_command()
                    if cmd_text:
                        logger.info(f"Command text received: '{cmd_text}'")
                        asyncio.run_coroutine_threadsafe(process_query_callback(cmd_text), loop)
                    else:
                        logger.warning("No command text obtained after wake word (either not detected or Whisper returned empty).")
                except Exception as cmd_e:
                    logger.error(f"Error processing command after wake word: {cmd_e}", exc_info=True)
        except Exception as e:
            logger.error("Error during openWakeWord detection: %s", e, exc_info=True)
            time.sleep(0.1)
            continue
    # No explicit cleanup required for openWakeWord Model
    return None
