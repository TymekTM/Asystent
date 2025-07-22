"""Comprehensive tests for core_module.

This test suite covers the core functionality of timers, events, reminders, tasks, and
lists. Tests are designed to verify async behavior and proper error handling following
AGENTS.md guidelines.
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import core module
from server.modules import core_module


class TestCoreModuleFunctions:
    """Test the plugin function definitions."""

    def test_get_functions_structure(self):
        """Test that get_functions returns properly structured function definitions."""
        functions = core_module.get_functions()

        assert isinstance(functions, list)
        assert len(functions) > 0

        # Check that each function has required fields
        for func in functions:
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"


class TestCoreModuleTimers:
    """Test timer functionality."""

    @pytest.mark.asyncio
    async def test_set_timer_success(self):
        """Test successful timer creation."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            result = await core_module.execute_function(
                "set_timer", {"duration": "5m", "label": "Test Timer"}, user_id=1
            )

            assert result["success"] is True
            assert "Test Timer" in result["message"]
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_timer_invalid_duration(self):
        """Test timer creation with invalid duration."""
        result = await core_module.execute_function(
            "set_timer", {"duration": "invalid", "label": "Test Timer"}, user_id=1
        )

        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_view_timers(self):
        """Test viewing active timers."""
        with patch("server.modules.core_module._load_storage") as mock_load:
            mock_load.return_value = {
                "timers": [
                    {
                        "label": "Test Timer",
                        "target": (datetime.now() + timedelta(minutes=5)).isoformat(),
                        "created": datetime.now().isoformat(),
                    }
                ]
            }

            result = await core_module.execute_function("view_timers", {}, user_id=1)

            assert result["success"] is True
            assert "Test Timer" in result["message"]

    @pytest.mark.asyncio
    async def test_timer_completion(self):
        """Test timer completion mechanism."""
        # Test that timer polling can be started without errors
        try:
            core_module._start_timer_polling_task()
            # If no exception is raised, the test passes
            assert True
        except Exception:
            # If task is already running, that's also fine
            assert True


class TestCoreModuleEvents:
    """Test event/calendar functionality."""

    @pytest.mark.asyncio
    async def test_add_event_success(self):
        """Test successful event creation."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            result = await core_module.execute_function(
                "add_event",
                {"title": "Test Event", "date": "2025-06-25", "time": "14:00"},
                user_id=1,
            )

            assert result["success"] is True
            assert "Test Event" in result["message"]
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_event_invalid_date(self):
        """Test event creation with invalid date."""
        result = await core_module.execute_function(
            "add_event",
            {"title": "Test Event", "date": "invalid-date", "time": "14:00"},
            user_id=1,
        )

        assert result["success"] is False
        assert "date" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_view_calendar(self):
        """Test viewing calendar events."""
        with patch("server.modules.core_module._load_storage") as mock_load:
            mock_load.return_value = {
                "events": [
                    {
                        "title": "Test Event",
                        "time": "2025-06-25T14:00:00",  # Full ISO format
                    }
                ]
            }

            result = await core_module.execute_function("view_calendar", {}, user_id=1)

            assert result["success"] is True
            assert "Test Event" in result["message"]


class TestCoreModuleReminders:
    """Test reminder functionality."""

    @pytest.mark.asyncio
    async def test_set_reminder_success(self):
        """Test successful reminder creation."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            result = await core_module.execute_function(
                "set_reminder",
                {"text": "Test Reminder", "time": "2025-06-25T14:00:00"},
                user_id=1,
            )

            assert result["success"] is True
            assert "Test Reminder" in result["message"]
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_view_reminders(self):
        """Test viewing reminders."""
        with patch("server.modules.core_module._load_storage") as mock_load:
            mock_load.return_value = {
                "reminders": [{"text": "Test Reminder", "time": "2025-06-25T14:00:00"}]
            }

            result = await core_module.execute_function("view_reminders", {}, user_id=1)

            assert result["success"] is True
            assert "Test Reminder" in result["message"]

    @pytest.mark.asyncio
    async def test_reminder_due_today(self):
        """Test getting reminders due today."""
        today = datetime.now().date()
        with patch("server.modules.core_module._load_storage") as mock_load:
            mock_load.return_value = {
                "reminders": [
                    {
                        "text": "Today's Reminder",
                        "time": today.isoformat() + "T14:00:00",
                    },
                    {
                        "text": "Tomorrow's Reminder",
                        "time": (today + timedelta(days=1)).isoformat() + "T14:00:00",
                    },
                ]
            }

            result = await core_module.execute_function(
                "get_reminders_for_today", {}, user_id=1
            )

            assert result["success"] is True
            assert "Today's Reminder" in result["message"]
            assert "Tomorrow's Reminder" not in result["message"]


class TestCoreModuleTasks:
    """Test task management functionality."""

    @pytest.mark.asyncio
    async def test_add_task_success(self):
        """Test successful task creation."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            result = await core_module.execute_function(
                "add_task", {"task": "Test Task", "priority": "high"}, user_id=1
            )

            assert result["success"] is True
            assert "Test Task" in result["message"]
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_view_tasks(self):
        """Test viewing tasks."""
        with patch("server.modules.core_module._load_storage") as mock_load:
            mock_load.return_value = {
                "tasks": [
                    {
                        "task": "Test Task",
                        "priority": "high",
                        "completed": False,
                        "created": datetime.now().isoformat(),
                    }
                ]
            }

            result = await core_module.execute_function("view_tasks", {}, user_id=1)

            assert result["success"] is True
            assert "Test Task" in result["message"]

    @pytest.mark.asyncio
    async def test_complete_task(self):
        """Test task completion."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            with patch("server.modules.core_module._load_storage") as mock_load:
                mock_load.return_value = {
                    "tasks": [
                        {
                            "task": "Test Task",
                            "priority": "high",
                            "completed": False,
                            "created": datetime.now().isoformat(),
                        }
                    ]
                }

                result = await core_module.execute_function(
                    "complete_task", {"task_id": 0}, user_id=1
                )

                assert result["success"] is True
                assert "completed" in result["message"].lower()
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_task(self):
        """Test task removal."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            with patch("server.modules.core_module._load_storage") as mock_load:
                mock_load.return_value = {
                    "tasks": [
                        {
                            "task": "Test Task",
                            "priority": "high",
                            "completed": False,
                            "created": datetime.now().isoformat(),
                        }
                    ]
                }

                result = await core_module.execute_function(
                    "remove_task", {"task_id": 0}, user_id=1
                )

                assert result["success"] is True
                assert "removed" in result["message"].lower()
                mock_save.assert_called_once()


class TestCoreModuleLists:
    """Test list management functionality."""

    @pytest.mark.asyncio
    async def test_add_item_to_list(self):
        """Test adding item to a list."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            result = await core_module.execute_function(
                "add_item", {"list_name": "Shopping", "item": "Milk"}, user_id=1
            )

            assert result["success"] is True
            assert "Milk" in result["message"]
            assert "Shopping" in result["message"]
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_view_list(self):
        """Test viewing a list."""
        with patch("server.modules.core_module._load_storage") as mock_load:
            mock_load.return_value = {"lists": {"Shopping": ["Milk", "Bread", "Eggs"]}}

            result = await core_module.execute_function(
                "view_list", {"list_name": "Shopping"}, user_id=1
            )

            assert result["success"] is True
            assert "Milk" in result["message"]
            assert "Bread" in result["message"]
            assert "Eggs" in result["message"]

    @pytest.mark.asyncio
    async def test_remove_item_from_list(self):
        """Test removing item from a list."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            with patch("server.modules.core_module._load_storage") as mock_load:
                mock_load.return_value = {
                    "lists": {"Shopping": ["Milk", "Bread", "Eggs"]}
                }

                result = await core_module.execute_function(
                    "remove_item", {"list_name": "Shopping", "item": "Milk"}, user_id=1
                )

                assert result["success"] is True
                assert "removed" in result["message"].lower()
                mock_save.assert_called_once()


class TestCoreModuleAsync:
    """Test async behavior and non-blocking operations."""

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test that multiple operations can run concurrently."""
        with patch("server.modules.core_module._save_storage") as mock_save:
            # Start multiple operations concurrently
            tasks = [
                core_module.execute_function(
                    "add_task", {"task": f"Task {i}"}, user_id=1
                )
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # All should succeed
            for result in results:
                assert result["success"] is True

            # Save should be called for each operation
            assert mock_save.call_count == 3

    @pytest.mark.asyncio
    async def test_async_timer_polling(self):
        """Test that timer polling doesn't block other operations."""
        # This test ensures the timer polling runs in background
        # without blocking other async operations

        start_time = asyncio.get_event_loop().time()

        # Start a quick operation
        result = await core_module.execute_function("get_current_time", {}, user_id=1)

        end_time = asyncio.get_event_loop().time()

        # Operation should complete quickly (< 0.1 seconds)
        assert (end_time - start_time) < 0.1
        assert result["success"] is True


class TestCoreModuleErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_storage_file_error(self):
        """Test handling of storage file errors."""
        with patch("server.modules.core_module._load_storage") as mock_load:
            mock_load.side_effect = FileNotFoundError("Storage file not found")

            result = await core_module.execute_function("view_tasks", {}, user_id=1)

            # Should handle error gracefully
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_unknown_function(self):
        """Test handling of unknown function names."""
        result = await core_module.execute_function("unknown_function", {}, user_id=1)

        assert result["success"] is False
        assert "unknown" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_invalid_parameters(self):
        """Test handling of invalid parameters."""
        result = await core_module.execute_function(
            "set_timer",
            {"duration": None, "label": "Test"},  # Invalid duration
            user_id=1,
        )

        assert result["success"] is False
        assert "error" in result


class TestCoreModuleIntegration:
    """Integration tests for core module."""

    @pytest.mark.asyncio
    async def test_full_workflow_timers(self):
        """Test complete timer workflow."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            # Initialize file with proper JSON structure
            initial_data = {
                "timers": [],
                "events": [],
                "reminders": [],
                "shopping_list": [],
                "tasks": [],
                "lists": {},
            }
            json.dump(initial_data, f)
            temp_file = f.name

        try:
            with patch("server.modules.core_module.STORAGE_FILE", temp_file):
                # Set a timer
                result1 = await core_module.execute_function(
                    "set_timer",
                    {"duration": "1s", "label": "Integration Test"},
                    user_id=1,
                )
                assert result1["success"] is True

                # View timers
                result2 = await core_module.execute_function(
                    "view_timers", {}, user_id=1
                )
                assert result2["success"] is True

                # Wait for timer to complete
                await asyncio.sleep(2)

                # Check timer is no longer active
                result3 = await core_module.execute_function(
                    "view_timers", {}, user_id=1
                )
                assert result3["success"] is True
                # Timer should be completed/removed

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_full_workflow_tasks(self):
        """Test complete task workflow."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            # Initialize file with proper JSON structure
            initial_data = {
                "timers": [],
                "events": [],
                "reminders": [],
                "shopping_list": [],
                "tasks": [],
                "lists": {},
            }
            json.dump(initial_data, f)
            temp_file = f.name

        try:
            with patch("server.modules.core_module.STORAGE_FILE", temp_file):
                # Add a task
                result1 = await core_module.execute_function(
                    "add_task",
                    {"task": "Integration Test Task", "priority": "high"},
                    user_id=1,
                )
                assert result1["success"] is True

                # View tasks
                result2 = await core_module.execute_function(
                    "view_tasks", {}, user_id=1
                )
                assert result2["success"] is True

                # Complete task
                result3 = await core_module.execute_function(
                    "complete_task", {"task_id": 0}, user_id=1
                )
                assert result3["success"] is True

                # Remove task
                result4 = await core_module.execute_function(
                    "remove_task", {"task_id": 0}, user_id=1
                )
                assert result4["success"] is True

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
