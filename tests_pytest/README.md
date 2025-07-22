# Testy GAJA Assistant

Ten katalog zawiera kompleksowy zestaw testów dla systemu GAJA Assistant, obejmujący zarówno serwer jak i klient.

## Struktura testów

```
tests_pytest/
├── conftest.py              # Konfiguracja pytest i fixtures
├── test_server.py           # Testy serwera
├── test_client.py           # Testy klienta
├── test_integration.py      # Testy integracyjne
├── test_performance.py      # Testy wydajności
└── test_audio.py           # Testy komponentów audio
```

## Typy testów

### 🔧 Testy jednostkowe (Unit Tests)
- **Marker**: `@pytest.mark.unit`
- **Plik**: `test_server.py`, `test_client.py`
- **Opis**: Testują pojedyncze komponenty w izolacji

### 🔗 Testy integracyjne (Integration Tests)
- **Marker**: `@pytest.mark.integration`
- **Plik**: `test_integration.py`
- **Opis**: Testują komunikację między komponentami

### ⚡ Testy wydajności (Performance Tests)
- **Marker**: `@pytest.mark.performance`
- **Plik**: `test_performance.py`
- **Opis**: Testują wydajność i stabilność pod obciążeniem

### 🎵 Testy audio (Audio Tests)
- **Marker**: `@pytest.mark.audio`
- **Plik**: `test_audio.py`
- **Opis**: Testują komponenty audio (wakeword, ASR, TTS)

### 🐌 Testy powolne (Slow Tests)
- **Marker**: `@pytest.mark.slow`
- **Opis**: Długotrwałe testy, wyłączane domyślnie

## Instalacja zależności

```bash
# Zainstaluj zależności testowe
pip install -r requirements_test.txt

# Lub użyj skryptu
python run_tests.py install
```

## Uruchamianie testów

### Podstawowe użycie

```bash
# Wszystkie testy
python run_tests.py run

# Tylko testy jednostkowe
python run_tests.py run --type unit

# Tylko testy integracyjne
python run_tests.py run --type integration

# Tylko testy wydajności
python run_tests.py run --type performance

# Tylko testy audio
python run_tests.py run --type audio
```

### Opcje zaawansowane

```bash
# Z pokryciem kodu
python run_tests.py run --coverage

# Równoległe wykonywanie
python run_tests.py run --parallel

# Szczegółowe informacje
python run_tests.py run --verbose

# Szybkie testy (bez powolnych)
python run_tests.py run --type fast

# Konkretny plik testowy
python run_tests.py file --file test_server.py
```

### Użycie bezpośrednio pytest

```bash
# Wszystkie testy
pytest tests_pytest/

# Konkretne markery
pytest tests_pytest/ -m unit
pytest tests_pytest/ -m "unit and not slow"
pytest tests_pytest/ -m "server or client"

# Z pokryciem
pytest tests_pytest/ --cov=server --cov=client --cov-report=html

# Równolegle
pytest tests_pytest/ -n auto
```

## Konfiguracja środowiska

### Sprawdzenie środowiska
```bash
python run_tests.py check
```

### Odkrywanie testów
```bash
python run_tests.py discover
```

### Generowanie raportów
```bash
python run_tests.py report
```

## Markery testów

| Marker | Opis |
|--------|------|
| `unit` | Testy jednostkowe |
| `integration` | Testy integracyjne |
| `server` | Testy serwera |
| `client` | Testy klienta |
| `websocket` | Testy WebSocket |
| `database` | Testy bazy danych |
| `ai` | Testy modułów AI |
| `audio` | Testy komponentów audio |
| `plugin` | Testy systemu pluginów |
| `performance` | Testy wydajności |
| `slow` | Powolne testy |

## Fixtures dostępne

### Podstawowe
- `event_loop` - Pętla zdarzeń asyncio
- `temp_config_dir` - Tymczasowy katalog konfiguracji
- `mock_config` - Mock konfiguracji
- `mock_db_manager` - Mock menedżera bazy danych
- `mock_ai_module` - Mock modułu AI
- `mock_websocket` - Mock połączenia WebSocket

### Aplikacje
- `server_app` - Instancja ServerApp
- `client_app` - Instancja ClientApp

### Audio
- `mock_audio_components` - Mock komponentów audio
- `mock_plugin` - Mock pluginu

### Dane testowe
- `sample_chat_data` - Przykładowe dane czatu
- `sample_plugin_data` - Przykładowe dane pluginów

## Przykłady użycia

### Test jednostkowy
```python
@pytest.mark.unit
def test_connection_manager_init():
    manager = ConnectionManager()
    assert manager.active_connections == {}
```

### Test integracyjny
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_websocket_communication(server_app, client_app):
    # Test komunikacji klient-serwer
    response = await server_app.process_user_request(user_id, message)
    assert response["type"] == "ai_response"
```

### Test audio
```python
@pytest.mark.audio
@pytest.mark.asyncio
async def test_whisper_transcription(mock_audio_components):
    asr = mock_audio_components["whisper_asr"]
    result = await asr.transcribe(audio_data)
    assert result == "Expected transcription"
```

### Test wydajności
```python
@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
async def test_high_frequency_requests(server_app):
    # Test wielu requestów
    for i in range(100):
        response = await server_app.process_user_request(user_id, request)
        assert response["type"] == "ai_response"
```

## Raporty testów

### HTML Report
Po uruchomieniu z `--coverage` dostępny w `htmlcov/index.html`

### JSON Report
Po uruchomieniu z `python run_tests.py report` dostępny w `test_report.json`

### XML Report
Dla integracji CI/CD w `coverage.xml`

## Debugging testów

### Uruchomienie jednego testu
```bash
pytest tests_pytest/test_server.py::TestConnectionManager::test_connect_user -v
```

### Z debuggerem
```bash
pytest tests_pytest/test_server.py::test_specific_function --pdb
```

### Z logami
```bash
pytest tests_pytest/ --log-cli-level=DEBUG
```

## Integracja CI/CD

### GitHub Actions
```yaml
- name: Run tests
  run: |
    python run_tests.py install
    python run_tests.py run --type unit --coverage
    python run_tests.py run --type integration
```

### Coverage Badge
Używa pliku `coverage.xml` do generowania badge pokrycia kodu.

## Najlepsze praktyki

1. **Używaj odpowiednich markerów** dla kategoryzacji testów
2. **Mock zewnętrzne zależności** w testach jednostkowych
3. **Testuj happy path i edge cases** 
4. **Używaj fixtures** dla wspólnych setupów
5. **Nazywaj testy opisowo** - `test_should_do_something_when_condition`
6. **Grupuj testy w klasy** dla lepszej organizacji
7. **Używaj async/await** dla testów asynchronicznych
8. **Sprawdzaj nie tylko sukces** ale też odpowiednie błędy

## Rozwiązywanie problemów

### Import errors
- Sprawdź czy `PYTHONPATH` zawiera odpowiednie katalogi
- Uruchom `python run_tests.py check`

### Błędy audio testów
- Sprawdź czy wszystkie mock komponenty są skonfigurowane
- Sprawdź czy system ma dostęp do urządzeń audio (dla testów integracyjnych)

### Timeouty
- Użyj `@pytest.mark.timeout(30)` dla długich testów
- Sprawdź czy nie ma deadlocków w kodzie asynchronicznym

### Problemy z fixtures
- Sprawdź scope fixtures (`session`, `module`, `function`)
- Upewnij się że fixtures są importowane w `conftest.py`
