"""
Wakeword detector for GAJA Assistant Client
Simplified version adapted for client-server architecture.
"""

import asyncio
import logging
import threading
import time
import queue
import numpy as np
from typing import Optional, Callable
from loguru import logger

class WakewordDetector:
    """Simplified wakeword detector for client."""
    
    def __init__(self, sensitivity: float = 0.6, callback: Optional[Callable] = None):
        self.sensitivity = sensitivity
        self.callback = callback
        self.running = False
        self.audio_queue = queue.Queue()
        self.thread = None
        
        # Check for dependencies
        self.sounddevice_available = self._check_sounddevice()
        self.openwakeword_available = self._check_openwakeword()
        
    def _check_sounddevice(self) -> bool:
        """Check if sounddevice is available."""
        try:
            import sounddevice as sd
            return True
        except ImportError:
            logger.warning("sounddevice not available - wakeword detection disabled")
            return False
    
    def _check_openwakeword(self) -> bool:
        """Check if openwakeword is available."""
        try:
            from openwakeword import Model
            return True
        except ImportError:
            logger.warning("openwakeword not available - using simple detection")
            return False
    
    def start(self):
        """Start wakeword detection."""
        if not self.sounddevice_available:
            logger.error("Cannot start wakeword detection - sounddevice not available")
            return False
            
        if self.running:
            logger.warning("Wakeword detection already running")
            return True
            
        self.running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        logger.info("Wakeword detection started")
        return True
    
    def stop(self):
        """Stop wakeword detection."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        logger.info("Wakeword detection stopped")
    
    def _detection_loop(self):
        """Main detection loop."""
        if self.openwakeword_available:
            self._advanced_detection()
        else:
            self._simple_detection()
    
    def _advanced_detection(self):
        """Advanced detection using openwakeword."""
        try:
            import sounddevice as sd
            from openwakeword import Model
            
            # Initialize model
            model = Model(wakeword_models=["hey_jarvis"])
            
            SAMPLE_RATE = 16000
            CHUNK_SIZE = 1280  # 80ms chunks
            
            logger.info("Starting advanced wakeword detection")
            
            def audio_callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Audio input status: {status}")
                
                # Convert to proper format
                audio_data = (indata[:, 0] * 32767).astype(np.int16)
                self.audio_queue.put(audio_data)
            
            # Start audio stream
            with sd.InputStream(callback=audio_callback, 
                              channels=1, 
                              samplerate=SAMPLE_RATE,
                              blocksize=CHUNK_SIZE):
                
                while self.running:
                    try:
                        # Get audio data
                        audio_data = self.audio_queue.get(timeout=0.1)
                        
                        # Process with model
                        prediction = model.predict(audio_data)
                        
                        # Check for wakeword
                        for wakeword in model.prediction_buffer.keys():
                            if prediction[wakeword] >= self.sensitivity:
                                logger.info(f"Wakeword detected: {wakeword}")
                                if self.callback:
                                    asyncio.create_task(self.callback())
                                    
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"Error in wakeword detection: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to start advanced wakeword detection: {e}")
            self._simple_detection()
    
    def _simple_detection(self):
        """Simple detection based on volume threshold."""
        try:
            import sounddevice as sd
            
            SAMPLE_RATE = 16000
            CHUNK_SIZE = 1024
            VOLUME_THRESHOLD = 0.02  # Adjust based on environment
            
            logger.info("Starting simple wakeword detection (volume-based)")
            
            def audio_callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Audio input status: {status}")
                
                # Calculate volume (RMS)
                volume = np.sqrt(np.mean(indata**2))
                
                if volume > VOLUME_THRESHOLD:
                    logger.debug(f"Audio detected - volume: {volume:.4f}")
                    # Simple trigger - could be improved with pattern recognition
                    if self.callback:
                        asyncio.create_task(self.callback())
            
            # Start audio stream
            with sd.InputStream(callback=audio_callback,
                              channels=1,
                              samplerate=SAMPLE_RATE,
                              blocksize=CHUNK_SIZE):
                
                while self.running:
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Failed to start simple wakeword detection: {e}")


# Factory function for easy integration
def create_wakeword_detector(config: dict, callback: Optional[Callable] = None) -> WakewordDetector:
    """Create and configure wakeword detector."""
    sensitivity = config.get('sensitivity', 0.6)
    return WakewordDetector(sensitivity=sensitivity, callback=callback)
