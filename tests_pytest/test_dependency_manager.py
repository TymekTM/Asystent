#!/usr/bin/env python3
"""Tests for dependency_manager.py Following AGENTS.md guidelines: comprehensive async
testing."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dependency_manager import (
    Dependency,
    DependencyContext,
    DependencyManager,
    get_dependency_manager,
)


class TestDependency:
    """Test Dependency dataclass."""

    def test_dependency_creation(self):
        """Test dependency object creation."""
        dep = Dependency(
            name="test-package",
            version=">=1.0.0",
            size_mb=10.0,
            essential=True,
            description="Test package",
        )

        assert dep.name == "test-package"
        assert dep.version == ">=1.0.0"
        assert dep.size_mb == 10.0
        assert dep.essential is True
        assert dep.description == "Test package"

    def test_dependency_defaults(self):
        """Test dependency default values."""
        dep = Dependency(name="test", version="1.0")

        assert dep.url is None
        assert dep.size_mb is None
        assert dep.checksum is None
        assert dep.essential is True
        assert dep.description == ""


class TestDependencyManager:
    """Test DependencyManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def manager(self, temp_dir):
        """Create dependency manager with temp directory."""
        return DependencyManager(app_dir=temp_dir)

    def test_manager_initialization(self, manager, temp_dir):
        """Test manager initialization."""
        assert manager.app_dir == temp_dir
        assert manager.dependencies_dir == temp_dir / "dependencies"
        assert manager.cache_dir == temp_dir / ".dependency_cache"
        assert manager.lock_file == temp_dir / "dependencies_installed.lock"
        assert manager.manifest_file == temp_dir / "dependencies" / "manifest.json"

        # Check directories are created
        assert manager.dependencies_dir.exists()
        assert manager.cache_dir.exists()

    @pytest.mark.asyncio
    async def test_check_installation_needed_no_lock(self, manager):
        """Test installation check when no lock file exists."""
        result = await manager.check_installation_needed()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_installation_needed_no_manifest(self, manager):
        """Test installation check when lock exists but no manifest."""
        # Create lock file
        manager.lock_file.touch()

        result = await manager.check_installation_needed()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_installation_needed_valid_installation(self, manager):
        """Test installation check with valid installation."""
        # Create lock file
        manager.lock_file.touch()

        # Create valid manifest with keys matching HEAVY_DEPENDENCIES
        manifest = {
            "installed": [
                "torch",
                "torchaudio",
                "whisper",
                "sounddevice",
                "librosa",
            ],  # Essential deps from HEAVY_DEPENDENCIES
            "version": "1.0",
        }

        manager.manifest_file.parent.mkdir(exist_ok=True)
        with open(manager.manifest_file, "w") as f:
            json.dump(manifest, f)

        result = await manager.check_installation_needed()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_installation_needed_missing_essential(self, manager):
        """Test installation check with missing essential dependencies."""
        # Create lock file
        manager.lock_file.touch()

        # Create manifest missing essential deps
        manifest = {
            "installed": ["openwakeword"],  # Non-essential only
            "version": "1.0",
        }

        manager.manifest_file.parent.mkdir(exist_ok=True)
        with open(manager.manifest_file, "w") as f:
            json.dump(manifest, f)

        result = await manager.check_installation_needed()
        assert result is True

    @pytest.mark.asyncio
    async def test_save_manifest(self, manager):
        """Test saving installation manifest."""
        installed = ["torch", "sounddevice"]

        await manager._save_manifest(installed)

        assert manager.manifest_file.exists()
        with open(manager.manifest_file) as f:
            manifest = json.load(f)

        assert manifest["installed"] == installed
        assert manifest["version"] == "1.0"
        assert "installation_date" in manifest
        assert "app_version" in manifest

    @pytest.mark.asyncio
    async def test_create_lock_file(self, manager):
        """Test creating lock file."""
        await manager._create_lock_file()

        assert manager.lock_file.exists()
        content = manager.lock_file.read_text()
        assert "Dependencies installed successfully" in content

    @pytest.mark.asyncio
    async def test_get_dependency_status(self, manager):
        """Test getting dependency status."""
        with patch("builtins.__import__") as mock_import:
            # Mock some imports as successful, some as failing
            def import_side_effect(name):
                if name in ["torch", "sounddevice"]:
                    return MagicMock()
                else:
                    raise ImportError(f"No module named '{name}'")

            mock_import.side_effect = import_side_effect

            status = await manager.get_dependency_status()

            assert status["torch"] is True
            assert status["sounddevice"] is True
            assert status["whisper"] is False
            assert status["librosa"] is False

    @pytest.mark.asyncio
    async def test_ensure_dependency_unknown(self, manager):
        """Test ensuring unknown dependency."""
        result = await manager.ensure_dependency("unknown-package")
        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_dependency_already_available(self, manager):
        """Test ensuring dependency that's already available."""
        with patch("builtins.__import__") as mock_import:
            mock_import.return_value = MagicMock()

            result = await manager.ensure_dependency("torch")
            assert result is True

    @pytest.mark.asyncio
    @patch("dependency_manager.DependencyManager._install_package")
    async def test_ensure_dependency_needs_installation(self, mock_install, manager):
        """Test ensuring dependency that needs installation."""
        with patch("builtins.__import__") as mock_import:
            mock_import.side_effect = ImportError("Not installed")
            mock_install.return_value = True

            result = await manager.ensure_dependency("torch")
            assert result is True
            mock_install.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_cache(self, manager):
        """Test cache cleanup."""
        # Create some cache files
        cache_file = manager.cache_dir / "test.cache"
        cache_file.touch()

        await manager.cleanup_cache()

        assert manager.cache_dir.exists()
        assert not cache_file.exists()


class TestDependencyContext:
    """Test DependencyContext async context manager."""

    @pytest.mark.asyncio
    async def test_dependency_context_success(self):
        """Test successful dependency context."""
        with patch("dependency_manager.get_dependency_manager") as mock_get_dm:
            mock_dm = AsyncMock()
            mock_dm.ensure_dependency.return_value = True
            mock_get_dm.return_value = mock_dm

            async with DependencyContext(["torch", "sounddevice"]) as ctx:
                assert ctx is not None

            assert mock_dm.ensure_dependency.call_count == 2

    @pytest.mark.asyncio
    async def test_dependency_context_failure(self):
        """Test dependency context with failure."""
        with patch("dependency_manager.get_dependency_manager") as mock_get_dm:
            mock_dm = AsyncMock()
            mock_dm.ensure_dependency.return_value = False
            mock_get_dm.return_value = mock_dm

            with pytest.raises(RuntimeError, match="Failed to ensure dependency"):
                async with DependencyContext(["torch"]):
                    pass


class TestGlobalFunctions:
    """Test global utility functions."""

    def test_get_dependency_manager_singleton(self):
        """Test dependency manager singleton."""
        dm1 = get_dependency_manager()
        dm2 = get_dependency_manager()

        assert dm1 is dm2  # Should be same instance
        assert isinstance(dm1, DependencyManager)

    @pytest.mark.asyncio
    async def test_ensure_dependencies(self):
        """Test convenience function."""
        with patch("dependency_manager.get_dependency_manager") as mock_get_dm:
            mock_dm = AsyncMock()
            mock_dm.install_dependencies.return_value = True
            mock_get_dm.return_value = mock_dm

            from dependency_manager import ensure_dependencies

            result = await ensure_dependencies()

            assert result is True
            mock_dm.install_dependencies.assert_called_once()


class TestIntegration:
    """Integration tests for full workflow."""

    @pytest.mark.asyncio
    async def test_full_installation_workflow(self):
        """Test complete installation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = DependencyManager(app_dir=temp_path)

            # Mock pip installation
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                # Mock successful pip install
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.communicate.return_value = (b"Successfully installed", b"")
                mock_subprocess.return_value = mock_process

                # Run installation
                result = await manager.install_dependencies()

                # Check results
                assert result is True
                assert manager.lock_file.exists()
                assert manager.manifest_file.exists()

                # Check manifest content
                with open(manager.manifest_file) as f:
                    manifest = json.load(f)

                essential_deps = [
                    name
                    for name, dep in manager.HEAVY_DEPENDENCIES.items()
                    if dep.essential
                ]
                assert set(manifest["installed"]) == set(essential_deps)

    @pytest.mark.asyncio
    async def test_installation_failure_handling(self):
        """Test handling of installation failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = DependencyManager(app_dir=temp_path)

            # Mock pip installation failure
            with patch("asyncio.create_subprocess_exec") as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 1
                mock_process.communicate.return_value = (b"", b"Installation failed")
                mock_subprocess.return_value = mock_process

                # Run installation
                result = await manager.install_dependencies()

                # Check results
                assert result is False
                assert not manager.lock_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
