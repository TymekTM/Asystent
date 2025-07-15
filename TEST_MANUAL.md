# Test Manual po Naprawach

## Uruchomienie Testów

1. **Uruchom klienta:**

   ```bash
   python client/client_main.py
   ```

2. **Sprawdź logi czy TTS się inicjalizuje:**

   - Poszukaj: `Legacy TTS module initialized` lub `Force-created TTS module`
   - Powinno być: `TTS settings adjusted`

3. **Sprawdź HTTP server:**

   - Powinno być: `HTTP server started on port 5001 for overlay`

4. **Sprawdź overlay process:**
   - Powinno być: `Started Tauri overlay process: [PID]`

## Testowanie Napraw

### 1. Settings Page

- Kliknij prawym na system tray -> "Ustawienia"
- Powinno otworzyć: http://localhost:5001/settings.html
- Strona powinna się załadować (nie pusta strona)

### 2. Overlay Click-Through

- Overlay powinien być zawsze aktywny (okno istnieje)
- Kiedy się wyświetla treść, nadal powinno być click-through
- Nie powinno blokować kliknięć

### 3. TTS Daily Briefing

- Wyślij daily briefing z serwera
- Powinno być wypowiedziane na głos
- Logi powinny pokazać: `Daily briefing spoken successfully`

### 4. Audio Devices

- Otwórz settings
- Sprawdź czy widać listę urządzeń audio
- Alternatywnie: `curl http://localhost:5001/api/audio_devices`

## Testowanie API

```bash
# Status
curl http://localhost:5001/api/status

# Audio devices
curl http://localhost:5001/api/audio_devices

# Test mikrofonu
curl http://localhost:5001/api/test_microphone

# Test TTS
curl http://localhost:5001/api/test_tts

# Settings page
curl http://localhost:5001/settings.html
```

## Oczekiwane Zachowanie

### Overlay

- ✅ Zawsze aktywny (okno istnieje)
- ✅ Pokazuje treść tylko gdy potrzeba
- ✅ Zawsze click-through (nie blokuje kliknięć)
- ✅ System tray: "Wyłącz overlay" wyłącza wyświetlanie treści
- ✅ System tray: "Zamknij" zamyka klienta i overlay

### TTS

- ✅ Inicjalizuje się przy starcie
- ✅ Daily briefing jest wypowiadany
- ✅ Fallback gdy inicjalizacja się nie powiedzie

### Settings

- ✅ Dostępne przez system tray
- ✅ Dostępne przez HTTP
- ✅ Pokazuje urządzenia audio
- ✅ Pozwala na testowanie mikrofonu i TTS

## Rozwiązywanie Problemów

### TTS nie działa

1. Sprawdź logi inicjalizacji TTS
2. Sprawdź czy OpenAI API key jest ustawiony
3. Sprawdź czy ffmpeg jest zainstalowany

### Settings nie ładuje się

1. Sprawdź czy HTTP server jest uruchomiony
2. Sprawdź czy plik settings.html istnieje
3. Sprawdź porty 5001 i 5000

### Overlay blokuje kliknięcia

1. Sprawdź logi Rust: `[Rust] ZAWSZE włącz click-through`
2. Overlay powinien być zawsze przeźroczysty
3. Restart overlay process

## Logi do Monitorowania

```
# Inicjalizacja TTS
Force-created TTS module
TTS settings adjusted

# Overlay
[Rust] Overlay started and hidden with click-through enabled
[Rust] ZAWSZE włącz click-through - overlay ma być przeźroczysty

# Settings
Settings requested from system tray
Opened settings via HTTP server
Served settings.html from [path]

# Daily briefing
Daily briefing received: [text]
Starting TTS for daily briefing...
Daily briefing spoken successfully
```

## Błędy do Naprawienia

Jeśli nadal występują problemy:

1. **TTS nie inicjalizuje się** - sprawdź czy moduł TTS jest dostępny
2. **Settings pusta strona** - sprawdź czy plik HTML jest prawidłowo serwowany
3. **Overlay blokuje kliknięcia** - sprawdź implementację click-through w Rust
4. **System tray nie działa** - sprawdź czy pystray jest zainstalowany
