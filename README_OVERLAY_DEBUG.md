# GAJA Overlay Debug Tools

Narzędzie debugowania dla systemu overlay GAJA Assistant. Pozwala na testowanie wszystkich funkcji overlay indywidualnie w prostym interfejsie użytkownika.

## Funkcje

### 🎛️ Status Control (Kontrola Statusu)

- **Show/Hide Overlay**: Pokaż/ukryj overlay
- **Get Status**: Pobierz aktualny status
- **Status State Testing**: Testuj różne stany (listening, speaking, wake word)
- **Auto-refresh**: Automatyczne odświeżanie statusu co 2 sekundy

### 📝 Text Testing (Testowanie Tekstu)

- **Preset Text**: Gotowe teksty testowe (krótkie, średnie, długie, bardzo długie)
- **Special Characters**: Testowanie polskich znaków, emoji, symboli
- **Custom Text**: Własny tekst do wyświetlenia
- **Text Clearing**: Czyszczenie tekstu z overlay

### 🎬 Animation Testing (Testowanie Animacji)

- **Ball Animation**: Testowanie animacji kuli (listening, speaking, wake word)
- **Status Text Animation**: Testowanie animacji tekstu statusu
- **Full Interaction Sequence**: Pełna sekwencja interakcji (wake word → listening → speaking → idle)
- **Timing Control**: Kontrola czasu trwania sekwencji

### 🔧 System Testing (Testowanie Systemu)

- **Connection Testing**: Test połączenia z serwerem
- **API Endpoints**: Test wszystkich endpointów API
- **SSE Stream**: Test strumieniowania Server-Sent Events
- **Performance Testing**: Testy wydajności (szybkie zmiany, duży tekst)
- **Error Handling**: Testowanie obsługi błędów

### 📊 Log Viewer (Przeglądarka Logów)

- **Real-time Logs**: Logi w czasie rzeczywistym
- **Export Logs**: Eksport logów do pliku
- **Auto-scroll**: Automatyczne przewijanie logów

## Instalacja

1. **Zainstaluj zależności**:

   ```powershell
   pip install -r requirements_overlay_debug.txt
   ```

2. **Upewnij się, że serwer GAJA jest uruchomiony**:

   ```powershell
   # Dla rozwoju (port 5001)
   python manage.py start-server

   # Lub sprawdź status
   python manage.py status
   ```

## Użycie

1. **Uruchom narzędzie debugowania**:

   ```powershell
   python overlay_debug_tools.py
   ```

2. **Interfejs składa się z 5 zakładek**:
   - **Status Control**: Podstawowa kontrola overlay
   - **Text Testing**: Testowanie wyświetlania tekstu
   - **Animation Testing**: Testowanie animacji
   - **System Testing**: Testy systemu i połączeń
   - **Log Viewer**: Przeglądanie logów

## Przykłady Użycia

### Podstawowe Testowanie

1. Przejdź do zakładki **Status Control**
2. Kliknij **Get Status** aby sprawdzić połączenie
3. Kliknij **Show Overlay** aby pokazać overlay
4. Przetestuj różne stany: **Set Listening**, **Set Speaking**, **Set Wake Word**

### Testowanie Tekstu

1. Przejdź do zakładki **Text Testing**
2. Użyj przycisków **Preset Text** dla szybkiego testowania
3. Lub wpisz własny tekst i kliknij **Send Text to Overlay**
4. Przetestuj polskie znaki przyciskiem **Polish Text**

### Testowanie Animacji

1. Przejdź do zakładki **Animation Testing**
2. Przetestuj poszczególne animacje: **Show Ball (Listening/Speaking/Wake Word)**
3. Uruchom **Full Interaction Sequence** dla pełnego testu
4. Dostosuj timing w polu **Sequence Timing**

### Testowanie Systemu

1. Przejdź do zakładki **System Testing**
2. **Test Connection** - sprawdź połączenie
3. **Test API Endpoints** - przetestuj wszystkie API
4. **Test SSE Stream** - sprawdź strumieniowanie
5. **Performance Tests** - testy wydajności

## Konfiguracja

### Port Serwera

- Domyślnie: `5001` (development)
- Możesz zmienić w zakładce **System Testing** → **Server Port**
- Produkcja zwykle używa portu `5000`

### Auto-refresh

- Domyślnie włączony (odświeżanie co 2 sekundy)
- Możesz wyłączyć checkbox **Auto-refresh status**

## Rozwiązywanie Problemów

### Overlay nie odpowiada

1. Sprawdź czy serwer GAJA jest uruchomiony:
   ```powershell
   python manage.py status
   ```
2. Sprawdź port w **System Testing** → **Test Connection**
3. Sprawdź logi w zakładce **Log Viewer**

### Błędy połączenia

1. Upewnij się, że używasz właściwego portu (5001 dev, 5000 prod)
2. Sprawdź firewall i antywirus
3. Przetestuj **Test API Endpoints** dla szczegółowej diagnozy

### Overlay nie wyświetla się

1. Sprawdź czy overlay executable istnieje: `client/overlay/gaja-overlay.exe`
2. Może być potrzebne zbudowanie overlay:
   ```powershell
   python manage.py build-client
   ```
3. Sprawdź logi systemu Windows Event Viewer

## Architektura

### Asynchroniczne API

- Wszystkie komunikacje używają `aiohttp` dla async I/O
- Zgodne z guidelines AGENTS.md (no blocking operations)
- Thread-safe integration z tkinter GUI

### Endpoints API

- `GET /api/status` - Status overlay
- `POST /overlay/show` - Pokaż overlay
- `POST /overlay/hide` - Ukryj overlay
- `POST /overlay/update` - Aktualizuj status
- `GET /status/stream` - SSE stream

### Error Handling

- Comprehensive error logging
- Graceful degradation przy problemach z połączeniem
- User-friendly error messages

## Development

### Testowanie

```powershell
# Uruchom testy
python -m pytest tests/test_overlay_debug_tools.py -v

# Testy z coverage
python -m pytest tests/test_overlay_debug_tools.py --cov=overlay_debug_tools
```

### Dodawanie Nowych Funkcji

1. Dodaj async funkcję w klasie `OverlayDebugToolsGUI`
2. Dodaj UI controls w odpowiedniej `_setup_*_tab` metodzie
3. Użyj `_safe_async_call()` wrapper dla GUI callbacks
4. Dodaj testy w `tests/test_overlay_debug_tools.py`

## Zgodność z AGENTS.md

✅ **Async-first**: Wszystkie operacje I/O są asynchroniczne
✅ **Test Coverage**: Comprehensive test suite
✅ **Error Handling**: Graceful error handling i logging
✅ **Modularity**: Czysta separacja GUI i logiki
✅ **Documentation**: Pełna dokumentacja i docstrings
✅ **Type Hints**: Type hints we wszystkich funkcjach

## Licencja

Część projektu GAJA Assistant. Zobacz główny README dla szczegółów licencji.
