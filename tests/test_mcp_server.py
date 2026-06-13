"""Unit tests for ``mcp_server.py`` — no live Ableton connection required.

These tests exercise:
  * ``DESTRUCTIVE_TOOLS`` dictionary completeness
  * Dry-run interception (returns a preview, never calls TCP)
  * Dry-run stripping before forwarding to LiveAgent
  * Batch dry-run previews
  * eval/exec gating behind ``LIVEAGENT_ENABLE_UNSAFE``
"""

import json
import os

import pytest

import mcp_server
from mcp_server import call_tool

# ── Helpers ──────────────────────────────────────────────────────────────────

async def _call(name, **kwargs):
    """Call the MCP ``call_tool`` handler and parse the JSON response."""
    result = await call_tool(name, kwargs)
    return json.loads(result[0].text)


# ── DESTRUCTIVE_TOOLS ────────────────────────────────────────────────────────

EXPECTED_DESTRUCTIVE_TOOLS = {
    "delete_clip",
    "clear_clip_notes",
    "set_parameter_value",
    "load_device",
    "load_sample_to_pad",
    "set_clip_properties",
    "set_clip_warp",
    "write_midi_notes",
    "write_clip_automation",
    "batch",
}


def test_destructive_tools_dict():
    """All destructive operations are registered in ``DESTRUCTIVE_TOOLS``."""
    assert isinstance(mcp_server.DESTRUCTIVE_TOOLS, dict)
    # Every expected operation is present.
    for op in EXPECTED_DESTRUCTIVE_TOOLS:
        assert op in mcp_server.DESTRUCTIVE_TOOLS, f"Missing destructive tool: {op}"
    # Each value is a callable lambda.
    for name, preview_fn in mcp_server.DESTRUCTIVE_TOOLS.items():
        assert callable(preview_fn), f"Preview for '{name}' is not callable"


# ── Dry-run interception ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dry_run_intercepts_delete_clip(mock_send):
    """``delete_clip`` with ``dry_run=True`` returns a preview and never hits TCP."""
    data = await _call("delete_clip", track_index=0, slot_index=2, dry_run=True)

    assert data["dry_run"] is True
    assert data["safe"] is True
    assert "Delete" in data["would_do"]
    assert "Track 0" in data["target"]
    assert "Slot 2" in data["target"]
    # The TCP send function must NOT have been called.
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_intercepts_set_parameter_value(mock_send):
    """``set_parameter_value`` with ``dry_run=True`` returns a preview."""
    data = await _call(
        "set_parameter_value",
        track_index=0,
        device_index=0,
        parameter_index=3,
        value=0.75,
        dry_run=True,
    )

    assert data["dry_run"] is True
    assert data["safe"] is True
    assert "0.75" in data["would_do"]
    assert "Track 0" in data["target"]
    mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_strips_before_forwarding(mock_send):
    """When ``dry_run`` is False the flag is removed before forwarding to TCP."""
    await _call(
        "set_parameter_value",
        track_index=0,
        device_index=0,
        parameter_index=1,
        value=0.5,
        dry_run=False,
    )

    mock_send.assert_called_once()
    forwarded_args = mock_send.call_args
    forwarded_payload = forwarded_args[0][1]  # second positional arg (payload dict)

    assert "dry_run" not in forwarded_payload, (
        "dry_run must be stripped before forwarding to LiveAgent"
    )
    assert forwarded_payload["value"] == 0.5


@pytest.mark.asyncio
async def test_dry_run_strips_when_absent(mock_send):
    """Even without dry_run in args, forwarding works and no dry_run leaks."""
    await _call("delete_clip", track_index=3, slot_index=1)

    mock_send.assert_called_once()
    _, forwarded_payload = mock_send.call_args[0]
    assert "dry_run" not in forwarded_payload


@pytest.mark.asyncio
async def test_batch_dry_run(mock_send):
    """``batch`` with ``dry_run=True`` previews all commands without executing."""
    commands = [
        {"command": "create_midi_track", "payload": {"index": -1}},
        {"command": "create_session_clip", "payload": {"track_index": 0, "slot_index": 0}},
        {
            "command": "write_midi_notes",
            "payload": {
                "track_index": 0,
                "slot_index": 0,
                "notes": [{"pitch": 60, "start": 0, "duration": 0.25}],
            },
        },
    ]
    data = await _call("batch", commands=commands, dry_run=True)

    assert data["dry_run"] is True
    assert data["safe"] is True
    assert "3 commands" in data["would_do"]
    assert "create_midi_track" in data["target"]
    assert "create_session_clip" in data["target"]
    assert "write_midi_notes" in data["target"]
    mock_send.assert_not_called()


# ── eval / exec env-var gating ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_eval_disabled_by_default(mock_send_eval, env_cleanup):
    """eval returns an error when ``LIVEAGENT_ENABLE_UNSAFE`` is not set."""
    assert os.environ.get("LIVEAGENT_ENABLE_UNSAFE") is None

    data = await _call("eval", expr="1 + 1")

    assert "error" in data
    assert "disabled" in data["error"].lower()
    # The mock was still called (mcp_server forwards eval/exec).
    mock_send_eval.assert_called_once()


@pytest.mark.asyncio
async def test_eval_enabled_with_env_var(mock_send_eval, monkeypatch):
    """eval succeeds when ``LIVEAGENT_ENABLE_UNSAFE=1`` is set."""
    monkeypatch.setenv("LIVEAGENT_ENABLE_UNSAFE", "1")

    data = await _call("eval", expr="1 + 1")

    assert "error" not in data
    assert data.get("result") == 2
    mock_send_eval.assert_called_once()


@pytest.mark.asyncio
async def test_exec_disabled_by_default(mock_send_eval, env_cleanup):
    """exec returns an error when ``LIVEAGENT_ENABLE_UNSAFE`` is not set."""
    data = await _call("exec", stmt="x = 1")

    assert "error" in data
    assert "disabled" in data["error"].lower()


@pytest.mark.asyncio
async def test_exec_enabled_with_env_var(mock_send_eval, monkeypatch):
    """exec succeeds when ``LIVEAGENT_ENABLE_UNSAFE=1`` is set."""
    monkeypatch.setenv("LIVEAGENT_ENABLE_UNSAFE", "1")

    data = await _call("exec", stmt="x = 1")

    assert "error" not in data
