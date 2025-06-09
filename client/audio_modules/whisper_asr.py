"""
Whisper ASR (Automatic Speech Recognition) module for GAJA Assistant Client
Simplified version adapted for client-server architecture.
"""

import asyncio
import io
import logging
import os
import tempfile
import wave
from typing import Optional, Dict, Any
from loguru import logger
import numpy as np

class WhisperASR:
    """Simplified Whisper ASR for client."""
    
    def __init__(self, model_name: str = "base", language: str = "pl"):
        self.model_name = model_name
        self.language = language
        self.model = None
        self.initialized = False
        
        # Check dependencies
        self.whisper_available = self._check_whisper()
        self.torch_available = self._check_torch()
    
    def _check_whisper(self) -> bool:
        """Check if Whisper is available."""
        try:
            import whisper
            return True
        except ImportError:
            try:
                from faster_whisper import WhisperModel
                return True
            except ImportError:
                logger.warning("Neither whisper nor faster-whisper available")
                return False
    
    def _check_torch(self) -> bool:
        """Check if PyTorch is available."""
        try:
            import torch
            return True
        except ImportError:
            logger.warning("PyTorch not available - some features may be limited")
            return False
    
    async def initialize(self) -> bool:
        """Initialize the Whisper model."""
        if self.initialized:
            return True
            
        if not self.whisper_available:
            logger.error("Cannot initialize ASR - Whisper not available")
            return False
        
        try:
            # Try faster-whisper first, then fallback to whisper
            try:
                from faster_whisper import WhisperModel
                logger.info(f"Initializing faster-whisper model: {self.model_name}")
                
                # Determine device
                device = "cuda" if self.torch_available else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
                
                self.model = WhisperModel(
                    self.model_name,
                    device=device,
                    compute_type=compute_type
                )
                self.use_faster_whisper = True
                
            except ImportError:
                import whisper
                logger.info(f"Initializing whisper model: {self.model_name}")
                
                device = "cuda" if self.torch_available else "cpu"
                self.model = whisper.load_model(self.model_name, device=device)
                self.use_faster_whisper = False
            
            self.initialized = True
            logger.success(f"ASR model initialized: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ASR model: {e}")
            return False
    
    async def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """Transcribe audio data to text."""
        if not self.initialized:
            if not await self.initialize():
                return None
        
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # Write WAV file
                with wave.open(temp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(sample_rate)
                    
                    # Convert float32 to int16
                    if audio_data.dtype == np.float32:
                        audio_data = (audio_data * 32767).astype(np.int16)
                    
                    wav_file.writeframes(audio_data.tobytes())
            
            # Transcribe using appropriate method
            if self.use_faster_whisper:
                result = await self._transcribe_faster_whisper(temp_path)
            else:
                result = await self._transcribe_whisper(temp_path)
            
            # Clean up
            os.unlink(temp_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    async def _transcribe_faster_whisper(self, audio_path: str) -> Optional[str]:
        """Transcribe using faster-whisper."""
        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=self.language,
                beam_size=5,
                word_timestamps=False
            )
            
            # Combine all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            
            result = " ".join(text_parts).strip()
            
            logger.debug(f"Transcription completed: {len(result)} characters")
            return result if result else None
            
        except Exception as e:
            logger.error(f"faster-whisper transcription error: {e}")
            return None
    
    async def _transcribe_whisper(self, audio_path: str) -> Optional[str]:
        """Transcribe using standard whisper."""
        try:
            result = self.model.transcribe(
                audio_path,
                language=self.language,
                fp16=False  # Disable fp16 for CPU
            )
            
            text = result.get("text", "").strip()
            
            logger.debug(f"Transcription completed: {len(text)} characters")
            return text if text else None
            
        except Exception as e:
            logger.error(f"whisper transcription error: {e}")
            return None
    
    async def transcribe_file(self, file_path: str) -> Optional[str]:
        """Transcribe audio file."""
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return None
        
        if not self.initialized:
            if not await self.initialize():
                return None
        
        try:
            if self.use_faster_whisper:
                return await self._transcribe_faster_whisper(file_path)
            else:
                return await self._transcribe_whisper(file_path)
                
        except Exception as e:
            logger.error(f"Error transcribing file {file_path}: {e}")
            return None


class AudioRecorder:
    """Simple audio recorder for ASR."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.recording = False
        self.audio_data = []
        
        # Check sounddevice
        self.sounddevice_available = self._check_sounddevice()
    
    def _check_sounddevice(self) -> bool:
        """Check if sounddevice is available."""
        try:
            import sounddevice as sd
            return True
        except ImportError:
            logger.warning("sounddevice not available - audio recording disabled")
            return False
    
    async def record_audio(self, duration: float = 5.0) -> Optional[np.ndarray]:
        """Record audio for specified duration."""
        if not self.sounddevice_available:
            logger.error("Cannot record audio - sounddevice not available")
            return None
        
        try:
            import sounddevice as sd
            
            logger.info(f"Recording audio for {duration} seconds...")
            
            # Record audio
            audio_data = sd.rec(
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32'
            )
            
            sd.wait()  # Wait for recording to complete
            
            logger.info("Audio recording completed")
            return audio_data.flatten()
            
        except Exception as e:
            logger.error(f"Error recording audio: {e}")
            return None


# Factory functions for easy integration
def create_whisper_asr(config: dict) -> WhisperASR:
    """Create and configure Whisper ASR."""
    model_name = config.get('model', 'base')
    language = config.get('language', 'pl')
    return WhisperASR(model_name=model_name, language=language)

def create_audio_recorder(sample_rate: int = 16000) -> AudioRecorder:
    """Create audio recorder."""
    return AudioRecorder(sample_rate=sample_rate)
