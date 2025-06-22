#!/usr/bin/env python3
"""GAJA Assistant Server Entry Point Dedicated entry point for server-only builds."""

import sys
from pathlib import Path

# Add server path
sys.path.insert(0, str(Path(__file__).parent / "server"))
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Server entry point."""
    # Force server mode by adding server argument
    if len(sys.argv) == 1 or sys.argv[1] != "server":
        sys.argv.append("server")

    from server.server_main import main as server_main

    server_main()


if __name__ == "__main__":
    main()
