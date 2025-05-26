# Budowanie aplikacji Gaja - Instrukcja

## Przegląd

System automatycznie tworzy pojedynczy plik EXE, który przy pierwszym uruchomieniu pobiera wszystkie potrzebne zależności. Użytkownik musi pobrać tylko jeden plik - `Gaja.exe`.

## Jak zbudować aplikację

### Krok 1: Przygotowanie środowiska

```powershell
# Zainstaluj podstawowe zależności do kompilacji
pip install -r requirements_build.txt
```

### Krok 2: Budowanie (Automatyczny)

```powershell
# Uruchom skrypt build (wszystko robi automatycznie)
python build.py
```

### Krok 3: Budowanie (Ręczne)

```powershell
# Wyczyść poprzednie build
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

# Skompiluj do pojedynczego EXE
pyinstaller --clean gaja.spec

# Sprawdź wynik
ls dist/
```

## Jak działa system

### 1. Kompilacja
- PyInstaller tworzy **pojedynczy plik EXE** (~50-100MB)
- EXE zawiera tylko podstawowy kod aplikacji + dependency_manager
- Duże biblioteki (numpy, pandas, AI modele) są wykluczone z kompilacji

### 2. Pierwsze uruchomienie
Gdy użytkownik po raz pierwszy uruchamia `Gaja.exe`:

1. **Sprawdzenie zależności**: Aplikacja sprawdza czy folder `dependencies/` istnieje
2. **Pobieranie Python**: Automatyczne pobranie Python 3.11 Embedded (~15MB)
3. **Instalacja pip**: Automatyczna instalacja pip
4. **Pakiety Python**: Pobieranie i instalacja kluczowych pakietów (~200MB)
5. **Znacznik ukończenia**: Utworzenie pliku `installation.lock`

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
