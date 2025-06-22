# Budowanie aplikacji Gaja - Architektura Client (EXE) + Server (Docker)

## Przegląd

System został zaprojektowany zgodnie z nowoczesnymi praktykami DevOps:

- **Client**: Budowany jako lekki EXE (~50-80 MB), ciężkie zależności ML pobierane przy pierwszym uruchomieniu
- **Server**: Uruchamiany jako Docker container dla łatwego deployment i zarządzania
- **Dependency Manager**: Automatyczne pobieranie ciężkich pakietów ML (torch, whisper, etc.) do folderu aplikacji

## Jak działa system zależności

### Lekki EXE + Runtime Dependencies
Klient jest budowany jako lekki EXE zawierający tylko podstawowe zależności:
- WebSocket komunikacja
- GUI (tkinter) 
- Podstawowe utilities
- **Dependency Manager**

Ciężkie zależności ML (~800 MB) są pobierane przy pierwszym uruchomieniu:
- torch, torchaudio (~800 MB)
- whisper, faster-whisper (~200 MB)
- sounddevice, librosa (~100 MB)
- openwakeword (~100 MB)

### Pierwsze uruchomienie klienta
```
🚀 GAJA Assistant Client
========================================
🔧 First run detected - downloading required dependencies...
   This may take a few minutes depending on your internet connection.
   The application will be much faster on subsequent runs.

[DEPENDENCY] Installing torch (PyTorch machine learning framework)...
✅ torch installed successfully
[DEPENDENCY] Installing sounddevice (Audio device access)...
✅ sounddevice installed successfully
...
✅ All dependencies installed successfully!
```

## Szybki start

### 1. Zbuduj klienta (EXE)

```powershell
# Zbuduj klienta jako EXE
python build.py
```

### 2. Uruchom serwer (Docker)

```powershell
# Uruchom serwer w Docker
docker-compose up gaja-server-cpu
```

### 3. Uruchom klienta

```powershell
# Uruchom klienta (połączy się z serwerem)
dist\GajaClient.exe
```

## Szczegółowe opcje budowania

### Budowanie klienta

```powershell
# Domyślnie buduje klienta
python build.py

# Explicite budowanie klienta
python build.py --component client

# Pomiń budowanie Rust overlay
python build.py --skip-overlay

# Pomiń weryfikację architektury
python build.py --skip-verification
```

### Zarządzanie serwerem (Docker)

```powershell
# Zbuduj obraz Docker serwera
docker-compose build gaja-server-cpu

# Uruchom serwer w tle
docker-compose up -d gaja-server-cpu

# Zobacz logi serwera
docker-compose logs -f gaja-server-cpu

# Zatrzymaj serwer
docker-compose down

# Przebuduj i uruchom ponownie
docker-compose build gaja-server-cpu && docker-compose up -d gaja-server-cpu
```

### Legacy (opcjonalnie)

```powershell
# Zbuduj stary system unified (zawiera klienta i serwer w jednym EXE)
python build.py --component legacy
```

## Przygotowanie środowiska

### Wymagania dla klienta (EXE)

```powershell
# Zainstaluj zależności do budowania klienta
pip install -r client/requirements_client.txt
pip install pyinstaller
```

### Wymagania dla serwera (Docker)

```powershell
# Wymagany Docker i docker-compose
docker --version
docker-compose --version
```

## Wyniki budowania

Po udanym procesie otrzymasz:

```
dist/
├── GajaClient.exe    # Lekki klient (~50-80 MB) + dependency manager
└── Gaja.exe          # Legacy unified (jeśli budowane) - ~200-350 MB

Po pierwszym uruchomieniu klienta:
dependencies/         # Ciężkie zależności ML (~800 MB)
├── torch/
├── whisper/
├── sounddevice/
├── librosa/
└── manifest.json     # Lista zainstalowanych pakietów

docker images:
├── gaja-server-cpu   # Serwer (FastAPI + AI + Database)
```

## Architektura systemu

### Client (GajaClient.exe)
- **Rozmiar EXE**: ~50-80 MB (lekki build)
- **Runtime dependencies**: ~800 MB (pobierane automatycznie)
- **Funkcjonalności**: Audio processing, wake-word detection, GUI overlay, WebSocket communication
- **Folder aplikacji**: 
  - `dependencies/` - Ciężkie pakiety ML
  - `logs/` - Logi klienta
  - `config/` - Konfiguracja klienta
- **Połączenie**: ws://localhost:8001/ws/{user_id}
- **Dystrybucja**: Pojedynczy plik EXE do pobrania przez użytkowników

### Server (Docker)
- **Funkcjonalności**: FastAPI API, AI processing (OpenAI/Anthropic/Ollama), SQLite database, plugin system
- **Porty**: 8001 (API), 8080 (Web UI)
- **Volumes**: Persistence dla danych, cache, logs
- **Zarządzanie**: Docker Compose z resource management

## Zadania VS Code

Dostępne zadania w VS Code (Ctrl+Shift+P → "Tasks: Run Task"):

### Build Tasks
- **Build Client EXE** - Zbuduj klienta jako EXE
- **Build Legacy EXE** - Zbuduj legacy unified EXE
- **Build EXE** - Alias dla "Build Client EXE"

### Docker Tasks  
- **Docker: Build Server** - Zbuduj obraz Docker serwera
- **Docker: Start Server** - Uruchom serwer w tle
- **Docker: Stop Server** - Zatrzymaj serwer
- **Docker: Server Logs** - Zobacz logi serwera w czasie rzeczywistym

## Deployment

### Dystrybucja klienta
1. Zbuduj: `python build.py`
2. Udostępnij: `dist/GajaClient.exe` (pojedynczy plik)
3. Instrukcja dla użytkowników: "Pobierz i uruchom GajaClient.exe"

### Deployment serwera
1. Na serwerze produkcyjnym:
```bash
# Sklonuj repozytorium
git clone <repo>
cd Asystent

# Skonfiguruj zmienne środowiskowe
cp .env.example .env
# Edytuj .env z production settings

# Uruchom serwer
docker-compose up -d gaja-server-cpu

# Sprawdź status
docker-compose ps
docker-compose logs gaja-server-cpu
```

2. Konfiguracja nginx (opcjonalnie):
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## Rozwiązywanie problemów

### Problemy z buildem klienta
```powershell
# Sprawdź czy PyInstaller jest dostępny
python -c "import PyInstaller; print(PyInstaller.__version__)"

# Sprawdź zależności audio
python -c "import sounddevice; print('Audio OK')"

# Verbose build
python -m PyInstaller --clean --log-level DEBUG gaja_client.spec
```

### Problemy z Docker serverem
```powershell
# Sprawdź Docker
docker --version
docker-compose --version

# Sprawdź logi
docker-compose logs gaja-server-cpu

# Przebuduj od zera
docker-compose down
docker-compose build --no-cache gaja-server-cpu
docker-compose up -d gaja-server-cpu
```

### Problemy z połączeniem
- Sprawdź czy serwer działa: `curl http://localhost:8001/health`
- Sprawdź porty: `netstat -an | findstr 8001`
- Sprawdź logi klienta i serwera

## Migracja z poprzedniej wersji

### Ze starego systemu unified
1. **Zachowaj dane**: Skopiuj `data/` i `config/`
2. **Zbuduj nowy klient**: `python build.py`
3. **Uruchom serwer w Docker**: `docker-compose up gaja-server-cpu`
4. **Przetestuj**: Uruchom `GajaClient.exe`

### Konfiguracja
- **Serwer**: `server/server_config.json` → Docker volumes
- **Klient**: `client/client_config.json` → lokalnie w folderze klienta

## Performance & Monitoring

### Metryki serwera
- Resource usage: `docker stats gaja-server-cpu`
- API health: `curl http://localhost:8001/health`
- Database size: `du -sh data/server_data.db`

### Metryki klienta
- Połączenie z serwerem sprawdzane automatycznie
- Logi klienta w lokalnym folderze `logs/`

## Bezpieczeństwo

### Serwer (Production)
- Zmień `GAJA_SECRET_KEY` w `.env`
- Skonfiguruj `CORS_ORIGINS`
- Użyj reverse proxy (nginx)
- Regularnie aktualizuj obraz Docker

### Klient
- Połączenie tylko z zaufanymi serwerami
- Dane audio przetwarzane lokalnie
- Brak wysyłania wrażliwych danych bez zgody

## Status implementacji

✅ **Ukończone**:
- Build klienta jako EXE
- Docker server z docker-compose
- Zadania VS Code dla obu architektur  
- Dokumentacja deployment
- Weryfikacja architektury
- Resource management w Docker

🔄 **W trakcie**:
- Optymalizacja rozmiaru EXE klienta
- Monitoring i health checks

📋 **Planowane**:
- Automated builds (CI/CD)
- Multi-platform Docker images
- Client auto-update mechanism

### 3. Kolejne uruchomienia
- Sprawdzenie pliku `installation.lock`
- Konfiguracja ścieżek do zainstalowanych pakietów
- Normalne uruchomienie aplikacji

## Struktura plików po instalacji

```
Gaja.exe                     # Główna aplikacja (50-100MB)
dependencies/                # Folder zależności (tworzy się automatycznie)
├── python/                  # Python 3.11 Embedded
│   ├── python.exe
│   ├── python311.dll
│   └── ...
├── packages/                # Pakiety Python (Flask, OpenAI, etc.)
│   ├── flask/
│   ├── openai/
│   └── ...
├── models/                  # Modele AI (przyszłe)
├── installation.lock        # Znacznik ukończonej instalacji
└── deps_config.json        # Konfiguracja instalacji
```

## Zalety tego podejścia

✅ **Pojedynczy plik do dystrybucji** - użytkownik pobiera tylko EXE
✅ **Szybkie pobieranie** - mały rozmiar początkowy (~50-100MB vs ~2GB)
✅ **Automatyczna instalacja** - zero konfiguracji dla użytkownika
✅ **Elastyczność** - można dodawać pakiety bez rekompilacji
✅ **Szybkie kolejne uruchomienia** - zależności już zainstalowane

## Opcje konfiguracji

### W pliku `dependency_manager.py`:

```python
# Zmień listę pakietów do instalacji
essential_packages = [
    "flask==3.1.0",
    "requests==2.31.0",
    # Dodaj więcej...
]

# Zmień wersję Python Embedded
self.python_embedded_url = "https://www.python.org/ftp/python/3.12.0/python-3.12.0-embed-amd64.zip"
```

### W pliku `gaja.spec`:

```python
# Dodaj pakiety do wykluczenia z kompilacji
excludes=[
    'tensorflow',      # Duże biblioteki ML
    'torch',          # PyTorch
    'numpy',          # Będzie pobrane później
    # Dodaj więcej...
]
```

## Rozwiązywanie problemów

### Problem: Błąd kompilacji PyInstaller
```bash
# Sprawdź logi
pyinstaller --clean --debug all gaja.spec
```

### Problem: Błąd podczas pobierania zależności
```python
# W dependency_manager.py zwiększ timeout
subprocess.run(cmd, timeout=300)  # 5 minut
```

### Problem: Brakujące pakiety po instalacji
```python
# Dodaj pakiet do essential_packages w dependency_manager.py
essential_packages = [
    "flask==3.1.0",
    "your-package==1.0.0"  # Dodaj tutaj
]
```

## Testowanie

### Test kompilacji:
```powershell
python build.py
```

### Test pierwszego uruchomienia:
```powershell
# Usuń folder dependencies (symuluje pierwsze uruchomienie)
Remove-Item -Recurse -Force dependencies -ErrorAction SilentlyContinue

# Uruchom EXE
.\dist\Gaja.exe
```

### Test kolejnego uruchomienia:
```powershell
# Uruchom ponownie (dependencies już istnieją)
.\dist\Gaja.exe
```

## Dystrybucja

Po udanej kompilacji:

1. **Plik do dystrybucji**: `dist/Gaja.exe`
2. **Rozmiar**: ~50-100MB (pojedynczy plik)
3. **Wymagania**: Windows 10+, połączenie internetowe (pierwsze uruchomienie)
4. **Instalacja**: Nie wymagana - tylko pobranie i uruchomienie EXE

## Wersjonowanie

Każda kompilacja zawiera:
- Wersję w `deps_config.json`
- Timestamp instalacji
- Listę zainstalowanych pakietów

To pozwala na tracking i debug problemów.
