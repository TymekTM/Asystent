"""Test Plugin Module for GAJA Assistant Basic test plugin to verify plugin system
functionality."""


class TestModule:
    """Basic test module for plugin system testing."""

    def __init__(self):
        self.name = "Test Module"
        self.version = "1.0.0"
        self.description = "Test plugin for production tests"

    def get_commands(self):
        """Return available commands."""
        return {
            "test": {
                "description": "Run test command",
                "usage": "test",
                "function": self.test_command,
            }
        }

    def test_command(self, query=""):
        """Test command function."""
        return {
            "response": "Test command executed successfully",
            "status": "success",
            "data": {"query": query, "module": self.name, "version": self.version},
        }

    def is_active(self):
        """Check if module is active."""
        return True


# Module interface for GAJA
def get_module():
    """Return module instance."""
    return TestModule()


def get_commands():
    """Return available commands."""
    module = TestModule()
    return module.get_commands()
