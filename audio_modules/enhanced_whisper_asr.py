"""
Enhanced Whisper ASR Module with User Mode Support
Obsługuje różnych dostawców Whisper w zależności od trybu użytkownika
"""

import asyncio
import logging
import os
import time
import tempfile
from typing import Optional, Dict, Any, List
from pathlib import Path

# Import user modes
from user_modes import get_current_mode, get_current_config, UserMode, WhisperProvider

# Optional dependencies based on mode
try:
    import whisper
    import torch
except ImportError:
    whisper = None
    torch = None

try:
    import openai
except ImportError:
    openai = None

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None

from performance_monitor import measure_performance

logger = logging.getLogger(__name__)

class EnhancedWhisperASR:
    """Enhanced Whisper ASR z obsługą różnych trybów użytkownika."""
    
    def __init__(self):
        self._current_mode = None
        self._whisper_providers = {}
        self._local_models = {}  # Cache for local Whisper models
        self._model_performance = {}  # Performance tracking for dynamic model selection
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Inicjalizuje dostępnych dostawców Whisper."""
        
        # Local Whisper Provider (Poor Man Mode)
        if whisper is not None:
            self._whisper_providers[WhisperProvider.LOCAL_WHISPER] = self._local_whisper_transcribe
            logger.info("Local Whisper provider initialized")
        
        # OpenAI Whisper Provider (Paid User Mode)
        if openai is not None:
            self._whisper_providers[WhisperProvider.OPENAI_WHISPER] = self._openai_whisper_transcribe
            logger.info("OpenAI Whisper provider initialized")
        
        # Azure Whisper Provider (Enterprise Mode)
        if speechsdk is not None:
            self._whisper_providers[WhisperProvider.AZURE_WHISPER] = self._azure_whisper_transcribe
            logger.info("Azure Whisper provider initialized")
        
        logger.info(f"Initialized {len(self._whisper_providers)} Whisper providers")
    
    def _get_optimal_model_size(self, config: Dict[str, Any], audio_duration: float = None) -> str:
        """Dynamiczny dobór rozmiaru modelu dla Poor Man Mode."""
        if not config.get('dynamic_model_selection', False):
            return config.get('model_size', 'base')
        
        max_model = config.get('max_model_size', 'small')
        fallback_models = config.get('fallback_models', ['tiny', 'base', 'small'])
        
        # Model hierarchy by size and performance
        model_hierarchy = ['tiny', 'base', 'small', 'medium', 'large']
        max_model_idx = model_hierarchy.index(max_model) if max_model in model_hierarchy else 2
        
        # Dynamic selection based on audio duration
        if audio_duration:
            if audio_duration < 5:  # Short audio - use faster model
                selected = 'tiny'
            elif audio_duration < 15:  # Medium audio - balanced model
                selected = 'base' 
            elif audio_duration < 30:  # Longer audio - better model if allowed
                selected = 'small' if max_model_idx >= 2 else 'base'
            else:  # Very long audio - best allowed model
                selected = max_model
        else:
            # Default to base model
            selected = 'base'
        
        # Ensure selected model is within allowed range
        if selected not in model_hierarchy[:max_model_idx + 1]:
            selected = fallback_models[0] if fallback_models else 'tiny'
        
        # Check performance history for this model
        if selected in self._model_performance:
            perf = self._model_performance[selected]
            # If model consistently performs poorly, try smaller one
            if perf.get('avg_time', 0) > 10 and perf.get('error_rate', 0) > 0.1:
                smaller_idx = max(0, model_hierarchy.index(selected) - 1)
                selected = model_hierarchy[smaller_idx]
        
        logger.debug(f"Selected Whisper model: {selected} (duration: {audio_duration}s)")
        return selected
    
    def _load_local_model(self, model_size: str) -> Optional[Any]:
        """Ładuje lokalny model Whisper z cache."""
        if model_size in self._local_models:
            return self._local_models[model_size]
        
        try:
            logger.info(f"Loading Whisper model: {model_size}")
            start_time = time.time()
            
            # Check if CUDA is available for faster processing
            device = "cuda" if torch and torch.cuda.is_available() else "cpu"
            
            model = whisper.load_model(model_size, device=device)
            self._local_models[model_size] = model
            
            load_time = time.time() - start_time
            logger.info(f"Whisper model {model_size} loaded in {load_time:.2f}s on {device}")
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model {model_size}: {e}")
            return None
    
    def _update_model_performance(self, model_size: str, duration: float, success: bool):
        """Aktualizuje statystyki wydajności modelu."""
        if model_size not in self._model_performance:
            self._model_performance[model_size] = {
                'total_time': 0,
                'total_requests': 0,
                'errors': 0,
                'avg_time': 0,
                'error_rate': 0
            }
        
        perf = self._model_performance[model_size]
        perf['total_time'] += duration
        perf['total_requests'] += 1
        if not success:
            perf['errors'] += 1
        
        perf['avg_time'] = perf['total_time'] / perf['total_requests']
        perf['error_rate'] = perf['errors'] / perf['total_requests']
    
    @measure_performance
    async def transcribe(self, audio_file_path: str) -> str:
        """Główna metoda transkrypcji - wybiera dostawcę na podstawie trybu użytkownika."""
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        # Get current user mode and config
        current_mode = get_current_mode()
        config = get_current_config()
        whisper_provider = config.whisper_provider
        
        # Check if provider is available
        if whisper_provider not in self._whisper_providers:
            logger.error(f"Whisper provider {whisper_provider.value} not available, falling back to local Whisper")
            whisper_provider = WhisperProvider.LOCAL_WHISPER
            
            if whisper_provider not in self._whisper_providers:
                raise Exception("No Whisper providers available")
        
        # Call appropriate provider
        try:
            result = await self._whisper_providers[whisper_provider](audio_file_path, config.whisper_config)
            logger.debug(f"Transcription result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Whisper error with {whisper_provider.value}: {e}")
            # Try fallback to local Whisper if available
            if whisper_provider != WhisperProvider.LOCAL_WHISPER and WhisperProvider.LOCAL_WHISPER in self._whisper_providers:
                logger.info("Falling back to local Whisper")
                try:
                    return await self._local_whisper_transcribe(audio_file_path, config.whisper_config)
                except Exception as fallback_e:
                    logger.error(f"Fallback Whisper also failed: {fallback_e}")
                    raise fallback_e
            else:
                raise e
    
    async def _local_whisper_transcribe(self, audio_file_path: str, config: Dict[str, Any]) -> str:
        """Local Whisper implementation (Poor Man Mode) z dynamicznym doborem rozmiaru."""
        if whisper is None:
            raise Exception("whisper library is not available")
        
        # Get audio duration for dynamic model selection
        try:
            import librosa
            y, sr = librosa.load(audio_file_path, sr=None)
            audio_duration = len(y) / sr
        except ImportError:
            # Fallback: estimate from file size (rough approximation)
            file_size = os.path.getsize(audio_file_path)
            audio_duration = file_size / 32000  # Rough estimate for 16kHz 16-bit audio
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
            audio_duration = None
        
        # Select optimal model size
        model_size = self._get_optimal_model_size(config, audio_duration)
        
        # Load model
        model = self._load_local_model(model_size)
        if model is None:
            # Try fallback models
            fallback_models = config.get('fallback_models', ['tiny', 'base'])
            for fallback in fallback_models:
                model = self._load_local_model(fallback)
                if model is not None:
                    model_size = fallback
                    break
            
            if model is None:
                raise Exception("Could not load any Whisper model")
        
        # Transcribe
        start_time = time.time()
        success = False
        
        try:
            language = config.get('language', 'pl')
            auto_detect = config.get('auto_detect_language', True)
            
            # Transcribe with selected model
            result = await asyncio.to_thread(
                model.transcribe,
                audio_file_path,
                language=language if not auto_detect else None,
                verbose=False
            )
            
            transcription = result.get('text', '').strip()
            success = True
            
            # Log detected language if auto-detection was used
            if auto_detect and 'language' in result:
                detected_lang = result['language']
                logger.debug(f"Detected language: {detected_lang}")
            
            return transcription
            
        except Exception as e:
            logger.error(f"Local Whisper transcription failed: {e}")
            raise e
            
        finally:
            # Update performance metrics
            duration = time.time() - start_time
            self._update_model_performance(model_size, duration, success)
    
    async def _openai_whisper_transcribe(self, audio_file_path: str, config: Dict[str, Any]) -> str:
        """OpenAI Whisper implementation (Paid User Mode)."""
        if openai is None:
            raise Exception("openai library is not available")
        
        model = config.get('model', 'whisper-1')
        language = config.get('language', 'pl')
        response_format = config.get('response_format', 'json')
        temperature = config.get('temperature', 0.0)
        
        try:
            with open(audio_file_path, 'rb') as audio_file:
                result = await asyncio.to_thread(
                    openai.audio.transcriptions.create,
                    model=model,
                    file=audio_file,
                    language=language,
                    response_format=response_format,
                    temperature=temperature
                )
            
            if response_format == 'json':
                return result.text.strip()
            else:
                return str(result).strip()
                
        except Exception as e:
            logger.error(f"OpenAI Whisper transcription failed: {e}")
            raise e
    
    async def _azure_whisper_transcribe(self, audio_file_path: str, config: Dict[str, Any]) -> str:
        """Azure Speech Services implementation (Enterprise Mode)."""
        if speechsdk is None:
            raise Exception("azure-cognitiveservices-speech library is not available")
        
        region = config.get('region', 'eastus')
        language = config.get('language', 'pl-PL')
        profanity_filter = config.get('profanity_filter', True)
        add_punctuation = config.get('add_punctuation', True)
        
        try:
            # Configure Azure Speech SDK
            speech_key = os.getenv("AZURE_SPEECH_KEY")
            if not speech_key:
                raise Exception("AZURE_SPEECH_KEY environment variable not set")
            
            speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=region)
            speech_config.speech_recognition_language = language
            
            if profanity_filter:
                speech_config.set_profanity(speechsdk.ProfanityOption.Masked)
            
            audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            # Perform recognition
            result = await asyncio.to_thread(speech_recognizer.recognize_once_async().get)
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return result.text.strip()
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning("Azure Speech: No speech could be recognized")
                return ""
            else:
                raise Exception(f"Azure Speech recognition failed: {result.reason}")
                
        except Exception as e:
            logger.error(f"Azure Whisper transcription failed: {e}")
            raise e
    
    def get_model_performance_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki wydajności modeli."""
        return self._model_performance.copy()
    
    def clear_model_cache(self):
        """Czyści cache modeli lokalnych."""
        self._local_models.clear()
        logger.info("Local Whisper model cache cleared")

# Create global instance
_enhanced_whisper_instance = EnhancedWhisperASR()

# Module-level functions for compatibility
async def transcribe(audio_file_path: str) -> str:
    """Module-level function for transcription."""
    return await _enhanced_whisper_instance.transcribe(audio_file_path)

def get_performance_stats() -> Dict[str, Any]:
    """Module-level function to get performance stats."""
    return _enhanced_whisper_instance.get_model_performance_stats()

def clear_cache():
    """Module-level function to clear model cache."""
    _enhanced_whisper_instance.clear_model_cache()

# Legacy compatibility
WhisperASR = EnhancedWhisperASR
