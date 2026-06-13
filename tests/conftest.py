"""Shared test fixtures for live-agent-remote MCP server tests.

All tests mock the TCP send function so no actual Ableton Live connection
is required.
"""

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_send(monkeypatch):
    """Patch ``mcp_server.liveagent_send`` to return a generic success.

    The returned MagicMock records every call so tests can assert on the
    command name and forwarded arguments.
    """
    mock = MagicMock(return_value={"status": "ok"})
    monkeypatch.setattr("mcp_server.liveagent_send", mock)
    return mock


@pytest.fixture
def mock_send_eval(monkeypatch):
    """Mock ``liveagent_send`` that simulates LiveAgent's env-var gate.

    This mirrors the behaviour of ``LiveAgent._eval`` / ``_exec``: when
    ``LIVEAGENT_ENABLE_UNSAFE`` is not ``"1"`` the call returns an error
    dict; otherwise it returns a normal result.
    """
    def _send(command, payload=None):
        if command in ("eval", "exec"):
            if os.environ.get("LIVEAGENT_ENABLE_UNSAFE", "0") != "1":
                return {
                    "error": (
                        f"{command} is disabled. "
                        "Set LIVEAGENT_ENABLE_UNSAFE=1 environment variable to enable."
                    ),
                    "security": "This command allows arbitrary code execution "
                    "and is disabled by default.",
                }
            return {"result": 2}
        return {"status": "ok", "command": command}

    mock = MagicMock(side_effect=_send)
    monkeypatch.setattr("mcp_server.liveagent_send", mock)
    return mock


@pytest.fixture
def env_cleanup(monkeypatch):
    """Ensure ``LIVEAGENT_ENABLE_UNSAFE`` is unset for the test."""
    monkeypatch.delenv("LIVEAGENT_ENABLE_UNSAFE", raising=False)
