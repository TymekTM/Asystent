import json
import logging
import os
import queue
import subprocess
import time

import numpy as np
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    def __init__(self, model_path: str, mic_device_id: int, stt_silence_threshold: int = 600):
        if not os.path.exists(model_path):
            raise Exception("Model Vosk nie znaleziony!")
        self.model = Model(model_path)
        self.mic_device_id = mic_device_id
        self.stt_silence_threshold = stt_silence_threshold
        self.audio_q = queue.Queue()
        # Nie używamy webrtcvad – fallback oparty na RMS z dynamiczną kalibracją
        self.vad = None

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            logger.warning("Audio status: %s", status)
        self.audio_q.put(bytes(indata))

    def play_beep(self):
        beep_file = "beep.mp3"
        if os.path.exists(beep_file):
            try:
                subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", beep_file])
            except Exception as e:
                logger.error("Error playing beep: %s", e)
        else:
            logger.warning("beep.mp3 nie został znaleziony.")

    def calibrate_threshold(self, duration=0.5) -> float:
        logger.info("Kalibruję poziom tła przez %.1f sekund...", duration)
        noise_values = []
        calib_start = time.time()
        while time.time() - calib_start < duration:
            try:
                data = self.audio_q.get(timeout=0.05)
            except queue.Empty:
                continue
            audio_array = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt((audio_array ** 2).mean())
            noise_values.append(rms)
        if noise_values:
            avg_noise = sum(noise_values) / len(noise_values)
            dynamic_threshold = avg_noise * 1.5
            logger.info("Dynamiczny próg ustawiony na: %.2f", dynamic_threshold)
            return dynamic_threshold
        return self.stt_silence_threshold

    def listen_command(self, min_command_duration=3.0, silence_duration=1.0, frame_duration_ms=30) -> str:
        logger.info("Nasłuchiwanie komendy (fallback RMS z dynamiczną kalibracją)...")
        self.play_beep()
        dynamic_threshold = self.calibrate_threshold()
        recognizer = KaldiRecognizer(self.model, 16000)
        silence_start = None
        start_time = time.time()
        collected_audio = bytearray()
        while True:
            try:
                data = self.audio_q.get(timeout=0.05)
            except queue.Empty:
                if silence_start and (time.time() - silence_start >= silence_duration) and (time.time() - start_time >= min_command_duration):
                    break
                continue
            collected_audio.extend(data)
            audio_array = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt((audio_array ** 2).mean())
            if rms > dynamic_threshold:
                silence_start = None
            else:
                if silence_start is None:
                    silence_start = time.time()
        recognizer.AcceptWaveform(bytes(collected_audio))
        result = json.loads(recognizer.Result())
        return result.get("text", "")
