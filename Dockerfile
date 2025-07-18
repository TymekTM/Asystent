FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy server requirements
COPY requirements_server_minimal.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/ ./server/
COPY .env .env

# Create necessary directories
RUN mkdir -p logs databases ssl data/cache data/history data/logs data/user_data

# Set file permissions
RUN chmod 755 /app
RUN chmod -R 755 logs databases ssl data server

# Expose port (server runs on 5000 by default)
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Environment variables
ENV PYTHONPATH=/app
ENV PRODUCTION=true
ENV DEBUG=false

# Start server
WORKDIR /app/server
CMD ["python", "server_main.py"]
