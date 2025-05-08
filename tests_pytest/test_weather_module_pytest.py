import pytest
from modules.weather_module import register

def test_weather_register_returns_handler():
    info = register()
    assert 'handler' in info
    assert callable(info['handler'])
    assert 'description' in info
    assert isinstance(info['description'], str)

# Example test for the handler (stub, adjust as needed)
def test_weather_handler_basic():
    info = register()
    handler = info['handler']
    # Simulate a simple weather query (adjust params as needed for your implementation)
    result = handler('pogoda Warszawa')
    assert isinstance(result, (str, dict))
    # Optionally check for expected keys if dict
    if isinstance(result, dict):
        assert 'weather' in result or 'summary' in result
