# Tests Directory

This directory contains all testing utilities and scripts for GAJA Assistant.

## Structure

- **`performance/`** - Performance and load testing scripts
- **`integration/`** - Integration tests between components  
- **`debug/`** - Debug utilities and diagnostic tools
- **`../tests_pytest/`** - PyTest unit tests
- **`../tests_unit/`** - Legacy unit tests

## Quick Start

### Performance Tests
```bash
cd tests/performance
python concurrent_users_test.py    # Full load testing
python quick_perf_test.py          # Quick performance check
```

### Integration Tests
```bash
cd tests/integration
python test_client_integration.py  # Test client compatibility
```

### Debug Tools
```bash
cd tests/debug
python debug_tts.py               # Debug TTS providers
```

## Test Results

Test reports and summaries are stored in the `../reports/` directory.

---
*Tests organized on June 10, 2025*
