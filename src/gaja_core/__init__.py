"""
Gaja Core - Shared utilities and core functionality.

This module contains shared utilities, common functions, and core
functionality used by both the server and client components.
"""

from . import database_models, mode_integrator

__version__ = "0.1.0"
__author__ = "Gaja Assistant Team"

__all__ = [
    "database_models",
    "mode_integrator",
]
