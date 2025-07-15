import sys
from pathlib import Path
import asyncio
from datetime import datetime, timedelta
from unittest import mock

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "server"))
from server.server_main import ServerApp

@pytest.mark.asyncio
async def test_get_status_summary(monkeypatch):
    app = ServerApp()
    app.start_time = datetime.now() - timedelta(seconds=120)
    app.connection_manager.active_connections = {"u1": object(), "u2": object()}

    class DummyProcess:
        def memory_info(self):
            return mock.Mock(rss=50 * 1024 * 1024)

    monkeypatch.setattr("psutil.Process", lambda: DummyProcess())
    monkeypatch.setattr("psutil.cpu_percent", lambda interval=None: 12.5)

    summary = app.get_status_summary()
    assert summary["connected_users"] == 2
    assert summary["memory_mb"] == 50
    assert summary["cpu_percent"] == 12.5
    assert summary["uptime_seconds"] >= 120
