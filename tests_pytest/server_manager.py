"""🔧 Server Checker and Auto-Starter for Stress Tests.

Checks if the Gaja server is running and optionally starts it.
Compliant with AGENTS.md requirements - uses async operations.
"""

import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path

import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServerManager:
    """Manages Gaja server for testing."""

    def __init__(self, server_url: str = "http://localhost:8001"):
        self.server_url = server_url
        self.server_process = None

    async def check_server_health(self, timeout: int = 5) -> bool:
        """Check if server is running and healthy."""
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(f"{self.server_url}/health") as response:
                    if response.status == 200:
                        logger.info("✅ Server is healthy and responding")
                        return True
                    else:
                        logger.warning(
                            f"⚠️ Server responded with status {response.status}"
                        )
                        return False
        except Exception as e:
            logger.debug(f"Server health check failed: {e}")
            return False

    async def wait_for_server(self, max_wait_seconds: int = 60) -> bool:
        """Wait for server to become healthy."""
        logger.info(f"⏳ Waiting for server to be ready (max {max_wait_seconds}s)...")

        start_time = time.time()
        while time.time() - start_time < max_wait_seconds:
            if await self.check_server_health():
                return True
            await asyncio.sleep(2)

        logger.error(
            f"❌ Server did not become healthy within {max_wait_seconds} seconds"
        )
        return False

    def start_server_docker(self) -> bool:
        """Start server using Docker."""
        try:
            logger.info("🐳 Starting server using Docker...")

            # Use manage.py to start server
            result = subprocess.run(
                [sys.executable, "manage.py", "start-server"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            if result.returncode == 0:
                logger.info("✅ Docker server start command executed successfully")
                return True
            else:
                logger.error(f"❌ Failed to start Docker server: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Exception starting Docker server: {e}")
            return False

    def start_server_local(self) -> bool:
        """Start server locally using Python."""
        try:
            logger.info("🐍 Starting server locally...")

            # Start server using server_main.py
            server_script = Path(__file__).parent.parent / "server" / "server_main.py"

            if not server_script.exists():
                logger.error(f"❌ Server script not found: {server_script}")
                return False

            # Start server in background
            self.server_process = subprocess.Popen(
                [sys.executable, str(server_script)], cwd=Path(__file__).parent.parent
            )

            logger.info(f"✅ Server started with PID {self.server_process.pid}")
            return True

        except Exception as e:
            logger.error(f"❌ Exception starting local server: {e}")
            return False

    def stop_server(self) -> None:
        """Stop the server if we started it."""
        if self.server_process:
            try:
                logger.info("🛑 Stopping server...")
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
                logger.info("✅ Server stopped")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ Server didn't stop gracefully, killing...")
                self.server_process.kill()
            except Exception as e:
                logger.error(f"❌ Error stopping server: {e}")
            finally:
                self.server_process = None

    async def ensure_server_running(
        self, auto_start: bool = False, prefer_docker: bool = True
    ) -> bool:
        """Ensure server is running, optionally start it.

        Args:
            auto_start: Whether to automatically start server if not running
            prefer_docker: Whether to prefer Docker over local Python execution

        Returns:
            True if server is running, False otherwise
        """
        logger.info(f"🔍 Checking server at {self.server_url}...")

        # First check if server is already running
        if await self.check_server_health():
            return True

        if not auto_start:
            logger.error("❌ Server is not running and auto-start is disabled")
            return False

        # Try to start server
        started = False

        if prefer_docker:
            started = self.start_server_docker()
            if started:
                started = await self.wait_for_server(60)

        if not started:
            logger.info("🔄 Docker start failed, trying local Python server...")
            started = self.start_server_local()
            if started:
                started = await self.wait_for_server(30)

        if not started:
            logger.error("❌ Failed to start server using any method")
            return False

        logger.info("✅ Server is now running and ready for testing")
        return True


async def main():
    """Main function for server management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check and manage Gaja server for testing"
    )
    parser.add_argument(
        "--server-url",
        default="http://localhost:8001",
        help="Server URL to check (default: http://localhost:8001)",
    )
    parser.add_argument(
        "--auto-start",
        action="store_true",
        help="Automatically start server if not running",
    )
    parser.add_argument(
        "--prefer-local",
        action="store_true",
        help="Prefer local Python server over Docker",
    )
    parser.add_argument(
        "--stop", action="store_true", help="Stop the server (if we started it)"
    )

    args = parser.parse_args()

    manager = ServerManager(args.server_url)

    try:
        if args.stop:
            manager.stop_server()
            return

        # Ensure server is running
        success = await manager.ensure_server_running(
            auto_start=args.auto_start, prefer_docker=not args.prefer_local
        )

        if success:
            logger.info("🎯 Server is ready for stress testing!")

            # Show quick status
            print("\n" + "=" * 50)
            print("🚀 SERVER STATUS")
            print("=" * 50)
            print(f"URL: {args.server_url}")
            print("Status: ✅ Running and healthy")
            print("Ready for stress testing!")
            print("=" * 50)

            sys.exit(0)
        else:
            logger.error("❌ Could not ensure server is running")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
        manager.stop_server()
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        manager.stop_server()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
