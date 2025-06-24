# Issues to Track

## TODO Items Found During Cleanup

### 1. Simple Wakeword Detector Async Pattern

**File:** `client/audio_modules/simple_wakeword_detector.py:114`
**Issue:** Replace with proper async/await pattern
**Priority:** Medium
**Description:** The wakeword detector needs to be refactored to use proper async patterns instead of blocking operations.

### 2. App Version Configuration

**File:** `dependency_manager.py:218`
**Issue:** Get app version from config instead of hardcoding
**Priority:** Low
**Description:** App version should be read from configuration file or package metadata instead of being hardcoded.

## Completed Cleanup Tasks

- [x] Archived old files (\_old.py, \_new.py) to archive/ folder
- [x] Merged duplicate GitHub Actions workflows (removed ci-cd-fixed.yml)
- [x] Migrated requests → httpx.AsyncClient in server/ai_module.py and test files
- [x] Replaced threading.Lock → asyncio.Lock in multiple modules
- [x] Fixed psutil.cpu_percent(interval=1) → interval=None with async sleep
- [x] Replaced print() statements with logger calls in production code
- [x] Updated pytest.ini with coverage and strict asyncio mode
- [x] Updated CI/CD workflow with strict linting (ruff --select F,E,I,N, mypy --strict)
- [x] Enhanced CORS security with ALLOWED_ORIGINS environment variable whitelist
- [x] Added WebSocket version handshake validation
- [x] Implemented pydantic models for JSON schema validation
- [x] Added try/catch for json.loads() in AI module with error logging
- [x] Archived duplicate compliance reports
- [x] Added coverage and status badges to README.md
- [x] Made Docker CUDA tag configurable via CUDA_TAG build argument
- [x] Updated all async locks from threading.Lock to asyncio.Lock
- [x] Added httpx client cleanup method in AI module
