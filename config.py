# config.py

# Ścieżka do modelu Vosk
VOSK_MODEL_PATH = "vosk_model"

# Numer urządzenia mikrofonu
MIC_DEVICE_ID = 5

# Słowo kluczowe aktywujące asystenta
WAKE_WORD = "asystencie"

# Próg ciszy w STT
STT_SILENCE_THRESHOLD = 600

# MODELE
STT_MODEL = "gemma3:4B"     # do refinowania promptu ze stt
MAIN_MODEL = "gemma3:4B"    # do zwykłych odpowiedzi
DEEP_MODEL = "openthinker"  # do głębokiego rozumowania

# Ustawienia dla Whisper jako alternatywy STT
USE_WHISPER_FOR_COMMAND = False # Jak nie działa ci cuda, gigantyczne zużycie CPU, wyniki o wiele lepsze (wszystkie językie nie tylko polski)
WHISPER_MODEL = "openai/whisper-small"