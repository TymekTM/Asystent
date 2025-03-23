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
STT_MODEL = "gemma3:4b-it-q4_K_M"     # do refinowania promptu ze stt
MAIN_MODEL = "gemma3:4b-it-q4_K_M"    # do zwykłych odpowiedzi
DEEP_MODEL = "openthinker"  # do głębokiego rozumowania

# Wybór dostawcy: dostępne opcje: "ollama", "lmstudio", "openai", "deepseek", "anthropic", "transformer"
PROVIDER = "lmstudio"  # <- zmień tutaj na wybranego dostawcę

# Ustawienia dla Whisper jako alternatywy STT
USE_WHISPER_FOR_COMMAND = False # Jak nie działa ci cuda, gigantyczne zużycie CPU, wyniki o wiele lepsze (wszystkie językie nie tylko polski)
WHISPER_MODEL = "openai/whisper-small"