FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements_minimal.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs databases ssl data/cache data/history data/logs data/user_data

# Set file permissions
RUN chmod 755 /app
RUN chmod -R 755 logs databases ssl data

# Expose port
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f -k https://localhost:8443/health || exit 1

# Environment variables
ENV PYTHONPATH=/app
ENV PRODUCTION=true
ENV DEBUG=false

# Start server
CMD ["python", "server_main.py"]
