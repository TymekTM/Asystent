"""
Dependency Manager - Automatyczne pobieranie brakujących pakietów Python
Pobiera tylko te pakiety, które nie są dostępne w systemowym Python
"""

import os
import sys
import subprocess
import logging
import json
import shutil
from pathlib import Path
import time
from typing import List, Dict, Optional

# Podstawowe importy które muszą być dostępne
try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

class DependencyManager:
    """Zarządza automatyczną instalacją brakujących pakietów Python."""
    
    def __init__(self):
        # Określ ścieżkę aplikacji
        if getattr(sys, 'frozen', False):
            # Aplikacja uruchomiona z PyInstaller
            self.app_dir = Path(os.path.dirname(sys.executable))
        else:
            # Aplikacja uruchomiona z Pythona
            self.app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        
        self.deps_dir = self.app_dir / "dependencies"
        self.packages_dir = self.deps_dir / "packages"
        self.cache_dir = self.deps_dir / "cache"
        self.lock_file = self.deps_dir / "installation.lock"
        self.config_file = self.deps_dir / "deps_config.json"
          def is_initialized(self) -> bool:
        """Sprawdza czy zależności zostały już sprawdzone/zainstalowane."""
        return self.lock_file.exists()
        
    def check_missing_packages(self) -> List[str]:
        """Sprawdza które pakiety brakują - tylko te które nie są wbudowane w EXE."""
        # Minimalna lista - tylko to co jest absolutnie potrzebne i nie może być wbudowane
        required_packages = [
            # Audio processing (duże, nie da się wbudować)
            "sounddevice",
            "faster_whisper", 
            "openwakeword",
            
            # ML/AI (za duże do wbudowania)
            "torch",
            "huggingface_hub",
            "transformers",
            "scipy",
            "sklearn",
            
            # Specjalistyczne
            "deepseek",
            "whisper",
        ]
        
        missing = []
        logger.info("Sprawdzanie pakietów w folderze dependencies i systemie...")
        
        for package in required_packages:
            # Najpierw sprawdź czy pakiet jest już w folderze dependencies
            if self._package_exists_in_deps(package):
                logger.info(f"   ✅ {package} (dependencies)")
                continue
                
            # Jeśli nie ma w dependencies, sprawdź systemowy import
            try:
                __import__(package)
                logger.info(f"   ✅ {package} (system)")
            except ImportError:
                missing.append(package)
                logger.warning(f"   ❌ {package} (brak)")
        
        return missing
      def _package_exists_in_deps(self, package_name: str) -> bool:
        """Sprawdza czy pakiet już istnieje w folderze dependencies."""
        if not self.packages_dir.exists():
            return False
            
        # Rozszerzone mapowanie nazw pakietów na foldery/pliki
        package_folders = {
            "sklearn": ["sklearn", "scikit_learn"],
            "PIL": ["PIL", "Pillow"],
            "bs4": ["bs4", "beautifulsoup4"],
            "flask_httpauth": ["flask_httpauth", "Flask_HTTPAuth"],
            "flask_limiter": ["flask_limiter", "Flask_Limiter"],
            "python_dotenv": ["dotenv", "python_dotenv"],
            "faster_whisper": ["faster_whisper"],
            "edge_tts": ["edge_tts"],
            "huggingface_hub": ["huggingface_hub"],
            "torch": ["torch"],
            "transformers": ["transformers"],
            "scipy": ["scipy"],
            "sounddevice": ["sounddevice", "_sounddevice"],
            "openwakeword": ["openwakeword"],
            "deepseek": ["deepseek"],
            "whisper": ["whisper"],
        }
        
        # Sprawdź wszystkie możliwe nazwy folderów dla pakietu
        possible_names = package_folders.get(package_name, [package_name])
        
        for folder_name in possible_names:
            # Sprawdź czy folder pakietu istnieje
            package_path = self.packages_dir / folder_name
            if package_path.exists() and (package_path.is_dir() or package_path.is_file()):
                logger.debug(f"Znaleziono pakiet {package_name} jako {folder_name}")
                return True
                
            # Sprawdź czy jest plik .py z nazwą pakietu  
            py_file = self.packages_dir / f"{folder_name}.py"
            if py_file.exists():
                logger.debug(f"Znaleziono pakiet {package_name} jako {folder_name}.py")
                return True
        
        return False

    def install_missing_packages(self, missing_packages: List[str]) -> bool:
        """Instaluje brakujące pakiety do folderu dependencies."""
        if not missing_packages:
            logger.info("Brak pakietów do instalacji")
            return True
            
        try:
            # Utwórz foldery
            self.deps_dir.mkdir(exist_ok=True)
            self.packages_dir.mkdir(exist_ok=True)
            self.cache_dir.mkdir(exist_ok=True)
            
            logger.info(f"📦 Instalowanie {len(missing_packages)} brakujących pakietów...")
            print(f"📦 Instalowanie {len(missing_packages)} brakujących pakietów...")
            
            # Wybierz interpreter pip: w trybie frozen użyj launchera py, inaczej sys.executable
            if getattr(sys, 'frozen', False):
                pip_exec = shutil.which('py') or shutil.which('python') or sys.executable
            else:
                pip_exec = sys.executable
              # Mapa nazw importów na nazwy pakietów pip
            package_map = {
                # Flask extensions
                "flask_httpauth": "Flask-HTTPAuth",
                "flask_limiter": "Flask-Limiter",
                
                # Data science
                "sklearn": "scikit-learn",
                "PIL": "Pillow",
                "bs4": "beautifulsoup4",
                
                # Audio packages
                "faster_whisper": "faster-whisper",
                "edge_tts": "edge-tts",
                
                # AI packages
                "huggingface_hub": "huggingface-hub",
                
            # Utilities
            "python_dotenv": "python-dotenv",
            # ASR
            "whisper": "openai-whisper"
            }
            
            # Specjalne przypadki instalacji (np. torch z CUDA)
            special_packages = {
                "torch": {
                    "command": [
                        pip_exec, "-3", "-m", "pip", "install",
                        "torch==2.1.2+cu118",
                        "--extra-index-url", "https://download.pytorch.org/whl/cu118",
                        "--target", str(self.packages_dir),
                        "--cache-dir", str(self.cache_dir),
                        "--no-warn-script-location"
                    ]
                }
            }
              success_count = 0
            for package in missing_packages:
                logger.info(f"📥 Instalowanie {package}...")
                print(f"   📥 Instalowanie {package}...")
                
                # Sprawdź czy to specjalny przypadek
                if package in special_packages:
                    # Try GPU-specific build first
                    cmd = special_packages[package]["command"]
                else:
                    pip_name = package_map.get(package, package)
                    cmd = [
                        pip_exec, "-m", "pip", "install",
                        pip_name,
                        "--target", str(self.packages_dir),
                        "--cache-dir", str(self.cache_dir),
                        "--no-warn-script-location"
                    ]
                
                try:
                    # Lepsze zarządzanie encoding dla subprocess
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True, 
                        timeout=300,
                        encoding='utf-8',
                        errors='replace',
                        env=dict(os.environ, PYTHONIOENCODING='utf-8')
                    )
                    # Fallback dla torch: gdy cu118 nie znajdzie wersji, spróbuj CPU-only
                    if package == 'torch' and result.returncode != 0:
                        logger.warning("⚠️ Nie udało się zainstalować torch z cu118, próbuję wersję CPU-only")
                        print("   ⚠️ Nie udało się zainstalować torch z cu118, próbuję wersję CPU-only")
                        cmd = [pip_exec, "-m", "pip", "install", "torch",
                               "--target", str(self.packages_dir),
                               "--cache-dir", str(self.cache_dir),
                               "--no-warn-script-location"]
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=300,
                            encoding='utf-8',
                            errors='replace',
                            env=dict(os.environ, PYTHONIOENCODING='utf-8')
                        )
                      if result.returncode == 0:
                        logger.info(f"✅ {package} - pomyślnie zainstalowano")
                        print(f"   ✅ {package}")
                        success_count += 1
                    else:
                        error_msg = result.stderr[:100] if result.stderr else "Nieznany błąd"
                        logger.error(f"❌ {package}: {error_msg}")
                        print(f"   ❌ {package}: {error_msg}...")
                        
                except subprocess.TimeoutExpired:
                    logger.error(f"⏰ Timeout podczas instalacji: {package}")
                    print(f"   ⏰ Timeout: {package}")
                except Exception as e:
                    logger.error(f"❌ Błąd instalacji {package}: {e}")
                    print(f"   ❌ Błąd: {package}: {e}")
            
            logger.info(f"📊 Zainstalowano: {success_count}/{len(missing_packages)}")
            print(f"📊 Zainstalowano: {success_count}/{len(missing_packages)}")
            return success_count > 0  # Sukces jeśli przynajmniej jeden pakiet się zainstalował
              except Exception as e:
            logger.error(f"Błąd instalacji pakietów: {e}")
            print(f"❌ Błąd instalacji: {e}")
            return False
    
    def setup_environment(self):
        """Konfiguruje ścieżki do zainstalowanych pakietów."""
        if self.packages_dir.exists():
            # Dodaj ścieżkę do pakietów na końcu sys.path (aby nie nadpisać stdlib)
            packages_path = str(self.packages_dir)
            if packages_path not in sys.path:
                sys.path.append(packages_path)
                print(f"   📁 Dodano ścieżkę: {packages_path}")
    
    def _create_lock_file(self, installed_packages: List[str]):
        """Tworzy plik lock oznaczający zakończenie sprawdzania."""
        config = {
            "check_date": str(int(time.time())),
            "version": "2.0.0",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "installed_packages": installed_packages,
            "status": "complete"
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass
        
        self.lock_file.touch()
    
    def get_installation_status(self) -> Dict:
        """Zwraca status instalacji pakietów."""
        if not self.is_initialized():
            return {"status": "not_checked"}
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except:
            return {"status": "unknown"}


def ensure_dependencies():
    """Główna funkcja sprawdzająca i instalująca brakujące pakiety."""
    # Zawsze sprawdzaj i instaluj brakujące pakiety przy każdym uruchomieniu
    manager = DependencyManager()
    print("\n" + "="*60)
    print("🔍 SPRAWDZANIE ZALEŻNOŚCI APLIKACJI")
    print("="*60)
    # Pierwsze sprawdzenie zależności
    if not manager.is_initialized():
        # Pierwsze sprawdzenie i instalacja brakujących pakietów
        print("📋 Sprawdzanie dostępności wymaganych pakietów...")
        missing = manager.check_missing_packages()
        if missing:
            print(f"\n❌ Brakuje {len(missing)} pakietów")
            print("📥 Automatyczne pobieranie brakujących pakietów...")
            manager.install_missing_packages(missing)
        else:
            print(f"\n✅ Wszystkie pakiety dostępne!")
        # Utwórz plik blokady z listą zainstalowanych pakietów
        manager._create_lock_file(missing)
    else:
        # Kolejne uruchomienie - sprawdź, czy są nowe brakujące pakiety
        print("\n🔄 Sprawdzanie aktualizacji zależności...")
        missing = manager.check_missing_packages()
        if missing:
            print(f"\n❌ Nowe brakujące pakiety: {len(missing)}")
            print("📥 Instalowanie nowych pakietów...")
            manager.install_missing_packages(missing)
            # Zaktualizuj lockfile z nowymi pakietami
            status = manager.get_installation_status()
            prev = status.get('installed_packages', [])
            manager._create_lock_file(prev + missing)
        else:
            print("\n✅ Zależności są aktualne, pomijanie instalacji.")
    print("\n" + "="*60)
    print("🚀 URUCHAMIANIE APLIKACJI")
    print("="*60 + "\n")
    # Konfiguruj środowisko (dodaj ścieżki do zainstalowanych pakietów)
    manager.setup_environment()
    return True


if __name__ == "__main__":
    ensure_dependencies()
