# Gaja Assistant - Docker Guide

This guide explains how to run Gaja Assistant using Docker for easy deployment and development.

## Quick Start

### 1. Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- (Optional) NVIDIA Docker for GPU support

### 2. Environment Setup

Copy the environment template and configure your settings:

```bash
cp .env.example .env
# Edit .env with your API keys and preferences
```

### 3. Choose Your Deployment

#### CPU-only Deployment (Default)
```bash
# Start the application
docker-compose up -d

# Or explicitly specify the CPU profile
docker-compose --profile cpu up -d
```

#### GPU-enabled Deployment
```bash
# Start with GPU support
docker-compose --profile gpu up -d
```

#### Development Environment
```bash
# Start development environment with live reloading
docker-compose --profile development up -d
```

#### Full Production Stack
```bash
# Start with database, Redis, and Nginx
docker-compose --profile production up -d
```

## Available Services

### Core Services

- **gaja-server-cpu**: Main application server (CPU variant)
- **gaja-server-gpu**: Main application server (GPU variant) 
- **gaja-dev**: Development environment with live reloading

### Production Services

- **database**: PostgreSQL database for production
- **redis**: Redis for caching and sessions
- **nginx**: Reverse proxy and static file server

## Docker Images

The Dockerfile supports multiple build targets:

### Build Targets

1. **cpu** (default): Optimized for CPU inference
   - Based on `python:3.11-slim`
   - Includes all audio processing dependencies
   - Smaller image size

2. **gpu**: CUDA-enabled for GPU acceleration
   - Based on `nvidia/cuda:12.1-runtime-ubuntu20.04`
   - Includes PyTorch with CUDA support
   - Requires NVIDIA Docker runtime

3. **development**: Development environment
   - Includes all dev dependencies
   - Pre-commit hooks installed
   - Code mounted as volume for live reloading

## Building Images

### Build CPU Image
```bash
docker build -f docker/Dockerfile --target cpu -t gaja-assistant:cpu .
```

### Build GPU Image
```bash
docker build -f docker/Dockerfile --target gpu -t gaja-assistant:gpu .
```

### Build Development Image
```bash
docker build -f docker/Dockerfile --target development -t gaja-assistant:dev .
```

## Volumes and Data Persistence

The application uses several volumes for data persistence:

- `./data:/app/data` - Application data (logs, user data, history)
- `./config:/app/config` - Configuration files
- `gaja-cache:/app/.cache` - Application cache
- `gaja-models:/app/.hf_cache` - Downloaded AI models

## Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|---------------|---------------|---------|
| API Server | 5000 | 5000 | REST API |
| Web UI | 8080 | 8080 | Web Interface |
| Frontend Dev | 3000 | 3000 | Development Server |
| PostgreSQL | 5432 | 5432 | Database |
| Redis | 6379 | 6379 | Cache |
| Nginx | 80/443 | 80/443 | Reverse Proxy |

## Environment Variables

Key environment variables you should configure:

### Required
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GAJA_SECRET_KEY` - Application secret key

### Optional
- `GAJA_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `GAJA_HOST` - Host to bind to (default: 0.0.0.0)
- `GAJA_PORT` - Port to bind to (default: 5000)
- `CUDA_VISIBLE_DEVICES` - GPU devices to use
- `DB_PASSWORD` - Database password for PostgreSQL

## Health Checks

All services include health checks:

```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs gaja-server-cpu

# Follow logs in real-time
docker-compose logs -f gaja-server-cpu
```

## Common Commands

### Start Services
```bash
# Start in background
docker-compose up -d

# Start with logs
docker-compose up

# Start specific service
docker-compose up gaja-server-cpu
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop and remove images
docker-compose down --rmi all
```

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs gaja-server-cpu

# Follow logs
docker-compose logs -f
```

### Execute Commands
```bash
# Run commands in running container
docker-compose exec gaja-server-cpu python --version

# Run one-off commands
docker-compose run --rm gaja-server-cpu python -c "print('Hello World')"
```

## Development Workflow

### 1. Start Development Environment
```bash
docker-compose --profile development up -d
```

### 2. Access Development Tools
```bash
# Run tests
docker-compose exec gaja-dev poetry run pytest

# Run linting
docker-compose exec gaja-dev poetry run ruff check .

# Run formatting
docker-compose exec gaja-dev poetry run black .

# Interactive shell
docker-compose exec gaja-dev bash
```

### 3. Install New Dependencies
```bash
# Add new package
docker-compose exec gaja-dev poetry add package-name

# Rebuild if needed
docker-compose build gaja-dev
```

## Troubleshooting

### Common Issues

1. **Permission denied errors**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER ./data
   ```

2. **Port already in use**
   ```bash
   # Check what's using the port
   sudo netstat -tulpn | grep :5000
   
   # Change port in docker-compose.yml or .env
   ```

3. **Out of disk space**
   ```bash
   # Clean up Docker
   docker system prune -a
   
   # Remove unused volumes
   docker volume prune
   ```

4. **GPU not detected**
   ```bash
   # Install NVIDIA Docker runtime
   # https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
   
   # Test GPU access
   docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu20.04 nvidia-smi
   ```

### Debug Mode

Enable debug mode for more verbose logging:

```bash
# Set environment variable
export GAJA_DEBUG=true

# Or in .env file
GAJA_DEBUG=true
GAJA_LOG_LEVEL=DEBUG
```

## Security Considerations

### Production Deployment

1. **Change default passwords**
   - Update `GAJA_SECRET_KEY`
   - Update `DB_PASSWORD`
   - Update `REDIS_PASSWORD`

2. **Use HTTPS**
   - Configure SSL certificates in nginx
   - Update nginx.conf for HTTPS

3. **Network security**
   - Use Docker networks
   - Restrict port exposure
   - Configure firewall rules

4. **Regular updates**
   - Update base images regularly
   - Keep dependencies updated
   - Monitor security advisories

## Performance Tuning

### CPU Optimization
- Adjust `WORKER_PROCESSES` based on CPU cores
- Configure memory limits
- Use volume caching for models

### GPU Optimization
- Set `CUDA_VISIBLE_DEVICES` for specific GPUs
- Monitor GPU memory usage
- Use tensor parallelism for large models

### Database Tuning
- Configure PostgreSQL settings for your workload
- Use connection pooling
- Regular maintenance and vacuuming

## Monitoring

### Container Metrics
```bash
# Resource usage
docker stats

# System events
docker events

# Container inspection
docker inspect container_name
```

### Application Metrics
- Health check endpoints: `/health`
- Metrics endpoint: `/metrics` (if configured)
- Log aggregation with ELK stack or similar

## Backup and Recovery

### Data Backup
```bash
# Backup volumes
docker run --rm -v gaja-models:/data -v $(pwd):/backup ubuntu tar czf /backup/models-backup.tar.gz /data

# Backup database
docker-compose exec database pg_dump -U gaja gaja > backup.sql
```

### Restore
```bash
# Restore volumes
docker run --rm -v gaja-models:/data -v $(pwd):/backup ubuntu tar xzf /backup/models-backup.tar.gz -C /

# Restore database
docker-compose exec -T database psql -U gaja gaja < backup.sql
```
