"""
process_manager.py - Bezpieczne zarządzanie procesami zewnętrznymi
"""

import os
import sys
import logging
import subprocess
import time
import platform
from pathlib import Path
from typing import Optional, Dict, Any
import psutil

logger = logging.getLogger(__name__)

class ProcessManager:
    """Bezpieczne zarządzanie procesami zewnętrznymi."""
    
    def __init__(self):
        self.running_processes: Dict[str, subprocess.Popen] = {}
        self.process_configs: Dict[str, Dict[str, Any]] = {}
    
    def register_process_config(self, name: str, config: Dict[str, Any]):
        """
        Rejestruje konfigurację procesu.
        
        Args:
            name: Nazwa procesu
            config: Konfiguracja zawierająca executable_path, args, working_dir, etc.
        """
        self.process_configs[name] = config
    
    def start_process(self, name: str, **kwargs) -> Optional[subprocess.Popen]:
        """
        Uruchamia proces z walidacją bezpieczeństwa.
        
        Args:
            name: Nazwa procesu
            **kwargs: Dodatkowe argumenty nadpisujące konfigurację
            
        Returns:
            Obiekt procesu lub None w przypadku błędu
        """
        if name not in self.process_configs:
            logger.error(f"Process configuration not found: {name}")
            return None
        
        config = self.process_configs[name].copy()
        config.update(kwargs)
        
        executable_path = Path(config.get('executable_path', ''))
        
        # Walidacja ścieżki pliku
        if not self._validate_executable_path(executable_path):
            logger.error(f"Invalid or unsafe executable path: {executable_path}")
            return None
        
        try:
            # Przygotuj argumenty procesu
            args = [str(executable_path)]
            if config.get('args'):
                args.extend(config['args'])
            
            # Przygotuj środowisko
            env = os.environ.copy()
            if config.get('environment'):
                env.update(config['environment'])
            
            # Przygotuj opcje uruchomienia
            process_kwargs = {
                'args': args,
                'cwd': config.get('working_dir', executable_path.parent),
                'env': env,
                'stdout': subprocess.PIPE if config.get('capture_output') else None,
                'stderr': subprocess.PIPE if config.get('capture_output') else None,
            }
            
            # Dodaj flagi specyficzne dla Windows
            if platform.system() == "Windows":
                if config.get('no_window', True):
                    process_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                if config.get('detached', False):
                    process_kwargs['creationflags'] = getattr(process_kwargs, 'creationflags', 0) | subprocess.DETACHED_PROCESS
            
            # Uruchom proces
            process = subprocess.Popen(**process_kwargs)
            
            # Sprawdź czy proces wystartował prawidłowo
            if self._validate_process_startup(process, name):
                self.running_processes[name] = process
                logger.info(f"Successfully started process '{name}' (PID: {process.pid})")
                return process
            else:
                logger.error(f"Process '{name}' failed to start properly")
                return None
                
        except Exception as e:
            logger.error(f"Failed to start process '{name}': {e}")
            return None
    
    def stop_process(self, name: str, timeout: int = 5, force: bool = False) -> bool:
        """
        Zatrzymuje proces w bezpieczny sposób.
        
        Args:
            name: Nazwa procesu
            timeout: Czas oczekiwania na graceful shutdown
            force: Czy wymusić zamknięcie jeśli graceful nie zadziała
            
        Returns:
            True jeśli proces został zatrzymany, False w przeciwnym razie
        """
        if name not in self.running_processes:
            logger.warning(f"Process '{name}' not found in running processes")
            return True
        
        process = self.running_processes[name]
        
        try:
            if process.poll() is not None:
                # Proces już zakończony
                del self.running_processes[name]
                logger.info(f"Process '{name}' was already terminated")
                return True
            
            logger.info(f"Stopping process '{name}' (PID: {process.pid})")
            
            # Najpierw spróbuj graceful shutdown
            process.terminate()
            
            try:
                process.wait(timeout=timeout)
                logger.info(f"Process '{name}' terminated gracefully")
            except subprocess.TimeoutExpired:
                if force:
                    logger.warning(f"Process '{name}' did not terminate gracefully, forcing kill")
                    
                    # Na Windows użyj taskkill jeśli dostępne
                    if platform.system() == "Windows":
                        try:
                            subprocess.run(
                                ["taskkill", "/PID", str(process.pid), "/F"],
                                capture_output=True,
                                timeout=5
                            )
                            time.sleep(1)  # Daj czas na zakończenie
                        except (subprocess.TimeoutExpired, FileNotFoundError):
                            pass
                    
                    # Fallback - kill przez Python
                    try:
                        process.kill()
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        logger.error(f"Failed to force kill process '{name}'")
                        return False
                    
                    logger.info(f"Process '{name}' force killed")
                else:
                    logger.error(f"Process '{name}' did not terminate within timeout and force=False")
                    return False
            
            del self.running_processes[name]
            return True
            
        except Exception as e:
            logger.error(f"Error stopping process '{name}': {e}")
            return False
    
    def stop_all_processes(self, timeout: int = 5):
        """Zatrzymuje wszystkie zarządzane procesy."""
        logger.info("Stopping all managed processes")
        
        for name in list(self.running_processes.keys()):
            self.stop_process(name, timeout=timeout, force=True)
    
    def get_process_status(self, name: str) -> Dict[str, Any]:
        """
        Zwraca status procesu.
        
        Args:
            name: Nazwa procesu
            
        Returns:
            Słownik z informacjami o statusie
        """
        if name not in self.running_processes:
            return {"status": "not_running", "pid": None}
        
        process = self.running_processes[name]
        
        try:
            if process.poll() is None:
                # Proces nadal działa
                try:
                    ps_process = psutil.Process(process.pid)
                    return {
                        "status": "running",
                        "pid": process.pid,
                        "memory_mb": ps_process.memory_info().rss / 1024 / 1024,
                        "cpu_percent": ps_process.cpu_percent(),
                        "create_time": ps_process.create_time()
                    }
                except psutil.NoSuchProcess:
                    del self.running_processes[name]
                    return {"status": "terminated", "pid": process.pid}
            else:
                # Proces zakończony
                del self.running_processes[name]
                return {"status": "terminated", "pid": process.pid, "return_code": process.returncode}
                
        except Exception as e:
            logger.error(f"Error getting status for process '{name}': {e}")
            return {"status": "error", "error": str(e)}
    
    def _validate_executable_path(self, path: Path) -> bool:
        """Waliduje ścieżkę do pliku wykonywalnego."""
        try:
            # Sprawdź czy plik istnieje
            if not path.exists():
                return False
            
            # Sprawdź czy to jest plik
            if not path.is_file():
                return False
            
            # Sprawdź uprawnienia do odczytu
            if not os.access(path, os.R_OK):
                return False
            
            # Sprawdź czy ścieżka nie zawiera niebezpiecznych sekwencji
            resolved_path = path.resolve()
            path_str = str(resolved_path)
            
            # Zapobiegaj path traversal
            if '..' in path_str or path_str.startswith('/tmp') or path_str.startswith('\\temp'):
                return False
            
            # Na Windows sprawdź rozszerzenie
            if platform.system() == "Windows":
                if not path.suffix.lower() in ['.exe', '.bat', '.cmd']:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating executable path {path}: {e}")
            return False
    
    def _validate_process_startup(self, process: subprocess.Popen, name: str) -> bool:
        """Waliduje czy proces uruchomił się prawidłowo."""
        try:
            # Sprawdź czy proces nie zakończył się natychmiast
            time.sleep(0.1)  # Krótkie oczekiwanie
            
            if process.poll() is not None:
                logger.error(f"Process '{name}' terminated immediately with code {process.returncode}")
                return False
            
            # Sprawdź czy PID jest prawidłowy
            if process.pid <= 0:
                logger.error(f"Process '{name}' has invalid PID: {process.pid}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating process startup for '{name}': {e}")
            return False

# Globalna instancja menedżera procesów
process_manager = ProcessManager()
