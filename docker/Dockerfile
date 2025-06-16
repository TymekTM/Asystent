# Multi-stage Dockerfile for Gaja Assistant
# Supports both CPU and GPU variants

# ==============================================================================
# Base stage - common dependencies
# Using latest Python 3.11 patch version for security fixes
# Note: Docker scanner may report vulnerabilities in base images - these are
# typically patched in newer releases. Always use latest patch versions.
# ==============================================================================
FROM python:3.11-slim-bookworm AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Audio processing
    portaudio19-dev \
    libportaudio2 \
    libasound2-dev \
    # Speech synthesis
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    # Media processing
    ffmpeg \
    # Build tools
    build-essential \
    gcc \
    g++ \
    # Networking
    curl \
    wget \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Poetry
RUN pip install poetry==1.7.1

# Create app user
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# ==============================================================================
# Build stage - install dependencies and build wheels
# ==============================================================================
FROM base AS builder

# Install dependencies without creating venv yet
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root \
    && rm -rf $POETRY_CACHE_DIR

# Copy source code structure that matches the project
COPY src/ ./src/
COPY server/ ./server/
COPY client/ ./client/
COPY *.py ./
COPY README.md ./

# Now create and install into venv
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --only=main

# ==============================================================================
# CPU Runtime stage
# ==============================================================================
FROM base AS cpu

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code structure that matches the project
COPY --from=builder /app/src /app/src
COPY --from=builder /app/server /app/server
COPY --from=builder /app/client /app/client
COPY --from=builder /app/*.py /app/
COPY --from=builder /app/README.md /app/

# Create necessary directories
RUN mkdir -p /app/data/logs \
    /app/data/cache \
    /app/data/user_data \
    /app/data/history

# Switch to app user
USER app

# Make sure venv is in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Health check (adjusted for correct port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command (using actual server file)
CMD ["python", "server/server_main.py"]

# ==============================================================================
# GPU Runtime stage (CUDA support)
# ==============================================================================
FROM nvidia/cuda:12.1-runtime-ubuntu20.04 AS gpu-base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    # Audio processing
    portaudio19-dev \
    libportaudio2 \
    libasound2-dev \
    # Speech synthesis
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    # Media processing
    ffmpeg \
    # Build tools
    build-essential \
    gcc \
    g++ \
    # Networking
    curl \
    wget \
    # CUDA tools
    nvidia-cuda-toolkit \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create symlinks for Python
RUN ln -s /usr/bin/python3.11 /usr/bin/python \
    && ln -s /usr/bin/python3.11 /usr/bin/python3

# Install Poetry
RUN pip install poetry==1.7.1

# Create app user
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app

# Set working directory
WORKDIR /app

FROM gpu-base AS gpu-builder

# Set environment variables for Poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Install dependencies with CUDA support
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root \
    && rm -rf $POETRY_CACHE_DIR

# Install PyTorch with CUDA support (override poetry version)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy source code structure that matches the project
COPY src/ ./src/
COPY server/ ./server/
COPY client/ ./client/
COPY *.py ./
COPY README.md ./

# Now create and install into venv
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --only=main

FROM gpu-base AS gpu

# Copy virtual environment from GPU builder
COPY --from=gpu-builder /app/.venv /app/.venv

# Copy source code structure that matches the project
COPY --from=gpu-builder /app/src /app/src
COPY --from=gpu-builder /app/server /app/server
COPY --from=gpu-builder /app/client /app/client
COPY --from=gpu-builder /app/*.py /app/
COPY --from=gpu-builder /app/README.md /app/

# Create necessary directories
RUN mkdir -p /app/data/logs \
    /app/data/cache \
    /app/data/user_data \
    /app/data/history \
    && chown -R app:app /app

# Switch to app user
USER app

# Make sure venv is in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Set CUDA environment variables
ENV CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Health check (adjusted for correct port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command (using actual server file)
CMD ["python", "server/server_main.py"]

# ==============================================================================
# Development stage
# ==============================================================================
FROM base AS development

# Install all dependencies including dev
RUN poetry install && rm -rf $POETRY_CACHE_DIR

# Copy source code
COPY . .

# Install pre-commit
RUN poetry run pre-commit install

# Switch to app user
USER app

# Make sure venv is in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Default command for development
CMD ["poetry", "run", "python", "-m", "gaja_server.main", "--debug"]
