# GAJA Assistant - Kompletny Przewodnik Użytkownika

## 🎯 System Requirements

### Server Environment
- Python 3.8+
- SQLite
- Ollama z modelem gemma3:4b-it-q4_K_M (lub inny lokalny model)
- FastAPI, websockets, loguru

### Client Environment  
- Python 3.8+
- Tkinter (dla overlay GUI)
- sounddevice (dla audio)
- numpy
- whisper lub faster-whisper (dla ASR)
- openwakeword (opcjonalne, dla advanced wakeword detection)

## 🚀 Uruchomienie Systemu

### 1. Przygotowanie Środowiska

```bash
# Klonowanie/przejście do katalogu
cd F:\Asystent

# Serwer - instalacja zależności
cd server
pip install -r requirements_server.txt

# Klient - instalacja zależności  
cd ../client
pip install -r requirements_client.txt
```

### 2. Konfiguracja Bazy Danych

```bash
# Z głównego katalogu
python setup_test_user.py
```

To utworzy:
- Bazę danych SQLite (`gaja_memory.db`)
- Testowego użytkownika (ID: 1, username: "test_user")
- Struktura tabel dla użytkowników, pluginów, pamięci, historii

### 3. Uruchomienie Serwera

```bash
cd server
python server_main.py
```

Serwer uruchomi się na:
- WebSocket: `ws://localhost:8000/ws/{user_id}`
- HTTP API: `http://localhost:8000`
- Dashboard (opcjonalnie): `http://localhost:8000/`

### 4. Uruchomienie Klienta

```bash
cd client  
python client_main.py
```

Klient:
- Połączy się z serwerem przez WebSocket
- Uruchomi wakeword detection (jeśli dostępne)
- Wyświetli overlay UI
- Rozpocznie nasłuchiwanie komend głosowych

## 🎙️ Używanie Systemu

### Interakcja Głosowa

1. **Wakeword Detection**: Powiedz "Hey Jarvis" (lub po prostu głośniej mów jeśli używasz simple detection)
2. **Komenda**: Po wykryciu wakeword, masz 5 sekund na wydanie komendy
3. **Przetwarzanie**: Whisper ASR transkrybuje audio → serwer przetwarza przez AI → odpowiedź w overlay

### Przykładowe Komendy

```
"Jaka jest pogoda w Warszawie?"
→ Użyje weather_module (tryb testowy)

"Zapamiętaj, że lubię kawę rano"
→ Użyje memory_module do zapisania preferencji

"Co zapamiętałeś o mnie?"
→ Wyszuka informacje w memory_module

"Wyszukaj informacje o Python"
→ Użyje search_module (tryb testowy)
```

### WebSocket Messages

Klient wysyła:
```json
{
    "type": "ai_query",
    "query": "Jaka jest pogoda?",
    "context": {
        "input_method": "voice",
        "language": "pl"
    }
}
```

Serwer odpowiada:
```json
{
    "type": "ai_response", 
    "response": "Pogoda w trybie testowym: słonecznie, 22°C...",
    "function_calls": [...],
    "tokens_used": 45
}
```

## 🔌 System Pluginów

### Dostępne Pluginy

1. **weather_module**
   - `get_weather(location, test_mode=True)` - dane pogodowe
   - `get_forecast(location, days=3)` - prognoza pogody

2. **search_module**
   - `search(query, engine="duckduckgo", test_mode=True)` - wyszukiwanie
   - `search_news(query, language="pl")` - wiadomości

3. **memory_module**
   - `save_memory(memory_type, key, value, metadata)` - zapis do pamięci
   - `get_memory(memory_type, key)` - odczyt z pamięci
   - `search_memory(query)` - wyszukiwanie w pamięci

4. **api_module**
   - `make_api_request(method, url, headers, params)` - zapytania API

### Zarządzanie Pluginami

```bash
# Testowanie pluginów
python test_plugins.py

# Lista pluginów (z poziomu serwera)
curl http://localhost:8000/plugins/list/1

# Włączenie/wyłączenie pluginu
curl -X POST http://localhost:8000/plugins/toggle/1 \
  -H "Content-Type: application/json" \
  -d '{"plugin": "weather_module", "action": "enable"}'
```

## 💾 Struktura Bazy Danych

### Tabele

- **users** - informacje o użytkownikach
- **user_plugin_preferences** - preferencje pluginów per user
- **memory_contexts** - system pamięci kontekstowej
- **conversation_history** - historia rozmów
- **api_usage_logs** - logi użycia API

### Przykładowe Zapytania

```sql
-- Sprawdź użytkowników
SELECT * FROM users;

-- Sprawdź włączone pluginy dla użytkownika
SELECT * FROM user_plugin_preferences WHERE user_id = 1 AND enabled = 1;

-- Sprawdź pamięć użytkownika
SELECT * FROM memory_contexts WHERE user_id = 1;

-- Historia rozmów
SELECT * FROM conversation_history WHERE user_id = 1 ORDER BY timestamp DESC LIMIT 10;
```

## 🔧 Konfiguracja

### Server Config (`server/server_config.json`)

```json
{
    "host": "localhost",
    "port": 8000,
    "ai_provider": "ollama",
    "ollama_model": "gemma3:4b-it-q4_K_M",
    "ollama_base_url": "http://localhost:11434",
    "database": {
        "path": "../gaja_memory.db",
        "echo": false
    }
}
```

### Client Config (`client/client_config.json`)

```json
{
    "user_id": "1",
    "server_url": "ws://localhost:8000",
    "wakeword": {
        "enabled": true,
        "sensitivity": 0.6
    },
    "whisper": {
        "model": "base",
        "language": "pl"
    },
    "overlay": {
        "enabled": true,
        "position": "top-right",
        "auto_hide_delay": 10
    },
    "audio": {
        "sample_rate": 16000,
        "record_duration": 5.0
    }
}
```

## 🐛 Rozwiązywanie Problemów

### Częste Problemy

1. **"sounddevice not available"**
   ```bash
   pip install sounddevice
   ```

2. **"whisper not available"**
   ```bash
   pip install openai-whisper
   # lub
   pip install faster-whisper
   ```

3. **"openwakeword not available"**
   ```bash
   pip install openwakeword
   # Fallback: używa simple volume-based detection
   ```

4. **Problemy z Tkinter**
   - Windows: Tkinter zwykle włączony w Pythonie
   - Linux: `sudo apt-get install python3-tk`
   - Fallback: Console overlay

5. **Błąd połączenia WebSocket**
   - Sprawdź czy serwer działa: `curl http://localhost:8000/`
   - Sprawdź konfigurację portów
   - Sprawdź logi serwera

### Logi

- **Serwer**: `server/logs/server_YYYY-MM-DD.log`
- **Klient**: `client/logs/client_YYYY-MM-DD.log`
- **Konsola**: Kolorowe logi w czasie rzeczywistym

## 📊 Monitoring i Metryki

### Performance Monitoring

```bash
# Sprawdź status serwera
curl http://localhost:8000/health

# Metryki wydajności (jeśli włączone)
curl http://localhost:8000/metrics
```

### Database Monitoring

```bash
# Debugowanie bazy
python debug_database.py

# Test pamięci bezpośredni
python test_memory_direct.py
```

## 🎭 Demonstracja

```bash
# Pełna demonstracja funkcjonalności
python demo_functionality.py

# Szybki test komponentów
python test_functionality.py

# Test pluginów
python test_plugins.py
```

## 🔐 Bezpieczeństwo

### Obecny Stan
- ✅ Lokalny AI (brak wysyłania danych zewnętrznie)
- ✅ Plikowa baza SQLite (brak ekspozycji sieciowej)
- ✅ WebSocket tylko na localhost
- ⚠️ Brak autentykacji/autoryzacji
- ⚠️ Brak szyfrowania komunikacji WebSocket

### Planowane Ulepszenia
- Autentykacja użytkowników
- Szyfrowanie komunikacji WebSocket
- Rate limiting
- Secure configuration management

## 📈 Rozwój

### Dodawanie Nowych Pluginów

1. Utwórz plik `server/modules/moj_plugin.py`
2. Zaimplementuj funkcje `get_functions()` i `execute_function()`
3. Plugin zostanie automatycznie wykryty
4. Włącz dla użytkownika przez API lub bazę danych

### Przykład Nowego Pluginu

```python
def get_functions():
    return [{
        "name": "my_function",
        "description": "Opis funkcji",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parametr"}
            },
            "required": ["param1"]
        }
    }]

async def execute_function(function_name, parameters, user_id):
    if function_name == "my_function":
        # Implementacja
        return {"success": True, "data": "result"}
```

## 🎉 Gratulacje!

System GAJA Assistant został pomyślnie zaimplementowany jako architektura klient-serwer z pełną funkcjonalnością voice processing, AI integration, plugin system i persistent storage. System jest gotowy do testowania i dalszego rozwoju!
