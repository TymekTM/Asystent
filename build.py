"""
Skrypt do budowania pojedynczego pliku EXE z automatycznym pobieraniem zależności
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_build():
    """Czyści poprzednie pliki build"""
    print("🧹 Czyszczenie poprzednich build...")
    
    paths_to_remove = ['build', 'dist', '__pycache__']
    
    for path in paths_to_remove:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"   Usunięto folder: {path}")
            else:
                os.remove(path)
                print(f"   Usunięto plik: {path}")

def install_build_dependencies():
    """Instaluje pakiety potrzebne do kompilacji"""
    print("📦 Instalowanie zależności do kompilacji...")
    
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "requirements_build.txt"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Błąd instalacji zależności: {result.stderr}")
        return False
    
    print("✅ Zależności zainstalowane")
    return True

def build_overlay():
    """Buduje overlay Tauri"""
    print("🖼️ Budowanie overlay...")
    
    overlay_dir = Path("overlay")
    if not overlay_dir.exists():
        print("⚠️ Folder overlay nie istnieje, pomijam budowanie overlay")
        return True
    
    # Sprawdź czy overlay.exe już istnieje
    overlay_exe = overlay_dir / "target" / "release" / "Asystent Overlay.exe"
    if overlay_exe.exists():
        print(f"✅ Overlay już zbudowany: {overlay_exe}")
        return True
    
    # Instaluj npm dependencies
    print("   📦 Instalowanie npm dependencies...")
    result = subprocess.run([
        "npm", "install"
    ], cwd=overlay_dir, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"⚠️ Ostrzeżenie npm install: {result.stderr}")
    
    # Buduj overlay
    print("   🔨 Kompilowanie overlay...")
    result = subprocess.run([
        "npm", "run", "tauri", "build"
    ], cwd=overlay_dir, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Błąd kompilacji overlay: {result.stderr}")
        return False
    
    # Sprawdź czy plik został utworzony
    if overlay_exe.exists():
        size_mb = overlay_exe.stat().st_size / (1024 * 1024)
        print(f"✅ Overlay zbudowany: {overlay_exe}")
        print(f"📏 Rozmiar overlay: {size_mb:.1f} MB")
        return True
    else:
        print("❌ Plik overlay.exe nie został utworzony")
        return False

def build_exe():
    """Buduje pojedynczy plik EXE"""
    print("🔨 Budowanie pliku EXE...")
    
    # Uruchom PyInstaller
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller", 
        "--clean",
        "gaja.spec"
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Błąd kompilacji: {result.stderr}")
        return False
    
    # Sprawdź czy plik został utworzony
    exe_path = Path("dist/Gaja.exe")
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"✅ EXE utworzony: {exe_path}")
        print(f"📏 Rozmiar: {size_mb:.1f} MB")
        return True
    else:
        print("❌ Plik EXE nie został utworzony")
        return False

def create_release_package():
    """Tworzy pakiet release z instrukcjami"""
    print("📦 Tworzenie pakietu release...")
    
    release_dir = Path("release")
    release_dir.mkdir(exist_ok=True)
    
    # Skopiuj EXE
    exe_source = Path("dist/Gaja.exe")
    exe_dest = release_dir / "Gaja.exe"
    
    if exe_source.exists():
        shutil.copy2(exe_source, exe_dest)
        print(f"   Skopiowano: {exe_dest}")
      # Skopiuj overlay jeśli istnieje
    overlay_source = Path("overlay/target/release/Asystent Overlay.exe")
    overlay_dest = release_dir / "overlay" / "Asystent Overlay.exe"
    
    if overlay_source.exists():
        overlay_dest.parent.mkdir(exist_ok=True)
        shutil.copy2(overlay_source, overlay_dest)
        print(f"   Skopiowano: {overlay_dest}")
    else:
        print("⚠️ Overlay nie został znaleziony, aplikacja będzie działać bez overlay")
    
    # Utwórz README dla użytkownika
    readme_content = """# Gaja - Asystent AI

## Instalacja i pierwsze uruchomienie

1. **Pobierz**: Gaja.exe (ten plik)
2. **Uruchom**: Kliknij dwukrotnie na Gaja.exe
3. **Poczekaj**: Przy pierwszym uruchomieniu aplikacja sprawdzi dostępne pakiety Python
4. **Automatyczne doinstalowanie**: Jeśli brakuje pakietów, zostaną pobrane do folderu `dependencies`
5. **Gotowe**: Aplikacja uruchomi się automatycznie

## Jak to działa

- **EXE zawiera**: Podstawowe biblioteki (Flask, OpenAI, requests, etc.)
- **Automatyczne doinstalowanie**: Brakujące pakiety pobierają się do folderu `dependencies`
- **Pierwsze uruchomienie**: 1-3 minuty (sprawdzanie + ewentualne pobieranie)
- **Kolejne uruchomienia**: Szybkie (pakiety już dostępne)
- **Overlay**: Opcjonalny wizualny overlay pokazujący status asystenta

## Struktura plików po pierwszym uruchomieniu

```
Gaja.exe                     # Główna aplikacja
overlay/                     # Folder z overlay (opcjonalny)
├── Asystent Overlay.exe        # Wizualny overlay 
dependencies/                # Folder z dodatkowymi pakietami (tworzy się automatycznie)
├── packages/               # Dodatkowe pakiety Python
├── cache/                  # Cache instalatora
├── installation.lock       # Znacznik sprawdzenia zależności
└── deps_config.json       # Konfiguracja pakietów
```

## Wymagania

- **System**: Windows 10+ (64-bit)
- **Python**: Systemowy Python 3.11+ (jeśli nie ma, aplikacja poprosi o instalację)
- **Połączenie internetowe**: Tylko przy pierwszym uruchomieniu (dla brakujących pakietów)
- **Miejsce na dysku**: ~100MB dla aplikacji + ~500MB dla dodatkowych pakietów

## Rozwiązywanie problemów

- **"Brak Pythona"**: Zainstaluj Python z python.org
- **Błąd pobierania pakietów**: Sprawdź połączenie internetowe
- **Aplikacja nie startuje**: Uruchom jako administrator
- **Błędy pakietów**: Usuń folder `dependencies` i uruchom ponownie

## Co robi aplikacja przy pierwszym uruchomieniu?

1. Sprawdza czy potrzebne pakiety są już zainstalowane w systemie
2. Jeśli brakuje pakietów - instaluje je do folderu `dependencies` obok EXE
3. Konfiguruje ścieżki do zainstalowanych pakietów
4. Uruchamia główną aplikację

Wersja: 2.1.0
Data: 2025
"""
    
    readme_path = release_dir / "README.md"
    readme_path.write_text(readme_content, encoding='utf-8')
    print(f"   Utworzono: {readme_path}")
    
    print(f"🎉 Pakiet release gotowy w folderze: {release_dir}")

def main():
    """Główna funkcja build"""
    print("🚀 Rozpoczynam budowanie aplikacji Gaja")
    print("=" * 50)
    
    try:
        # Krok 1: Czyszczenie
        clean_build()
        print()
        
        # Krok 2: Instalacja zależności
        if not install_build_dependencies():
            return False
        print()
        
        # Krok 3: Budowanie overlay
        if not build_overlay():
            print("⚠️ Overlay nie został zbudowany, kontynuuję bez overlay")
        print()
        
        # Krok 4: Kompilacja
        if not build_exe():
            return False
        print()
        
        # Krok 5: Pakiet release
        create_release_package()
        print()
        
        print("🎉 Build zakończony pomyślnie!")
        print("📁 Sprawdź folder 'release' - tam znajdziesz gotową aplikację")
        
        return True
        
    except Exception as e:
        print(f"❌ Nieoczekiwany błąd: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n❌ Build zakończony niepowodzeniem")
        sys.exit(1)
    else:
        print("\n✅ Build zakończony pomyślnie!")
        sys.exit(0)
