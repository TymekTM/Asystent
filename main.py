#!/usr/bin/env python3
"""
GAJA Assistant - Main Entry Point
Unified entry point that can run as either client or server based on arguments.
"""

import sys
from pathlib import Path

# Add client and server paths
sys.path.insert(0, str(Path(__file__).parent / "client"))
sys.path.insert(0, str(Path(__file__).parent / "server"))
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Main entry point that determines whether to run client or server."""
    import asyncio

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Run as server
        from server.server_main import main as server_main

        server_main()
    else:
        # Default: run as client
        from client.client_main import main as client_main

        asyncio.run(client_main())


if __name__ == "__main__":
    main()
