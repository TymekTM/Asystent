#!/usr/bin/env python3
"""Simple GAJA Flask Server for Testing."""

import logging
import os

from flask import Flask, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "gaja-assistant"})


@app.route("/")
def home():
    """Root endpoint."""
    return jsonify(
        {
            "message": "GAJA Assistant Server",
            "status": "running",
            "endpoints": ["/health", "/api/status"],
        }
    )


@app.route("/api/status")
def status():
    """Status endpoint."""
    return jsonify(
        {
            "server": "GAJA Assistant",
            "version": "1.0.0-docker",
            "environment": "production",
            "port": 8443,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("SERVER_PORT", 8443))
    host = os.environ.get("SERVER_HOST", "0.0.0.0")

    logger.info(f"Starting GAJA Assistant Server on {host}:{port}")
    app.run(host=host, port=port, debug=False)
