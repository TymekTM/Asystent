#!/usr/bin/env python3
"""
GAJA Assistant - Dependency Manager
Asynchronous dependency management system for downloading heavy ML packages at runtime.
Follows AGENTS.md guidelines: async, testable, modular.
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """Represents a dependency package."""

    name: str
    version: str
    url: str | None = None
    size_mb: float | None = None
    checksum: str | None = None
    essential: bool = True
    description: str = ""


class DependencyManager:
    """Asynchronous dependency manager for GAJA Assistant.

    Downloads and manages heavy ML packages at runtime.
    """

    # Heavy dependencies that should not be bundled in EXE
    HEAVY_DEPENDENCIES = {
        "torch": Dependency(
            name="torch",
            version=">=2.0.0",
            size_mb=800.0,
            essential=True,
            description="PyTorch machine learning framework",
        ),
        "torchaudio": Dependency(
            name="torchaudio",
            version=">=2.0.0",
            size_mb=50.0,
            essential=True,
            description="PyTorch audio processing",
        ),
        "whisper": Dependency(
            name="openai-whisper",
            version=">=20231117",
            size_mb=200.0,
            essential=True,
            description="OpenAI Whisper speech recognition",
        ),
        "faster_whisper": Dependency(
            name="faster-whisper",
            version=">=0.10.0",
            size_mb=150.0,
            essential=False,
            description="Faster Whisper implementation",
        ),
        "openwakeword": Dependency(
            name="openwakeword",
            version=">=0.5.1",
            size_mb=100.0,
            essential=False,
            description="Wake word detection",
        ),
        "sounddevice": Dependency(
            name="sounddevice",
            version=">=0.4.6",
            size_mb=20.0,
            essential=True,
            description="Audio device access",
        ),
        "librosa": Dependency(
            name="librosa",
            version=">=0.10.1",
            size_mb=80.0,
            essential=True,
            description="Audio processing library",
        ),
    }

    def __init__(self, app_dir: Path | None = None):
        """Initialize dependency manager."""
        self.app_dir = app_dir or Path.cwd()
        self.dependencies_dir = self.app_dir / "dependencies"
        self.cache_dir = self.app_dir / ".dependency_cache"
        self.lock_file = self.app_dir / "dependencies_installed.lock"
        self.manifest_file = self.dependencies_dir / "manifest.json"

        # Create directories
        self.dependencies_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

        # Add dependencies to Python path
        if str(self.dependencies_dir) not in sys.path:
            sys.path.insert(0, str(self.dependencies_dir))

    async def check_installation_needed(self) -> bool:
        """Check if dependency installation is needed."""
        if not self.lock_file.exists():
            return True

        # Check if manifest exists and is valid
        if not self.manifest_file.exists():
            return True

        try:
            async with aiofiles.open(self.manifest_file) as f:
                manifest = json.loads(await f.read())

            # Verify essential dependencies are listed
            installed_deps = set(manifest.get("installed", []))
            essential_deps = {
                name for name, dep in self.HEAVY_DEPENDENCIES.items() if dep.essential
            }

            return not essential_deps.issubset(installed_deps)

        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return True

    async def install_dependencies(self, force: bool = False) -> bool:
        """Install all essential dependencies asynchronously.

        Args:
            force: Force reinstallation even if already installed

        Returns:
            True if installation successful, False otherwise
        """
        if not force and not await self.check_installation_needed():
            logger.info("Dependencies already installed")
            return True

        logger.info("Starting dependency installation...")

        # Install essential dependencies
        essential_deps = {
            name: dep for name, dep in self.HEAVY_DEPENDENCIES.items() if dep.essential
        }

        success = True
        installed = []

        for name, dependency in essential_deps.items():
            try:
                logger.info(
                    f"Installing {dependency.name} ({dependency.description})..."
                )
                if await self._install_package(dependency):
                    installed.append(name)
                    logger.info(f"✅ {dependency.name} installed successfully")
                else:
                    logger.error(f"❌ Failed to install {dependency.name}")
                    success = False
            except Exception as e:
                logger.error(f"❌ Error installing {dependency.name}: {e}")
                success = False

        if success:
            await self._save_manifest(installed)
            await self._create_lock_file()
            logger.info("✅ All essential dependencies installed successfully")
        else:
            logger.error("❌ Some dependencies failed to install")

        return success

    async def _install_package(self, dependency: Dependency) -> bool:
        """Install a single package using pip."""
        try:
            # Use pip to install the package
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                f"{dependency.name}{dependency.version}",
                "--target",
                str(self.dependencies_dir),
                "--no-cache-dir",
                "--no-deps",  # Install without dependencies to avoid conflicts
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.debug(f"pip install stdout: {stdout.decode()}")
                return True
            else:
                logger.error(f"pip install failed: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Failed to install {dependency.name}: {e}")
            return False

    async def _save_manifest(self, installed: list[str]) -> None:
        """Save installation manifest."""
        manifest = {
            "version": "1.0",
            "installed": installed,
            "installation_date": str(asyncio.get_event_loop().time()),
            "app_version": "2.1.0",  # TODO: Get from config
        }

        async with aiofiles.open(self.manifest_file, "w") as f:
            await f.write(json.dumps(manifest, indent=2))

    async def _create_lock_file(self) -> None:
        """Create lock file to indicate successful installation."""
        async with aiofiles.open(self.lock_file, "w") as f:
            await f.write(
                f"Dependencies installed successfully\nTimestamp: {asyncio.get_event_loop().time()}\n"
            )

    async def get_dependency_status(self) -> dict[str, bool]:
        """Get installation status of all dependencies."""
        status = {}

        for name, dependency in self.HEAVY_DEPENDENCIES.items():
            try:
                # Try to import the package
                __import__(dependency.name.replace("-", "_"))
                status[name] = True
            except ImportError:
                status[name] = False

        return status

    async def ensure_dependency(self, name: str) -> bool:
        """Ensure a specific dependency is available. Install it if not present.

        Args:
            name: Name of the dependency

        Returns:
            True if dependency is available, False otherwise
        """
        if name not in self.HEAVY_DEPENDENCIES:
            logger.warning(f"Unknown dependency: {name}")
            return False

        dependency = self.HEAVY_DEPENDENCIES[name]

        # Check if already available
        try:
            __import__(dependency.name.replace("-", "_"))
            return True
        except ImportError:
            pass

        # Install if not available
        logger.info(f"Installing missing dependency: {dependency.name}")
        return await self._install_package(dependency)

    async def cleanup_cache(self) -> None:
        """Clean up temporary cache files."""
        try:
            import shutil

            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                logger.info("Dependency cache cleaned")
        except Exception as e:
            logger.error(f"Failed to clean cache: {e}")


# Singleton instance for global access
_dependency_manager: DependencyManager | None = None


def get_dependency_manager() -> DependencyManager:
    """Get global dependency manager instance."""
    global _dependency_manager
    if _dependency_manager is None:
        _dependency_manager = DependencyManager()
    return _dependency_manager


async def ensure_dependencies() -> bool:
    """Convenience function to ensure all dependencies are installed."""
    dm = get_dependency_manager()
    return await dm.install_dependencies()


# Async context manager for dependency management
class DependencyContext:
    """Async context manager for dependency management."""

    def __init__(self, required_deps: list[str]):
        self.required_deps = required_deps
        self.dm = get_dependency_manager()

    async def __aenter__(self):
        """Ensure dependencies are available."""
        for dep in self.required_deps:
            if not await self.dm.ensure_dependency(dep):
                raise RuntimeError(f"Failed to ensure dependency: {dep}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup if needed."""
        pass


# Decorator for functions that require specific dependencies
def requires_dependencies(*deps):
    """Decorator to ensure dependencies are available before function execution."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with DependencyContext(list(deps)):
                return await func(*args, **kwargs)

        return wrapper

    return decorator
