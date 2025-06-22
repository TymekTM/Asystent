# Multi-stage Dockerfile for Gaja Assistant Server
# Supports both CPU and GPU variants with comprehensive resource management

# ==============================================================================
# Base stage - common dependencies with system resource management
# ==============================================================================
FROM python:3.11-slim-bookworm AS base

# Set comprehensive environment variables for resource management
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    # Resource management
    MALLOC_ARENA_MAX=2 \
    MALLOC_MMAP_THRESHOLD_=1048576 \
    MALLOC_TRIM_THRESHOLD_=1048576 \
    # AI/ML optimizations
    TORCH_HOME=/app/.torch_cache \
    HF_HOME=/app/.hf_cache \
    TRANSFORMERS_CACHE=/app/.hf_cache \
    # Server settings
    GAJA_MODE=server \
    GAJA_LOG_LEVEL=INFO \
    GAJA_HOST=0.0.0.0 \
    GAJA_PORT=8001

# Install comprehensive system dependencies for full resource management
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
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    # Build tools
    build-essential \
    gcc \
    g++ \
    cmake \
    # System monitoring and resource management
    htop \
    iotop \
    nethogs \
    sysstat \
    procps \
    # Networking
    curl \
    wget \
    netcat-openbsd \
    # Database tools
    sqlite3 \
    # Security
    ca-certificates \
    gnupg \
    # Memory management
    libjemalloc2 \
    # Process management
    supervisor \
    # Log management
    logrotate \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Poetry with all required dependencies
RUN pip install poetry==1.7.1

# Create app user with proper permissions for resource management
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app \
    && usermod -aG audio app \
    && mkdir -p /app/.torch_cache /app/.hf_cache /app/data /app/logs \
    && chown -R app:app /app

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# ==============================================================================
# Build stage - install dependencies and optimize for production
# ==============================================================================
FROM base AS builder

# Install dependencies with caching optimization
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root --no-dev \
    && rm -rf $POETRY_CACHE_DIR

# Copy source code structure that matches the project
COPY src/ ./src/
COPY server/ ./server/
COPY gaja_core/ ./gaja_core/
COPY gaja_server/ ./gaja_server/
COPY *.py ./
COPY README.md ./

# Create and install into optimized venv
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --only=main --no-dev

# ==============================================================================
# CPU Runtime stage with comprehensive resource management
# ==============================================================================
FROM base AS cpu

# Install jemalloc for better memory management
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code structure that matches the project
COPY --from=builder /app/src /app/src
COPY --from=builder /app/server /app/server
COPY --from=builder /app/gaja_core /app/gaja_core
COPY --from=builder /app/gaja_server /app/gaja_server
COPY --from=builder /app/*.py /app/
COPY --from=builder /app/README.md /app/

# Create comprehensive directory structure with proper permissions
RUN mkdir -p /app/data/{logs,cache,user_data,history,models,temp} \
    /app/config \
    /app/plugins \
    /app/.torch_cache \
    /app/.hf_cache \
    /var/log/gaja \
    && chown -R app:app /app /var/log/gaja

# Copy configuration files
COPY docker/supervisor.conf /etc/supervisor/conf.d/gaja.conf
COPY docker/logrotate.conf /etc/logrotate.d/gaja

# Switch to app user
USER app

# Make sure venv is in PATH and add current directory to PYTHONPATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# Resource limits and optimizations for CPU variant
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    NUMBA_NUM_THREADS=4

# Default command with supervisor for production process management
CMD ["python", "server/server_main.py"]

# ==============================================================================
# GPU Base stage - CUDA-enabled for AI acceleration
# ==============================================================================
FROM nvidia/cuda:12.1-runtime-ubuntu20.04 AS gpu-base

# Set comprehensive environment variables for GPU resource management
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    DEBIAN_FRONTEND=noninteractive \
    # GPU resource management
    CUDA_VISIBLE_DEVICES=0 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    # Memory management for GPU
    PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 \
    CUDA_LAUNCH_BLOCKING=0 \
    # AI/ML optimizations
    TORCH_HOME=/app/.torch_cache \
    HF_HOME=/app/.hf_cache \
    TRANSFORMERS_CACHE=/app/.hf_cache \
    # Server settings
    GAJA_MODE=server \
    GAJA_LOG_LEVEL=INFO \
    GAJA_HOST=0.0.0.0 \
    GAJA_PORT=8001

# Install system dependencies
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
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    # Build tools
    build-essential \
    gcc \
    g++ \
    cmake \
    # GPU monitoring
    nvidia-utils-535 \
    # System monitoring and resource management
    htop \
    iotop \
    nethogs \
    sysstat \
    procps \
    # Networking
    curl \
    wget \
    netcat-openbsd \
    # Database tools
    sqlite3 \
    # Security
    ca-certificates \
    gnupg \
    # Process management
    supervisor \
    # Log management
    logrotate \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Update alternatives to use Python 3.11
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Install Poetry
RUN pip3 install poetry==1.7.1 --no-deps

# Create app user with GPU access
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /bin/bash --create-home app \
    && usermod -aG audio app \
    && mkdir -p /app/.torch_cache /app/.hf_cache /app/data /app/logs \
    && chown -R app:app /app

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# ==============================================================================
# GPU Builder stage
# ==============================================================================
FROM gpu-base AS gpu-builder-stage

# Install dependencies with GPU support
RUN poetry config virtualenvs.create false \
    && poetry install --only=main --no-root --no-dev \
    && rm -rf $POETRY_CACHE_DIR

# Install PyTorch with CUDA support
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy source code
COPY src/ ./src/
COPY server/ ./server/
COPY gaja_core/ ./gaja_core/
COPY gaja_server/ ./gaja_server/
COPY *.py ./
COPY README.md ./

# Create optimized venv with GPU support
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry install --only=main --no-dev

# ==============================================================================
# GPU Runtime stage with full resource management
# ==============================================================================
FROM gpu-base AS gpu

# Copy virtual environment from builder
COPY --from=gpu-builder-stage /app/.venv /app/.venv

# Copy source code structure
COPY --from=gpu-builder-stage /app/src /app/src
COPY --from=gpu-builder-stage /app/server /app/server
COPY --from=gpu-builder-stage /app/gaja_core /app/gaja_core
COPY --from=gpu-builder-stage /app/gaja_server /app/gaja_server
COPY --from=gpu-builder-stage /app/*.py /app/
COPY --from=gpu-builder-stage /app/README.md /app/

# Create comprehensive directory structure with proper permissions
RUN mkdir -p /app/data/{logs,cache,user_data,history,models,temp} \
    /app/config \
    /app/plugins \
    /app/.torch_cache \
    /app/.hf_cache \
    /var/log/gaja \
    && chown -R app:app /app /var/log/gaja

# Switch to app user
USER app

# Make sure venv is in PATH and add current directory to PYTHONPATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:$PYTHONPATH"

# GPU-specific resource optimizations
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 \
    OMP_NUM_THREADS=8 \
    MKL_NUM_THREADS=8 \
    NUMBA_NUM_THREADS=8

# Health check with GPU monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health && \
        ps aux | grep -v grep | grep -q "server_main.py" && \
        [ $(df /app/data | tail -1 | awk '{print $5}' | sed 's/%//') -lt 95 ] && \
        nvidia-smi > /dev/null 2>&1

# Default command
CMD ["python", "server/server_main.py"]

# ==============================================================================
# Development stage with full debugging tools
# ==============================================================================
FROM base AS development

# Install development dependencies
USER root
RUN apt-get update && apt-get install -y \
    vim \
    git \
    gdb \
    strace \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER app

# Copy everything for development
COPY . /app/

# Install with dev dependencies
RUN poetry install --with dev

# Development command with auto-reload
CMD ["python", "-m", "uvicorn", "server.server_main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
