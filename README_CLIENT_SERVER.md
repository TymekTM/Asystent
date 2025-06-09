# GAJA Assistant - Architektura Klient-Serwer

## Opis architektury

Aplikacja GAJA została podzielona na dwie niezależne części:

### 🖥️ Serwer (`/server/`)
- **FastAPI** z WebSocket dla komunikacji
- Obsługuje **wielu użytkowników** jednocześnie
- Zarządza **AI providers** (OpenAI, Anthropic, Ollama)
- Przechowuje dane w **bazie SQLite**
- System **dynamicznych pluginów** per użytkownik
- Centralne **logowanie** i **monitoring**

### 💻 Klient (`/client/`)
- **Lokalne komponenty**: wakeword, overlay, Whisper ASR
- Komunikacja z serwerem przez **WebSocket**
- Lekka logika - większość przetwarzania na serwerze
- Lokalne przechowywanie ustawień użytkownika

## Struktura plików

```
/server/
├── server_main.py          # Główna aplikacja FastAPI
├── server_config.json      # Konfiguracja serwera
├── requirements_server.txt # Zależności serwera
├── config_loader.py       # Ładowanie konfiguracji
├── database_manager.py    # Zarządzanie bazą danych
├── database_models.py     # Modele danych
├── ai_module.py          # Moduł AI
├── function_calling_system.py # System funkcji
├── prompts.py            # Prompty AI
└── modules/              # Pluginy serwera
    ├── api_module.py
    ├── weather_module.py
    ├── search_module.py
    └── memory_module.py

/client/
├── client_main.py          # Główna aplikacja klienta
├── client_config.json      # Konfiguracja klienta
├── requirements_client.txt # Zależności klienta
└── audio_modules/          # Moduły audio klienta
    ├── wakeword_detector.py
    ├── whisper_asr.py
    └── tts_module.py
```

## Instalacja i uruchomienie

### 1. Przygotowanie środowiska serwera

```bash
cd server
python -m venv venv_server
venv_server\Scripts\activate  # Windows
# source venv_server/bin/activate  # Linux/Mac

pip install -r requirements_server.txt
```

### 2. Konfiguracja serwera

Edytuj `server/server_config.json`:
```json
{
    "api_keys": {
        "openai": "YOUR_OPENAI_API_KEY_HERE",
        "anthropic": "YOUR_ANTHROPIC_API_KEY_HERE"
    }
}
```

### 3. Uruchomienie serwera

```bash
cd server
python server_main.py
```

Serwer uruchomi się na `http://localhost:8000`

### 4. Przygotowanie środowiska klienta

```bash
cd client
python -m venv venv_client
venv_client\Scripts\activate  # Windows
# source venv_client/bin/activate  # Linux/Mac

pip install -r requirements_client.txt
```

### 5. Uruchomienie klienta

```bash
cd client
python client_main.py
```

### 6. Test całego systemu

```bash
# Z głównego katalogu
python test_client_server.py
```

## Komunikacja WebSocket

### Protokół komunikacji

**Klient → Serwer:**
```json
{
    "type": "ai_query",
    "query": "Jaka jest pogoda?",
    "context": {}
}
```

**Serwer → Klient:**
```json
{
    "type": "ai_response",
    "response": "Dzisiaj jest słonecznie...",
    "timestamp": 1641234567.89
}
```

### Dostępne typy wiadomości

- `ai_query` - zapytanie do AI
- `function_call` - wywołanie funkcji/pluginu
- `plugin_toggle` - włączenie/wyłączenie pluginu
- `ai_response` - odpowiedź AI
- `function_result` - wynik funkcji
- `plugin_toggled` - potwierdzenie zmiany pluginu
- `error` - komunikat błędu

## System pluginów

### Włączanie/wyłączanie pluginów per użytkownik

```json
{
    "type": "plugin_toggle",
    "plugin": "weather_module",
    "action": "enable"  // lub "disable"
}
```

### Dodawanie nowych pluginów

1. Utwórz plik w `server/modules/new_plugin.py`
2. Zaimplementuj funkcje `get_functions()` i `execute_function()`
3. Plugin zostanie automatycznie wykryty przez serwer

## Baza danych

Serwer używa SQLite z następującymi tabelami:

- `users` - użytkownicy systemu
- `user_sessions` - sesje WebSocket
- `messages` - historia konwersacji
- `memory_contexts` - kontekst pamięci
- `api_usage` - statystyki użycia API
- `system_logs` - logi systemowe
- `user_preferences` - preferencje użytkowników (w tym pluginy)

## Logowanie

### Serwer
- Logi w `server/logs/server_YYYY-MM-DD.log`
- Format: timestamp | level | module:function:line | message

### Klient
- Logi w `client/logs/client_YYYY-MM-DD.log`
- Format: timestamp | level | module:function:line | message

## API Endpoints

### FastAPI endpoints

- `GET /` - status serwera
- `GET /health` - health check
- `WebSocket /ws/{user_id}` - komunikacja z klientem

### Swagger UI

Dokumentacja API dostępna pod: `http://localhost:8000/docs`

## Rozwój

### Dodawanie nowych funkcji

1. **Po stronie serwera** - logika biznesowa, AI, baza danych
2. **Po stronie klienta** - interfejs użytkownika, audio, overlay

### Testowanie

```bash
# Test komunikacji
python test_client_server.py

# Test serwera
cd server
python -m pytest tests/

# Test klienta
cd client
python -m pytest tests/
```

## Troubleshooting

### Problemy z połączeniem

1. Sprawdź czy serwer działa na porcie 8000
2. Sprawdź konfigurację `server_url` w `client_config.json`
3. Sprawdź logi serwera i klienta

### Problemy z AI

1. Sprawdź klucze API w `server_config.json`
2. Sprawdź dostępność wybranego providera
3. Sprawdź logi w `server/logs/`

### Problemy z audio (klient)

1. Sprawdź dostępne urządzenia audio
2. Sprawdź uprawnienia do mikrofonu
3. Sprawdź instalację bibliotek audio

## Roadmap

- [ ] Implementacja wakeword detection
- [ ] Implementacja overlay GUI
- [ ] Implementacja Whisper ASR
- [ ] System autentykacji użytkowników
- [ ] Szyfrowanie komunikacji WebSocket
- [ ] Cluster mode dla serwera
- [ ] Mobile client (React Native)
- [ ] Web client (React)
