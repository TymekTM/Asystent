"""
audio_modules/whisper_asr.py
────────────────────────────
• auto‑download lub auto‑konwersja modelu Whisper (faster‑whisper)
• bez symlinków → działa na Windowsie
• próba GPU ↔ automatyczny fallback na CPU, jeśli brakuje cuBLAS
"""

from __future__ import annotations
import os, pathlib, logging, ctypes
from typing import List
import torch
from faster_whisper import WhisperModel
from performance_monitor import measure_performance

# ────────────────────────────────────────────────────────────────
# 1. Cache Hugging Face (lokalny dla projektu)
# ────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / ".hf_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

os.environ["HF_HOME"] = str(CACHE_DIR)
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"       # kopiuj, nie linkuj

# ────────────────────────────────────────────────────────────────
# 2. Logger
# ────────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# ────────────────────────────────────────────────────────────────
# 3. Detekcja „prawdziwego” GPU (czy jest cuBLAS DLL)
# ────────────────────────────────────────────────────────────────
def _gpu_ready() -> bool:
    if not torch.cuda.is_available():
        return False
    try:
        ctypes.CDLL("cublas64_12.dll")  # CUDA 12; spróbuj też 11, 10 …
        return True
    except OSError:
        return False

# ────────────────────────────────────────────────────────────────
# 4. Lista kandydatów (CT2 → oryginał → ścieżka)
# ────────────────────────────────────────────────────────────────
def _candidates(size: str) -> List[str]:
    std = {"tiny", "base", "small", "medium", "large", "large-v1", "large-v2"}
    out = []
    if size.lower() in std:
        out.append(f"faster-whisper/whisper-{size.lower()}-ct2")
        out.append(f"openai/whisper-{size.lower()}")
    out.append(size)  # last resort
    seen = set()
    return [x for x in out if not (x in seen or seen.add(x))]

# ────────────────────────────────────────────────────────────────
# 5. Klasa ASR
# ────────────────────────────────────────────────────────────────
class WhisperASR:
    def __init__(self, model_size: str = "base", compute_type: str = "int8"):
        # ── wybór urządzenia ───────────────────────────────────
        if _gpu_ready():
            self.device = "cuda"
            os.environ.pop("CT2_FORCE_CPU", None)     # pozwól na GPU
            log.info("GPU wykryte – używam CUDA.")
        else:
            self.device = "cpu"
            os.environ["CT2_FORCE_CPU"] = "1"         # zablokuj CUDA w CT2
            log.warning("GPU niedostępne (brak cuBLAS) – przechodzę na CPU.")

        self.compute_type = compute_type
        self.model_id = None
        self.model = None

        # ── ładowanie modelu ──────────────────────────────────
        errors = []
        for repo in _candidates(model_size):
            try:
                log.info(f"→ próba: {repo}")
                # Optimize: use multi-threading on CPU, half precision on GPU
                threads = os.cpu_count() if self.device == 'cpu' else None
                # switch to float16 for GPU if using int compute
                compute_type = self.compute_type
                if self.device == 'cuda' and compute_type.startswith('int'):
                    compute_type = 'float16'
                # Instantiate WhisperModel (newer API omits threads, local_files_only, download_root)
                # Using device and compute_type only; HF cache controlled via HF_HOME
                self.model = WhisperModel(
                    repo,
                    device=self.device,
                    compute_type=compute_type,
                )
                self.model_id = repo
                log.info(f"✓ załadowano: {repo}")
                break
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                log.warning(f"✗ nieudana próba: {repo} ({msg})")
                errors.append(f"{repo} -> {msg}")

        if self.model is None:
            raise RuntimeError(
                "Nie udało się załadować modelu Whisper:\n" + "\n".join(errors)
            )

    # ────────────────────────────────────────────────────────────
    @measure_performance
    def transcribe(
        self,
        audio: str | any,
        beam_size: int = 5,
        language: str = "pl",
        sample_rate: int | None = None,
    ) -> str:
        """
        Transcribe audio from a file path or numpy array.
        If audio is a numpy array, provide sample_rate.
        """
        # Prepare parameters for model.transcribe
        params: dict = {"beam_size": beam_size, "language": language}
        # Call underlying WhisperModel transcribe
        segments, _ = self.model.transcribe(audio, **params)
        return "".join(s.text for s in segments)

    # ────────────────────────────────────────────────────────────
    def unload(self) -> None:
        if hasattr(self, "model"):
            log.info(f"Unloading WhisperModel ({self.model_id}) …")
            del self.model
            if self.device == "cuda":
                torch.cuda.empty_cache()
