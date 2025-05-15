from __future__ import annotations
import os, pathlib, logging, ctypes
from typing import List
import torch
from faster_whisper import WhisperModel
from performance_monitor import measure_performance

# ────────────────────────────────────────────────────────────────
# auto-download / konwersja modelu Whisper (faster-whisper)
# bez symlinków → działa na Windowsie
# próba GPU ↔ automatyczny fallback na CPU, jeśli brakuje cuBLAS
# ────────────────────────────────────────────────────────────────

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".hf_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

# ────────────────────────────────────────────────────────────────
# Logger – tylko warning i error, żeby nie blokować
# ────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def _ensure_cublas() -> bool:
    try:
        ctypes.CDLL("cublas64_12.dll")
        return True
    except OSError:
        log.warning("cublas64_12.dll not found. Installing cuda-python package...")
        try:
            import subprocess, sys, importlib.util, pathlib, site, sysconfig, shutil
            subprocess.check_call([sys.executable, "-m", "pip", "install", "cuda-python"])
            spec = importlib.util.find_spec('cuda')
            search_dirs: list[pathlib.Path] = []
            if spec:
                if spec.origin:
                    search_dirs.append(pathlib.Path(spec.origin).parent)
                if spec.submodule_search_locations:
                    search_dirs.extend(pathlib.Path(p) for p in spec.submodule_search_locations)
            for sp in site.getsitepackages():
                search_dirs.append(pathlib.Path(sp))
            search_dirs.append(pathlib.Path(sysconfig.get_path('purelib')))
            for base_dir in search_dirs:
                for dll_path in base_dir.rglob('cublas*.dll'):
                    name = dll_path.name.lower()
                    if name == 'cublas64_12.dll':
                        os.environ["PATH"] = str(dll_path.parent) + os.pathsep + os.environ.get("PATH", "")
                        ctypes.CDLL(str(dll_path))
                        log.info(f"Loaded cuBLAS v12 from {dll_path}")
                        return True
                    if name.startswith('cublas64_'):
                        alias_dir = ROOT / '.cuda_alias'
                        alias_dir.mkdir(exist_ok=True)
                        alias_file = alias_dir / 'cublas64_12.dll'
                        if not alias_file.exists():
                            shutil.copy2(str(dll_path), str(alias_file))
                        os.environ["PATH"] = str(alias_dir) + os.pathsep + os.environ.get("PATH", "")
                        ctypes.CDLL(str(alias_file))
                        log.info(f"Aliased cuBLAS {dll_path.name} as cublas64_12.dll -> {alias_file}")
                        return True
        except Exception as e:
            log.error(f"Failed to install or load cuda-python cublas: {e}")
    return False

def _gpu_ready() -> bool:
    if not torch.cuda.is_available():
        return False
    return _ensure_cublas()

def _candidates(size: str) -> List[str]:
    std = {"tiny", "base", "small", "medium", "large", "large-v1", "large-v2", "large-v3"}
    out = [size]
    # also try base shorthand (e.g., 'small') and faster-whisper/HF repos
    raw = size.lower().split('/')[-1]
    # determine base model name, strip 'whisper-' prefix if present
    base = raw.split('whisper-', 1)[1] if raw.startswith('whisper-') else raw
    if base in std:
        # raw base model (will fetch openai/whisper-base by default)
        out.append(base)
        # Systran and explicit HF path
        out.append(f"Systran/faster-whisper-{base}")
        out.append(f"openai/whisper-{base}")
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]

class WhisperASR:
    def __init__(self, model_size: str = "base", compute_type: str = "int8"):
        # wybór urządzenia
        if _gpu_ready():
            self.device = "cuda"
            os.environ.pop("CT2_FORCE_CPU", None)
            log.info("GPU wykryte - używam CUDA.")
        else:
            self.device = "cpu"
            os.environ["CT2_FORCE_CPU"] = "1"
            log.warning("GPU niedostępne (brak cuBLAS) - przechodzę na CPU.")

        # wymusz float16 na GPU, ograniczenie wątków na CPU
        if self.device == "cuda":
            self.compute_type = "float16"
        else:
            self.compute_type = compute_type
            torch.set_num_threads(4)

        self.model_id = None
        self.model = None

        errors = []
        candidate_list = _candidates(model_size)
        log.info(f"Whisper model candidates: {candidate_list}")

        for repo in candidate_list:
            try:
                log.info(f"→ próba: {repo}")
                threads = os.cpu_count() if self.device == 'cpu' else None
                ct = self.compute_type
                self.model = WhisperModel(repo, device=self.device, compute_type=ct)
                self.model_id = repo
                log.info(f"✓ załadowano: {repo}")
                break
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                log.warning(f"✗ nieudana próba: {repo} ({msg})")
                errors.append(f"{repo} -> {msg}")

        if self.model is None:
            raise RuntimeError("Nie udało się załadować modelu Whisper:\n" + "\n".join(errors))

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
