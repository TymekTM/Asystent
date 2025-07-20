# Konfiguracja Mikrofonu - GAJA Assistant

## ✅ STATUS: SKONFIGUROWANY I DZIAŁAJĄCY

Mikrofon został pomyślnie skonfigurowany i rozpoznawanie słowa kluczowego "gaja" działa poprawnie.

**Obecna konfiguracja:**

- Urządzenie: ID 15 - "Mic | Line 2 (2 — Audient EVO4)"
- Status: ✅ Działa poprawnie
- Rozpoznawanie: ✅ Słowo "gaja" jest wykrywane
- Poziomy audio: Energy ~0.001-0.004, Max ~0.1-0.3

Ten przewodnik pomoże Ci skonfigurować mikrofon wejściowy dla asystenta GAJA.

## Szybki Start

### 1. Zobacz dostępne urządzenia audio

```bash
python configure_microphone.py list
```

### 2. Przetestuj mikrofon

```bash
python configure_microphone.py test <ID_URZĄDZENIA>
```

Przykład: `python configure_microphone.py test 1`

### 3. Ustaw mikrofon

```bash
python configure_microphone.py set <ID_URZĄDZENIA>
```

Przykład: `python configure_microphone.py set 1`

### 4. Sprawdź aktualne ustawienia

```bash
python configure_microphone.py status
```

## Pliki Konfiguracyjne

Ustawienia mikrofonu są synchronizowane w następujących plikach:

- **`config.json`** - Główny plik konfiguracyjny (MIC_DEVICE_ID)
- **`client/client_config.json`** - Konfiguracja klienta (wakeword.device_id, whisper.device_id, audio.input_device)

## Przykład Użycia

```bash
# 1. Zobacz dostępne mikrofony
python configure_microphone.py list

# Wynik:
# ID   1: Mic | Line 1/2 (2 — Audient EVO (DEFAULT)
# ID  54: Mic | Line 2 (2 — Audient EVO4)
# ID  97: Mikrofon (DroidCam Virtual Audio)

# 2. Przetestuj mikrofon
python configure_microphone.py test 1

# 3. Ustaw jako główny mikrofon
python configure_microphone.py set 1

# 4. Sprawdź że wszystko jest ustawione
python configure_microphone.py status
```

## Rozwiązywanie Problemów

### Niski sygnał mikrofonu

Jeśli test mikrofonu pokazuje "Low signal", sprawdź:

- Poziom głośności mikrofonu w systemie Windows
- Czy mikrofon jest włączony i nie wyciszony
- Czy używasz właściwego wejścia audio

### Inconsistent settings (Niespójne ustawienia)

Jeśli `status` pokazuje różne ID urządzeń w różnych konfiguracjach:

```bash
python configure_microphone.py set <ID_WŁAŚCIWEGO_URZĄDZENIA>
```

### Urządzenie nie działa

1. Sprawdź czy urządzenie istnieje: `python configure_microphone.py list`
2. Przetestuj urządzenie: `python configure_microphone.py test <ID>`
3. Sprawdź ustawienia systemu Windows

## Ręczna Edycja

Możesz również ręcznie edytować pliki konfiguracyjne:

### client/client_config.json

```json
{
  "wakeword": {
    "device_id": 1
  },
  "whisper": {
    "device_id": 1
  },
  "audio": {
    "input_device": 1
  }
}
```

### config.json

```json
{
  "MIC_DEVICE_ID": 1
}
```

**⚠️ Pamiętaj:** Po zmianie konfiguracji należy zrestartować klienta GAJA.

## Komendy

| Komenda     | Opis                                         |
| ----------- | -------------------------------------------- |
| `list`      | Wyświetl wszystkie dostępne urządzenia audio |
| `test <ID>` | Przetestuj określone urządzenie              |
| `set <ID>`  | Ustaw mikrofon dla wszystkich konfiguracji   |
| `status`    | Pokaż aktualne ustawienia mikrofonu          |

## Wsparcie

Jeśli masz problemy z konfiguracją mikrofonu:

1. Uruchom `python configure_microphone.py status` i sprawdź czy wszystkie konfiguracje są spójne
2. Przetestuj urządzenie przed ustawieniem: `python configure_microphone.py test <ID>`
3. Sprawdź logi klienta w `client/logs/` dla szczegółowych informacji o błędach
