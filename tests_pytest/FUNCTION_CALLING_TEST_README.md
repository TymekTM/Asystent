# 🔧 Function Calling Test Suite

Ten folder zawiera kompleksowe testy zdolności systemu Gaja do wykonywania wywołań funkcji (function calling). Testy sprawdzają, czy system poprawnie identyfikuje intencje użytkownika i wywołuje odpowiednie funkcje/narzędzia.

## 📁 Pliki testowe

### `test_function_calling_comprehensive.py`

Główny, kompleksowy test function calling zawierający:

- ✅ **Funkcje podstawowe**: czas, kalendarz, zadania, listy zakupów
- 🌤️ **Plugin pogodowy**: sprawdzanie pogody, różne dostawcy
- 🔍 **Plugin wyszukiwania**: wyszukiwanie w internecie, wiadomości
- 🧠 **Funkcje pamięci**: zapamiętywanie i przypominanie informacji
- 🚨 **Obsługa błędów**: testowanie graceful error handling
- 🎯 **Przypadki brzegowe**: złożone scenariusze, wiele wywołań

### `quick_function_calling_test.py`

Szybka wersja testów function calling przeznaczona do integracji z innymi testami:

- ⚡ Szybkie wykonanie (< 1 minuta)
- 🎯 Testuje tylko najważniejsze funkcje
- 🔗 Może być importowana i używana w innych testach
- 📊 Zwraca uproszczone wyniki

### Integracja z testem stresowym

Test function calling jest automatycznie włączony w głównym teście stresowym `test_multi_user_stress_60min.py` jako dodatkowa faza weryfikacji.

## 🚀 Jak uruchomić testy

### Uruchomienie kompleksowego testu function calling

```bash
# Uruchomienie jako pytest
cd f:\Asystent
pytest tests_pytest/test_function_calling_comprehensive.py -v

# Uruchomienie bezpośrednio
cd f:\Asystent\tests_pytest
python test_function_calling_comprehensive.py
```

### Uruchomienie szybkiego testu

```bash
cd f:\Asystent\tests_pytest
python quick_function_calling_test.py
```

### Uruchomienie testu stresowego z function calling

```bash
cd f:\Asystent
pytest tests_pytest/test_multi_user_stress_60min.py -v

# Lub przez kompletny runner
cd f:\Asystent\tests_pytest
python run_comprehensive_stress_test.py
```

## 📋 Wymagania wstępne

### 1. Uruchomiony serwer Gaja

```bash
cd f:\Asystent
python manage.py start-server
```

### 2. Poprawna konfiguracja

- Serwer dostępny na `http://localhost:8001`
- Baza danych skonfigurowana
- Pluginy (weather, search) zainstalowane

### 3. Środowisko testowe

```bash
# Instalacja zależności
pip install -r requirements_test.txt

# Sprawdzenie połączenia
curl http://localhost:8001/health
```

## 📊 Interpretacja wyników

### Metryki sukcesu

| Metryka            | Dobrze   | Ostrzeżenie | Krytycznie |
| ------------------ | -------- | ----------- | ---------- |
| **Success Rate**   | ≥85%     | 70-84%      | <70%       |
| **Response Time**  | <2s      | 2-5s        | >5s        |
| **Error Handling** | Graceful | Częściowe   | Crashes    |

### Przykładowy raport

```json
{
  "summary": {
    "overall_success_rate": 87.5,
    "total_tests": 24,
    "successful_tests": 21,
    "categories": {
      "core_functions": { "success_rate": 90.0 },
      "weather_functions": { "success_rate": 80.0 },
      "search_functions": { "success_rate": 85.0 },
      "memory_functions": { "success_rate": 95.0 }
    }
  }
}
```

### Kody wyjścia

- `0`: Excellent (≥85% success rate)
- `1`: Good with issues (≥70% success rate)
- `2`: Needs improvement (<70% success rate)

## ⚙️ Konfiguracja testów

### Zmienne środowiskowe

```bash
export GAJA_SERVER_URL="http://localhost:8001"
export GAJA_TEST_TIMEOUT=10
export GAJA_TEST_USER_PREFIX="func_test_"
```

### Parametry testu

```python
# W test_function_calling_comprehensive.py
SERVER_URL = "http://localhost:8001"
REQUEST_TIMEOUT = 10.0
MIN_SUCCESS_RATE = 70.0

# W quick_function_calling_test.py
QUICK_TIMEOUT = 5.0
ESSENTIAL_TESTS_COUNT = 5
```

## 🔧 Rozwiązywanie problemów

### Problem: Server not available

```bash
# Sprawdź status serwera
python manage.py status

# Uruchom serwer
python manage.py start-server

# Sprawdź logi
python manage.py logs
```

### Problem: Function calls not detected

1. Sprawdź czy pluginy są włączone w konfiguracji
2. Sprawdź logi serwera pod kątem błędów
3. Zweryfikuj czy endpoint `/api/chat` działa poprawnie

### Problem: Low success rate

1. **Weather plugin**: Sprawdź konfigurację API kluczy
2. **Search plugin**: Sprawdź dostęp do internetu
3. **Memory functions**: Sprawdź bazę danych
4. **Core functions**: Sprawdź podstawowe moduły serwera

### Problem: High response times

1. Sprawdź obciążenie serwera (CPU, RAM)
2. Zoptymalizuj bazę danych
3. Sprawdź połączenie sieciowe do API zewnętrznych

## 📈 Metryki i monitoring

### Performance metrics

```python
{
  "average_response_time": 1.234,
  "max_response_time": 3.456,
  "total_function_calls": 45,
  "successful_calls": 38,
  "api_success_rate": 84.4
}
```

### Function call analysis

```python
{
  "core_functions": {
    "get_current_time": {"success": True, "response_time": 0.89},
    "add_task": {"success": True, "response_time": 1.12},
    "weather": {"success": False, "error": "API key missing"}
  }
}
```

## 🚀 Rozszerzanie testów

### Dodawanie nowych funkcji

1. Dodaj test case do `test_function_calling_comprehensive.py`
2. Zaktualizuj `quick_function_calling_test.py` jeśli potrzeba
3. Dodaj odpowiednie assertion'y

### Dodawanie nowych pluginów

1. Sprawdź dostępne funkcje w `server/modules/`
2. Dodaj testy dla nowego pluginu
3. Zaktualizuj dokumentację

### Integracja z CI/CD

```yaml
# .github/workflows/test.yml
- name: Function Calling Tests
  run: |
    python manage.py start-server &
    sleep 10
    pytest tests_pytest/test_function_calling_comprehensive.py -v
    python manage.py stop-server
```

## 📚 Związane dokumenty

- **AGENTS.md**: Wymagania dotyczące kodowania
- **STRESS_TEST_README.md**: Dokumentacja testów stresowych
- **server/modules/**: Implementacje funkcji i pluginów
- **docs/**: Pełna dokumentacja systemu Gaja

---

**🔧 Function Calling to kluczowa funkcjonalność systemu Gaja - te testy zapewniają że wszystko działa jak należy!**
