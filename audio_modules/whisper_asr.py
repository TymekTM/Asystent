from __future__ import annotations
import os, pathlib, logging, ctypes
from typing import List

# Optional imports for ML packages
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
    log = logging.getLogger(__name__)
    print("⚠️  torch nie jest dostępny - będzie automatycznie doinstalowany przy pierwszym użyciu")

# Placeholder for faster-whisper import after environment setup
WhisperModel = None
FASTER_WHISPER_AVAILABLE = False

from performance_monitor import measure_performance
import sys # Added for PyInstaller path correction

# ────────────────────────────────────────────────────────────────
# auto-download / konwersja modelu Whisper (faster-whisper)
# bez symlinków → działa na Windowsie
# próba GPU ↔ automatyczny fallback na CPU, jeśli brakuje cuBLAS
# ────────────────────────────────────────────────────────────────

# Determine if running in a PyInstaller bundle
IS_BUNDLED = getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

if IS_BUNDLED:
    # Correctly set paths for bundled faster_whisper and its dependencies
    # This assumes faster_whisper is vendored or included in the _internal directory
    # Adjust the path according to your PyInstaller spec file or bundling structure
    _extra_dll_dir = os.path.join(sys._MEIPASS, '_internal', 'faster_whisper')
    if os.path.isdir(_extra_dll_dir):
        if sys.platform == "win32":
            os.add_dll_directory(_extra_dll_dir)
        else:
            # For Linux/macOS, you might need to adjust LD_LIBRARY_PATH or DYLD_LIBRARY_PATH
            # before the application starts, or ensure rpaths are set correctly during compilation.
            # Alternatively, ensure the .so/.dylib files are in a standard search path or next to the executable.
            pass # No direct equivalent to os.add_dll_directory for non-Windows in Python runtime
    
    # If faster_whisper is vendored, ensure its path is in sys.path
    # This might be needed if it's not automatically discoverable
    vendored_fw_path = os.path.join(sys._MEIPASS, '_internal') # Example path
    if vendored_fw_path not in sys.path:
        sys.path.insert(0, vendored_fw_path)

# Now, attempt to import WhisperModel after adjusting paths
if FASTER_WHISPER_AVAILABLE:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        WhisperModel = None
        print("⚠️  Nie udało się zaimportować faster_whisper po bundle - będzie doinstalowany przy pierwszym użyciu")
else:
    WhisperModel = None


ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".hf_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

# ────────────────────────────────────────────────────────────────
# Logger – tylko warning i error, żeby nie blokować
# ────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)
log.setLevel(logging.WARNING)

def _ensure_cublas() -> bool:
    # if we've already created an alias, load it directly and skip rediscovery
    alias_file = ROOT / '.cuda_alias' / 'cublas64_12.dll'
    if alias_file.exists():
        os.environ["PATH"] = str(alias_file.parent) + os.pathsep + os.environ.get("PATH", "")
        try:
            ctypes.CDLL(str(alias_file))
            log.info(f"Found existing cuBLAS alias at {alias_file}")
            return True
        except OSError:
            log.warning(f"Failed to load existing alias {alias_file}, will check system PATH.")
            # Fall through to check system PATH

    try:
        ctypes.CDLL("cublas64_12.dll")
        log.info("cublas64_12.dll found in system PATH.")
        return True
    except OSError:
        log.warning("cublas64_12.dll not found in system PATH or alias.")
        if IS_BUNDLED:
            # Path 1: DLL directly in _MEIPASS (e.g., if _MEIPASS is the _internal dir, or for one-file builds where DLL is at root of extraction)
            path1 = os.path.join(sys._MEIPASS, 'cublas64_12.dll')
            
            # Path 2: DLL in an '_internal' subdirectory relative to the executable's directory
            # This is common for one-dir builds or if _internal is a folder next to the EXE.
            exe_dir = os.path.dirname(sys.executable)
            path2 = os.path.join(exe_dir, '_internal', 'cublas64_12.dll')

            dll_to_load = None
            tried_paths_log = []

            if os.path.exists(path1):
                dll_to_load = path1
                tried_paths_log.append(f"{path1} (exists)")
            else:
                tried_paths_log.append(f"{path1} (not found)")

            if not dll_to_load and os.path.exists(path2):
                dll_to_load = path2
                tried_paths_log.append(f"{path2} (exists)")
            elif not dll_to_load: # only add path2 to log if it wasn't chosen and path1 failed
                tried_paths_log.append(f"{path2} (not found)")

            if dll_to_load:
                try:
                    ctypes.CDLL(dll_to_load)
                    log.info(f"cublas64_12.dll loaded from PyInstaller bundle: {dll_to_load}")
                    # Add the directory containing the DLL to PATH for other potential dependencies
                    _containing_dir = os.path.dirname(dll_to_load)
                    if _containing_dir not in os.environ["PATH"]:
                         os.environ["PATH"] = _containing_dir + os.pathsep + os.environ.get("PATH", "")
                    return True
                except OSError as e_bundle:
                    log.warning(f"Failed to load cublas64_12.dll from bundle ({dll_to_load}): {e_bundle}")
            else:
                log.warning(f"cublas64_12.dll not found in common PyInstaller bundle paths. Tried: {', '.join(tried_paths_log)}")
        
        log.warning("GPU acceleration with cuBLAS will not be available. Attempting to use CPU.")
    return False

def _gpu_ready() -> bool:
    # Check if torch is available and CUDA can be used
    if not (globals().get('TORCH_AVAILABLE') and torch is not None):
        return False
    # Check for CUDA-capable GPU
    try:
        if not torch.cuda.is_available():
            return False
        # detect device name and skip AMD GPUs
        device_name = torch.cuda.get_device_name(0)
        if any(keyword in device_name.lower() for keyword in ("amd", "radeon")):
            log.warning(f"GPU detected ({device_name}) is AMD – CUDA not supported, switching to CPU.")
            return False
    except Exception:
        return False
    # Ensure cuBLAS alias is loaded
    return _ensure_cublas()

def _candidates(size: str) -> List[str]:
    """
    Always use the faster-whisper model for the given base size.
    Only the Systran faster-whisper variant is attempted.
    """
    # extract base model name (e.g., 'base' from 'openai/whisper-base')
    raw = size.lower().split('/')[-1]
    base = raw.split('whisper-', 1)[1] if raw.startswith('whisper-') else raw
    # default to faster-whisper
    return [f"Systran/faster-whisper-{base}"]

class WhisperASR:
    def __init__(self, model_size: str = "base", compute_type: str = "int8"):
        # wybór urządzenia
        self.device = "cpu" # Default to CPU
        os.environ["CT2_FORCE_CPU"] = "1" # Ensure CTranslate2 uses CPU

        if _gpu_ready(): # This will call the modified _ensure_cublas
            self.device = "cuda"
            os.environ.pop("CT2_FORCE_CPU", None)
            log.info("GPU detected and cuBLAS found - attempting to use CUDA.")
        else:
            log.info("GPU not available or cuBLAS not found - using CPU.")

        # ustal compute_type i ograniczenie wątków na CPU
        if self.device == "cuda":
            self.compute_type = "float16"
        else:
            self.compute_type = compute_type
            # Ogranicz wątki tylko jeśli torch jest dostępny i obsługuje ustawianie wątków
            if globals().get('TORCH_AVAILABLE') and torch is not None and hasattr(torch, 'set_num_threads'):
                torch.set_num_threads(4)

        # Model availability flag
        self.available = True
        self.model_id = None
        self.model = None

        # Load Whisper model using faster-whisper if available
        candidate_list = _candidates(model_size)
        try:
            from faster_whisper import WhisperModel as FastWhisperModel
            for repo in candidate_list:
                try:
                    log.info(f"→ próba FastWhisper: {repo}")
                    self.model = FastWhisperModel(repo, device=self.device, compute_type=self.compute_type)
                    self.model_id = repo
                    log.info(f"✓ załadowano FastWhisper: {repo}")
                    break
                except Exception as e:
                    log.warning(f"✗ FastWhisper failed {repo}: {type(e).__name__}: {e}")
        except ImportError:
            log.warning("⚠️ faster_whisper not installed, skipping FastWhisper load")

        # If no model loaded, disable ASR feature
        if self.model is None:
            log.error("WhisperASR disabled: could not load any FastWhisper model.")
            self.available = False
            return

    @measure_performance
    def transcribe(
        self,
        audio: str | any,
        beam_size: int = 1,
        sample_rate: int | None = None,
    ) -> str:
        """
        Transcribe audio; greedy decoding (beam_size=1) dla szybkości.
        """
        segments, _ = self.model.transcribe(audio, beam_size=beam_size)
        return "".join(s.text for s in segments)

    def unload(self) -> None:
        if hasattr(self, "model"):
            log.info(f"Unloading WhisperModel ({self.model_id}) …")
            del self.model
            if self.device == "cuda":
                torch.cuda.empty_cache()
