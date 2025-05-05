import sounddevice as sd
import numpy as np
import logging, json
from queue import Queue
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    def __init__(self, model_path, mic_device_id, silence_threshold, sample_rate=16000):
        self.model = Model(model_path)
        self.mic_device_id = mic_device_id
        self.silence_threshold = silence_threshold
        self.sample_rate = sample_rate  # adaptive sample rate based on environment
        self.audio_q = Queue()

    def audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning("Audio callback status: %s", status)
        self.audio_q.put(bytes(indata))

    def unload(self):
        """Unloads the Vosk model."""
        if self.model:
            logger.info("Unloading Vosk model...")
            # Vosk model doesn't have an explicit unload, rely on GC
            self.model = None
            logger.info("Vosk model reference removed.")
        else:
            logger.info("Vosk model already unloaded or not loaded.")

    def listen_command(self):
        logger.info("Listening for command using Vosk (dynamic recording)...")
        audio_command = self.record_dynamic_command_audio()
        audio_int16 = (audio_command * 32767).astype(np.int16)
        recognizer = KaldiRecognizer(self.model, self.sample_rate)
        recognizer.AcceptWaveform(audio_int16.tobytes())
        try:
            result = json.loads(recognizer.FinalResult())
            recognized_text = result.get("text", "")
            logger.info("Vosk recognized: %s", recognized_text)
            return recognized_text
        except Exception as e:
            logger.error("Error in Vosk recognition: %s", e)
            return ""

    def record_command_audio(self, duration=5, device=None):
        device = device if device is not None else self.mic_device_id
        logger.info(f"Recording audio for {duration} seconds using device {device} at {self.sample_rate}Hz...")
        audio = sd.rec(int(duration * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype='float32', device=device)
        sd.wait()
        return audio.flatten()

    def record_dynamic_command_audio(self, silence_threshold=0.01, silence_duration=0.5, max_duration=10, min_duration=2):
        logger.info(f"Dynamic command recording at {self.sample_rate}Hz...")
        # Faster loop: smaller chunks for timely detection
        chunk_duration = 0.05  # 50ms chunks
        # use provided silence_duration and min_duration parameters
        chunk_frames = int(self.sample_rate * chunk_duration)
        recorded_audio = []
        silence_time = 0
        total_time = 0
        extended = False

        stream = sd.InputStream(samplerate=self.sample_rate, channels=1, device=self.mic_device_id, dtype='float32')
        stream.start()
        while True:
            data, _ = stream.read(chunk_frames)
            data = np.squeeze(data)
            recorded_audio.append(data)
            total_time += chunk_duration
            rms = np.sqrt(np.mean(data * data))
            # after minimum duration, detect silence
            if total_time >= min_duration:
                if rms < silence_threshold:
                    silence_time += chunk_duration
                else:
                    silence_time = 0
                if silence_time >= silence_duration:
                    logger.info("Silence detected, ending recording.")
                    break
            # if max_duration reached without silence, extend until silence
            if not extended and total_time >= max_duration and silence_time == 0:
                extended = True
                logger.info("Max duration reached but still speaking, extending recording until silence.")
            # Removed absolute cap; recording continues until silence detected
        stream.stop()
        stream.close()
        return np.concatenate(recorded_audio)
