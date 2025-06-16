# Migration Guide - Gaja Assistant Code Restructure

This guide helps you migrate from the old project structure to the new Poetry + Docker + CI/CD setup.

## 🚀 What Changed

### Repository & Code Hygiene Improvements

1. **✅ New Project Structure**: Moved code to `src/` directory with proper packaging
2. **✅ Poetry Configuration**: Replaced manual requirements.txt with pyproject.toml
3. **✅ Git LFS Setup**: Large binary files now tracked with Git LFS
4. **✅ Pre-commit Hooks**: Automated code formatting and linting
5. **✅ Docker Support**: Multi-stage Dockerfile with CPU/GPU variants
6. **✅ CI/CD Pipeline**: GitHub Actions for automated testing and builds

## 📦 Migration Steps

### Step 1: Install Dependencies

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install

# Install development dependencies
poetry install --with dev

# Install pre-commit hooks
poetry run pre-commit install
```

### Step 2: Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your actual API keys and settings
# At minimum, configure:
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY  
# - DEEPSEEK_API_KEY
# - GAJA_SECRET_KEY
```

### Step 3: Data Migration

Your existing data should remain compatible, but consider:

```bash
# Backup your current data
cp -r data/ data_backup/
cp -r user_data/ user_data_backup/
cp *.db *.db.backup

# Models will be re-downloaded to .hf_cache/ 
# (old models in various locations will be ignored)
```

### Step 4: Update Development Workflow

#### Old Way:
```bash
python client_main.py
python server_main.py
```

#### New Way:
```bash
# Using Poetry
poetry run python -m gaja_client.main
poetry run python -m gaja_server.main

# Using Docker
docker-compose up -d
```

### Step 5: Git LFS Setup

If you're working with the repository:

```bash
# Install Git LFS (if not already installed)
git lfs install

# Track large files (already configured in .gitattributes)
git lfs track "*.bin"
git lfs track "*.model"
# etc.

# Migrate existing large files to LFS
git lfs migrate import --include="*.bin,*.model,*.dll,*.exe"
```

## 🐳 Docker Usage

### Quick Start
```bash
# CPU-only deployment
docker-compose up -d

# GPU-enabled deployment
docker-compose --profile gpu up -d

# Development environment
docker-compose --profile development up -d
```

### Available Profiles
- `default` / `cpu`: Standard CPU deployment
- `gpu`: NVIDIA GPU-accelerated deployment  
- `development`: Development environment with live reloading
- `production`: Full stack with database, Redis, Nginx

See [README_DOCKER.md](README_DOCKER.md) for detailed Docker usage.

## 🔧 Development Tools

### Code Quality (Pre-commit Hooks)
```bash
# Manual run of all hooks
poetry run pre-commit run --all-files

# Individual tools
poetry run black .           # Format code
poetry run ruff check .      # Lint code  
poetry run mypy src/         # Type checking
poetry run pytest           # Run tests
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/test_specific.py

# Run tests in parallel
poetry run pytest -n auto
```

## 📁 Directory Structure Changes

### Old Structure:
```
├── client_main.py
├── server_main.py  
├── ai_module.py
├── assistant.py
├── audio_modules/
├── modules/
└── requirements.txt
```

### New Structure:
```
├── src/
│   ├── gaja_client/
│   ├── gaja_server/
│   └── gaja_core/
├── docker/
├── .github/workflows/
├── pyproject.toml
├── docker-compose.yml
└── .pre-commit-config.yaml
```

## 🔄 CI/CD Pipeline

The new GitHub Actions workflow automatically:

1. **Linting & Formatting**: Black, Ruff, MyPy
2. **Testing**: Pytest with coverage on Ubuntu/Windows
3. **Security Scanning**: Safety, Bandit
4. **Docker Building**: Multi-architecture images
5. **Release Building**: Standalone executables

### Triggering CI/CD
```bash
# Push to trigger CI
git add .
git commit -m "feat: your changes"
git push

# Create release to trigger full build
git tag v1.0.0
git push --tags
```

## ⚠️ Breaking Changes

### Import Changes
**Old imports:**
```python
from ai_module import AIModule
from assistant import Assistant
```

**New imports:**
```python
from gaja_core.ai_module import AIModule
from gaja_server.assistant import Assistant
```

### Configuration Changes
- Environment variables now use `GAJA_` prefix consistently
- Database configuration moved to environment variables
- Docker-specific configuration available

### Command Changes
**Old commands:**
```bash
python build.py
python client_main.py
```

**New commands:**
```bash
poetry run python build.py
poetry run python -m gaja_client.main
# Or with Docker:
docker-compose up gaja-client
```

## 🐛 Troubleshooting

### Common Issues

1. **"Module not found" errors**
   ```bash
   # Make sure you're using Poetry
   poetry run python your_script.py
   
   # Or activate the virtual environment
   poetry shell
   python your_script.py
   ```

2. **Large files not tracked by LFS**
   ```bash
   # Check LFS status
   git lfs ls-files
   
   # Migrate large files
   git lfs migrate import --include="*.bin"
   ```

3. **Docker permission issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER ./data
   
   # Or use rootless Docker
   ```

4. **Pre-commit hooks failing**
   ```bash
   # Update hooks
   poetry run pre-commit autoupdate
   
   # Skip hooks temporarily (not recommended)
   git commit --no-verify
   ```

### Getting Help

1. Check [README_DOCKER.md](README_DOCKER.md) for Docker-specific issues
2. Check [GitHub Issues](../../issues) for known problems
3. Review CI/CD logs in [GitHub Actions](../../actions)

## 🎯 Next Steps

After migration:

1. **Test thoroughly**: Run your existing workflows to ensure compatibility
2. **Update documentation**: Update any project-specific documentation  
3. **Train team**: Ensure all team members understand new workflows
4. **Monitor CI/CD**: Watch the first few CI runs to catch any issues
5. **Optimize**: Fine-tune Docker, pre-commit, and CI settings for your needs

## 📈 Benefits

After migration, you'll have:

- ✅ **Cleaner codebase** with proper structure and packaging
- ✅ **Automated quality checks** preventing bad code from being committed
- ✅ **Easy deployment** with Docker containers
- ✅ **Continuous integration** catching issues early
- ✅ **Better dependency management** with Poetry
- ✅ **Reduced repository size** with Git LFS
- ✅ **Professional development workflow** matching industry standards
