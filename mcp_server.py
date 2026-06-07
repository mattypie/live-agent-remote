#!/usr/bin/env python3
"""
LiveAgent MCP Server
====================
MCP (Model Context Protocol) server that wraps the LiveAgent Ableton Live
control surface. Allows any MCP-compatible AI agent (Claude Desktop, Cursor,
etc.) to control Ableton Live directly.

Transport: stdio

Usage in Claude Desktop config (claude_desktop_config.json):
{
  "mcpServers": {
    "ableton-live": {
      "command": "/path/to/live-agent-remote/.venv/bin/python3",
      "args": ["/path/to/live-agent-remote/mcp_server.py"]
    }
  }
}
"""

import json
import socket
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)

# ── LiveAgent TCP Client ──────────────────────────────────────

LIVEAGENT_HOST = "127.0.0.1"
LIVEAGENT_PORT = 8765


def liveagent_send(command: str, payload: dict | None = None) -> dict:
    """Send a single JSON command to LiveAgent and return the result."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((LIVEAGENT_HOST, LIVEAGENT_PORT))
        request = {"command": command}
        if payload:
            request["payload"] = payload
        sock.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode())

        buf = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break

        resp = json.loads(buf.decode().strip())
        if not resp.get("ok"):
            return {"error": resp.get("error", "Unknown error")}
        return resp.get("result", {})
    except ConnectionRefusedError:
        return {"error": "Cannot connect to Ableton Live. Is LiveAgent control surface active?"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        sock.close()


# ── MCP Server Definition ─────────────────────────────────────

app = Server("ableton-live-agent")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="ping",
            description="Check if Ableton Live is connected and responding via LiveAgent.",
        ),
        Tool(
            name="get_live_state",
            description="Get the full state of Ableton Live: tempo, tracks, scenes, playing status, selected track.",
        ),
        Tool(
            name="list_tracks",
            description="List all tracks in the current Ableton Live set with their devices, clips, and settings.",
        ),
        Tool(
            name="create_midi_track",
            description="Create a new MIDI track in Ableton Live.",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "Insert position (-1 = end)",
                        "default": -1,
                    },
                },
            },
        ),
        Tool(
            name="create_session_clip",
            description="Create a new MIDI clip in session view on a specific track and slot.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Target track index (0-based)"},
                    "slot_index": {"type": "integer", "description": "Target slot/scene index (0-based)"},
                    "length_beats": {"type": "number", "description": "Clip length in beats (default 16)", "default": 16},
                    "name": {"type": "string", "description": "Clip name"},
                    "replace": {"type": "boolean", "description": "Replace existing clip (default true)", "default": True},
                },
            },
        ),
        Tool(
            name="write_midi_notes",
            description="Write MIDI notes to a clip. Notes are specified as an array of {pitch, start, duration, velocity}.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index", "notes"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Target track index"},
                    "slot_index": {"type": "integer", "description": "Target slot index"},
                    "notes": {
                        "type": "array",
                        "description": "Array of note objects",
                        "items": {
                            "type": "object",
                            "required": ["pitch", "start", "duration"],
                            "properties": {
                                "pitch": {"type": "integer", "description": "MIDI note number (0-127)"},
                                "start": {"type": "number", "description": "Start time in beats"},
                                "duration": {"type": "number", "description": "Duration in beats"},
                                "velocity": {"type": "integer", "description": "Velocity 0-127 (default 96)"},
                            },
                        },
                    },
                },
            },
        ),
        Tool(
            name="read_clip_notes",
            description="Read all MIDI notes from a clip.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "slot_index": {"type": "integer"},
                    "length_beats": {"type": "number", "description": "Length to read in beats (default 16)", "default": 16},
                },
            },
        ),
        Tool(
            name="clear_clip_notes",
            description="Clear all notes from a MIDI clip.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "slot_index": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="list_devices",
            description="List all devices (plugins, built-in effects) on a track with their parameters.",
            inputSchema={
                "type": "object",
                "required": ["track_index"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Track index to inspect"},
                },
            },
        ),
        Tool(
            name="set_parameter_value",
            description="Set a parameter value on a device. Identify device/parameter by index or name.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "value"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "device_index": {"type": "integer", "description": "Device index on the track"},
                    "device_name": {"type": "string", "description": "Device name (alternative to index)"},
                    "parameter_index": {"type": "integer", "description": "Parameter index"},
                    "parameter_name": {"type": "string", "description": "Parameter name (alternative to index)"},
                    "value": {"type": "number", "description": "New parameter value"},
                },
            },
        ),
        Tool(
            name="write_clip_automation",
            description="Write automation envelope points to a clip for a specific device parameter.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index", "points"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "slot_index": {"type": "integer"},
                    "device_index": {"type": "integer"},
                    "device_name": {"type": "string"},
                    "parameter_index": {"type": "integer"},
                    "parameter_name": {"type": "string"},
                    "points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "time": {"type": "number", "description": "Time in beats"},
                                "value": {"type": "number", "description": "Parameter value"},
                            },
                        },
                    },
                    "step_duration": {"type": "number", "description": "Step duration in beats (default 0.25)", "default": 0.25},
                },
            },
        ),
        Tool(
            name="load_device",
            description="Load a plugin/device onto a track by searching Ableton's browser. Supports VST/AU plugins, built-in instruments, and effects.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "device_name"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Track to load the device onto"},
                    "device_name": {"type": "string", "description": "Name of the device/plugin to load (e.g. 'Massive', 'Reverb')"},
                    "browser_type": {
                        "type": "string",
                        "description": "Browser category: 'plug-in', 'instrument', 'audio_effect', 'midi_effect'",
                        "default": "plug-in",
                    },
                },
            },
        ),
        Tool(
            name="list_browser_devices",
            description="Search and list available devices/plugins from Ableton's browser. Use this to find what's installed before loading.",
            inputSchema={
                "type": "object",
                "properties": {
                    "browser_type": {
                        "type": "string",
                        "description": "Category: 'plug-in', 'instrument', 'audio_effect', 'midi_effect'",
                        "default": "plug-in",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (partial match, case-insensitive)",
                        "default": "",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default 100)",
                        "default": 100,
                    },
                },
            },
        ),
        Tool(
            name="create_audio_track",
            description="Create a new audio track in Ableton Live.",
            inputSchema={
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "Insert position (-1 = end)",
                        "default": -1,
                    },
                },
            },
        ),
        Tool(
            name="import_audio_clip",
            description="Import an audio file (wav, aiff, mp3, etc.) into a track slot. The file must exist on disk.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index", "file_path"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Target track index"},
                    "slot_index": {"type": "integer", "description": "Target slot index"},
                    "file_path": {"type": "string", "description": "Absolute path to audio file"},
                },
            },
        ),
        Tool(
            name="get_clip_info",
            description="Get detailed info about a clip: name, type (audio/MIDI), loop settings, warp, pitch, gain, file path, etc.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "slot_index": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="set_clip_properties",
            description="Set clip properties: name, color, loop start/end, start/end markers, pitch, gain.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "slot_index": {"type": "integer"},
                    "name": {"type": "string", "description": "Clip name"},
                    "color": {"type": "integer", "description": "Clip color (RGB int)"},
                    "looping": {"type": "boolean", "description": "Enable/disable loop"},
                    "loop_start": {"type": "number", "description": "Loop start in beats"},
                    "loop_end": {"type": "number", "description": "Loop end in beats"},
                    "start_marker": {"type": "number", "description": "Start marker in beats"},
                    "end_marker": {"type": "number", "description": "End marker in beats"},
                    "pitch_coarse": {"type": "integer", "description": "Pitch transpose (semitones, audio only)"},
                    "pitch_fine": {"type": "number", "description": "Fine pitch (cents, audio only)"},
                    "gain": {"type": "number", "description": "Clip gain (audio only)"},
                },
            },
        ),
        Tool(
            name="duplicate_clip",
            description="Duplicate a clip to another slot (same or different track).",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Source track"},
                    "slot_index": {"type": "integer", "description": "Source slot"},
                    "dest_track_index": {"type": "integer", "description": "Destination track (default: same)"},
                    "dest_slot_index": {"type": "integer", "description": "Destination slot (default: source+1)"},
                },
            },
        ),
        Tool(
            name="delete_clip",
            description="Delete a clip from a track slot.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "slot_index": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="set_clip_warp",
            description="Set warp properties on an audio clip. Warp modes: 0=beats, 1=tones, 2=texture, 3=re-pitch, 4=complex, 5=complex pro.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "slot_index": {"type": "integer"},
                    "warping": {"type": "boolean", "description": "Enable/disable warp"},
                    "warp_mode": {"type": "integer", "description": "0=beats, 1=tones, 2=texture, 3=re-pitch, 4=complex, 5=complex pro"},
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    args = arguments or {}
    result = liveagent_send(name, args)
    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


# ── Main ──────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
