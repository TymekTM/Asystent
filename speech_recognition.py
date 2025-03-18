import sounddevice as sd
import numpy as np
import logging
import json
from queue import Queue
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    def __init__(self, model_path, mic_device_id, silence_threshold):
        self.model = self.load_model(model_path)
        self.mic_device_id = mic_device_id
        self.silence_threshold = silence_threshold
        self.audio_q = Queue()

    def load_model(self, model_path):
        return Model(model_path)

    def audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning("Audio callback status: %s", status)
        self.audio_q.put(bytes(indata))

    def listen_command(self, sample_rate=16000):
        """
        Nagrywa komendę dynamicznie i rozpoznaje ją przy użyciu Vosk.
        Przed rozpoznaniem konwertujemy dane z float32 do int16,
        a następnie po przesłaniu audio wywołujemy FinalResult() by uzyskać finalny wynik.
        """
        logger.info("Listening for command using Vosk method (dynamic recording)...")
        audio_command = self.record_dynamic_command_audio(sample_rate=sample_rate)
        # Konwersja z float32 (zakres -1.0 do 1.0) do int16 (zakres -32768 do 32767)
        audio_int16 = (audio_command * 32767).astype(np.int16)
        recognizer = KaldiRecognizer(self.model, sample_rate)
        recognizer.AcceptWaveform(audio_int16.tobytes())
        result = recognizer.FinalResult()
        try:
            res_json = json.loads(result)
            recognized_text = res_json.get("text", "")
            logger.info("Vosk recognized: %s", recognized_text)
            return recognized_text
        except Exception as e:
            logger.error("Error in Vosk recognition: %s", e)
            return ""

    def record_command_audio(self, duration=5, sample_rate=16000, device=None):
        if device is None:
            device = self.mic_device_id
        logger.info(f"Recording command audio for {duration} seconds using device {device}...")
        audio = sd.rec(int(duration * sample_rate),
                       samplerate=sample_rate,
                       channels=1,
                       dtype='float32',
                       device=device)
        sd.wait()
        return audio.flatten()

    def record_dynamic_command_audio(self, sample_rate=16000, silence_threshold=0.01, silence_duration=0.5, max_duration=10, min_duration=2):
        """
        Nagrywa komendę dynamicznie – kończy nagrywanie, gdy przez określony czas poziom sygnału
        spadnie poniżej zadanej wartości, ale gwarantuje nagranie przynajmniej min_duration sekund.
        Używa małych fragmentów (chunków) do analizy.
        """
        logger.info("Dynamiczne nagrywanie komendy...")
        chunk_duration = 0.1  # sekundy
        chunk_frames = int(sample_rate * chunk_duration)
        recorded_audio = []
        silence_time = 0
        total_time = 0

        stream = sd.InputStream(samplerate=sample_rate, channels=1, device=self.mic_device_id, dtype='float32')
        stream.start()

        while total_time < max_duration:
            data, _ = stream.read(chunk_frames)
            data = np.squeeze(data)
            recorded_audio.append(data)
            total_time += chunk_duration

            # Oblicz RMS dla chunku
            rms = np.sqrt(np.mean(np.square(data.astype(np.float32))))
            if total_time >= min_duration:
                if rms < silence_threshold:
                    silence_time += chunk_duration
                else:
                    silence_time = 0

                if silence_time >= silence_duration:
                    logger.info("Wykryto ciszę, kończę nagrywanie komendy.")
                    break
            # Jeśli total_time < min_duration, ignorujemy ciszę

        stream.stop()
        stream.close()

        return np.concatenate(recorded_audio)
