#!/usr/bin/env python3
"""GAJA Overlay Path Fix Naprawia ścieżki do overlay w konfiguracji klienta.

Following AGENTS.md guidelines:
- Async-first architecture
- Clear logging and error handling
- Modular design
"""

import logging
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OverlayPathFixer:
    """Fix overlay path issues in GAJA client."""

    def __init__(self):
        """Initialize path fixer."""
        self.project_root = Path(__file__).parent
        self.potential_overlay_paths = [
            # Current paths that client checks
            self.project_root
            / "client"
            / "overlay"
            / "target"
            / "release"
            / "gaja-overlay.exe",
            self.project_root / "overlay" / "target" / "release" / "gaja-overlay.exe",
            # Additional paths to check
            self.project_root
            / "gaja_client"
            / "overlay"
            / "target"
            / "release"
            / "gaja-overlay.exe",
            self.project_root
            / "gaja_ui"
            / "overlay"
            / "target"
            / "release"
            / "gaja-overlay.exe",
            self.project_root / "release" / "overlay" / "Asystent Overlay.exe",
            # Legacy locations
            self.project_root / "dist" / "overlay" / "gaja-overlay.exe",
            self.project_root / "build" / "overlay" / "gaja-overlay.exe",
        ]

    def find_overlay_executable(self) -> Path:
        """Find the correct overlay executable."""
        print("🔍 Searching for overlay executable...")

        for path in self.potential_overlay_paths:
            print(f"   Checking: {path}")
            if path.exists():
                print(f"   ✅ Found: {path}")
                return path
            else:
                print(f"   ❌ Not found: {path}")

        print("❌ No overlay executable found!")
        return None

    def test_overlay_execution(self, overlay_path: Path) -> bool:
        """Test if overlay can be executed."""
        try:
            print(f"🧪 Testing overlay execution: {overlay_path}")

            # Try to start overlay process (it will start and we'll kill it quickly)
            process = subprocess.Popen(
                [str(overlay_path)],
                cwd=overlay_path.parent.parent,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP")
                else 0,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait a bit to see if it starts
            import time

            time.sleep(2)

            # Check if process is still running
            if process.poll() is None:
                print("   ✅ Overlay started successfully")
                # Kill it
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
                return True
            else:
                stdout, stderr = process.communicate()
                print("   ❌ Overlay exited immediately")
                print(f"   stdout: {stdout.decode()}")
                print(f"   stderr: {stderr.decode()}")
                return False

        except Exception as e:
            print(f"   ❌ Error testing overlay: {e}")
            return False

    def create_symlink_fix(self, source_path: Path) -> bool:
        """Create symbolic link to fix path issues."""
        try:
            # Target path that client expects
            expected_path = (
                self.project_root
                / "client"
                / "overlay"
                / "target"
                / "release"
                / "gaja-overlay.exe"
            )

            print("🔗 Creating symlink fix...")
            print(f"   Source: {source_path}")
            print(f"   Target: {expected_path}")

            # Create directory structure if needed
            expected_path.parent.mkdir(parents=True, exist_ok=True)

            # Remove existing file/link if exists
            if expected_path.exists() or expected_path.is_symlink():
                expected_path.unlink()

            # Create symlink
            expected_path.symlink_to(source_path.absolute())

            if expected_path.exists():
                print("   ✅ Symlink created successfully")
                return True
            else:
                print("   ❌ Symlink creation failed")
                return False

        except Exception as e:
            print(f"   ❌ Error creating symlink: {e}")
            # Try copying instead
            return self.copy_overlay_fix(source_path)

    def copy_overlay_fix(self, source_path: Path) -> bool:
        """Copy overlay to expected location."""
        try:
            import shutil

            expected_path = (
                self.project_root
                / "client"
                / "overlay"
                / "target"
                / "release"
                / "gaja-overlay.exe"
            )

            print("📋 Copying overlay as fallback...")
            print(f"   Source: {source_path}")
            print(f"   Target: {expected_path}")

            # Create directory structure
            expected_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_path, expected_path)

            if expected_path.exists():
                print("   ✅ Copy successful")
                return True
            else:
                print("   ❌ Copy failed")
                return False

        except Exception as e:
            print(f"   ❌ Error copying overlay: {e}")
            return False

    def start_client_with_fixed_overlay(self) -> bool:
        """Start the client after fixing overlay path."""
        try:
            print("🚀 Starting GAJA client...")

            client_script = self.project_root / "client" / "client_main.py"
            if not client_script.exists():
                client_script = self.project_root / "client_main.py"

            if not client_script.exists():
                print("❌ Client script not found")
                return False

            # Start client process
            process = subprocess.Popen(
                [sys.executable, str(client_script)],
                cwd=client_script.parent,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP")
                else 0,
            )

            print(f"✅ Client started with PID: {process.pid}")
            print("   Monitor the client logs to see if overlay starts correctly")

            return True

        except Exception as e:
            print(f"❌ Error starting client: {e}")
            return False


def main():
    """Main fix entry point."""
    print("🔧 GAJA Overlay Path Fixer")
    print("=" * 40)

    fixer = OverlayPathFixer()

    # Step 1: Find overlay
    overlay_path = fixer.find_overlay_executable()
    if not overlay_path:
        print("❌ Cannot fix overlay - executable not found")
        return False

    # Step 2: Test overlay
    if not fixer.test_overlay_execution(overlay_path):
        print("⚠️ Overlay executable found but may have issues")
        # Continue anyway, might work in full context

    # Step 3: Fix path issue
    print("\n🔧 Applying path fix...")

    # Try symlink first (preferred)
    if fixer.create_symlink_fix(overlay_path):
        print("✅ Path fix applied successfully (symlink)")
    else:
        print("⚠️ Symlink failed, trying copy...")
        if fixer.copy_overlay_fix(overlay_path):
            print("✅ Path fix applied successfully (copy)")
        else:
            print("❌ All path fix methods failed")
            return False

    # Step 4: Start client
    print("\n🚀 Starting client...")
    if fixer.start_client_with_fixed_overlay():
        print("✅ Client startup initiated")
        print("\n📋 Next steps:")
        print("1. Check client logs for overlay startup")
        print("2. Run overlay debug tools to test functionality")
        print("3. Use 'python overlay_comprehensive_debug.py' to verify fix")
        return True
    else:
        print("❌ Failed to start client")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Overlay path fix completed successfully!")
    else:
        print("\n💥 Overlay path fix failed!")
        sys.exit(1)
