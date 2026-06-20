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
import os
import socket
import sys

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

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

# Dry-run schema fragment. Auto-injected into every tool whose name appears
# in DESTRUCTIVE_TOOLS below, so dry_run no longer needs to be hand-written
# in each tool's inputSchema (see _inject_dry_run).
DRY_RUN_SCHEMA = {
    "type": "boolean",
    "description": "If true, return what would happen without executing. Use to preview destructive operations before running them.",
    "default": False,
}

# Registry of destructive tools and their dry-run preview lambdas.
# Membership here has two effects:
#   1. call_tool() intercepts dry_run=True for these names (preview only).
#   2. _inject_dry_run() adds the dry_run property to their inputSchema.
DESTRUCTIVE_TOOLS = {
    "delete_clip": lambda a: {
        "would_do": "Delete clip",
        "target": f"Track {a.get('track_index')} / Slot {a.get('slot_index')}",
    },
    "clear_clip_notes": lambda a: {
        "would_do": "Clear all MIDI notes from clip",
        "target": f"Track {a.get('track_index')} / Slot {a.get('slot_index')}",
    },
    "set_parameter_value": lambda a: {
        "would_do": f"Set parameter value to {a.get('value')}",
        "target": f"Track {a.get('track_index')} / Device {a.get('device_index', a.get('device_name', '?'))} / Param {a.get('parameter_index', a.get('parameter_name', '?'))}",
    },
    "load_device": lambda a: {
        "would_do": f"Load device '{a.get('device_name')}'",
        "target": f"Track {a.get('track_index')} ({a.get('browser_type', 'plug-in')})",
    },
    "load_sample_to_pad": lambda a: {
        "would_do": f"Load sample to pad {a.get('pad_index')}",
        "target": f"Track {a.get('track_index')} / Pad {a.get('pad_index')} / {a.get('file_path', '?')}",
    },
    "set_clip_properties": lambda a: {
        "would_do": "Set clip properties",
        "target": f"Track {a.get('track_index')} / Slot {a.get('slot_index')}",
    },
    "set_clip_warp": lambda a: {
        "would_do": "Set clip warp properties",
        "target": f"Track {a.get('track_index')} / Slot {a.get('slot_index')} warping={a.get('warping')} mode={a.get('warp_mode')}",
    },
    "write_midi_notes": lambda a: {
        "would_do": f"Write {len(a.get('notes', []))} MIDI notes",
        "target": f"Track {a.get('track_index')} / Slot {a.get('slot_index')}",
    },
    "write_clip_automation": lambda a: {
        "would_do": f"Write {len(a.get('points', []))} automation points",
        "target": f"Track {a.get('track_index')} / Slot {a.get('slot_index')}",
    },
    # ── Transport (destructive: they change playback/tempo/signature) ──
    "stop_all_clips": lambda a: {
        "would_do": "Stop all playing clips",
        "target": "All tracks",
    },
    "set_tempo": lambda a: {
        "would_do": f"Set tempo to {a.get('tempo')} BPM",
        "target": "Global transport",
    },
    "tap_tempo": lambda a: {
        "would_do": "Tap tempo",
        "target": "Global transport",
    },
    "set_time_signature": lambda a: {
        "would_do": f"Set time signature to {a.get('numerator', '?')}/{a.get('denominator', '?')}",
        "target": "Global transport",
    },
    "set_metronome": lambda a: {
        "would_do": f"Set metronome to {a.get('enabled')}",
        "target": "Global transport",
    },
    "set_overdub": lambda a: {
        "would_do": f"Set overdub to {a.get('enabled')}",
        "target": "Global transport",
    },
    "launch_scene": lambda a: {
        "would_do": f"Launch scene {a.get('scene_index')}",
        "target": f"Scene {a.get('scene_index')}",
    },
    "launch_clip": lambda a: {
        "would_do": f"Launch clip in Track {a.get('track_index')} / Slot {a.get('slot_index')}",
        "target": f"Track {a.get('track_index')} / Slot {a.get('slot_index')}",
    },
    "batch": lambda a: {
        "would_do": f"Execute {len(a.get('commands', []))} commands as single undo step",
        "target": ", ".join(c.get("command", "?") for c in a.get("commands", [])),
    },
}


def _inject_dry_run(tools: list[Tool]) -> list[Tool]:
    """Add the dry_run property to the inputSchema of every destructive tool.

    This keeps dry_run declared in exactly one place (DESTRUCTIVE_TOOLS
    membership) instead of being hand-written in each tool's schema.
    """
    for tool in tools:
        if tool.name in DESTRUCTIVE_TOOLS:
            schema = tool.inputSchema or {"type": "object"}
            props = dict(schema.get("properties") or {})
            props.setdefault("dry_run", DRY_RUN_SCHEMA)
            schema = {**schema, "properties": props}
            tool.inputSchema = schema
    return tools


def _build_tools() -> list[Tool]:
    """Define all MCP tools. dry_run is auto-injected by _inject_dry_run."""
    tools = [
        Tool(
            name="ping",
            description="Check if Ableton Live is connected and responding via LiveAgent.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_live_state",
            description="Get the full state of Ableton Live: tempo, tracks, scenes, playing status, selected track.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_tracks",
            description="List all tracks in the current Ableton Live set with their devices, clips, and settings.",
            inputSchema={"type": "object", "properties": {}},
        ),
        # ── Transport & Playback ──
        Tool(
            name="get_transport_state",
            description="Get transport state: tempo, playing status, time signature, metronome, overdub.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="start_playing",
            description="Start playback of the Ableton Live transport.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="stop_playing",
            description="Stop playback of the Ableton Live transport.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="stop_all_clips",
            description="Stop all currently playing clips in the session view.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="set_tempo",
            description="Set the project tempo (BPM).",
            inputSchema={
                "type": "object",
                "required": ["tempo"],
                "properties": {
                    "tempo": {"type": "number", "description": "Tempo in BPM (20-999)"},
                },
            },
        ),
        Tool(
            name="tap_tempo",
            description="Tap the tempo. Call repeatedly in rhythm to set the tempo by tapping.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="set_time_signature",
            description="Set the time signature (e.g. 4/4, 3/4, 6/8).",
            inputSchema={
                "type": "object",
                "properties": {
                    "numerator": {"type": "integer", "description": "Beats per bar (1-16)"},
                    "denominator": {"type": "integer", "description": "Note value (1, 2, 4, 8, or 16)"},
                },
            },
        ),
        Tool(
            name="set_metronome",
            description="Turn the metronome on or off.",
            inputSchema={
                "type": "object",
                "required": ["enabled"],
                "properties": {
                    "enabled": {"type": "boolean", "description": "True to enable, False to disable"},
                },
            },
        ),
        Tool(
            name="set_overdub",
            description="Enable or disable MIDI overdub recording (new notes added without replacing existing).",
            inputSchema={
                "type": "object",
                "required": ["enabled"],
                "properties": {
                    "enabled": {"type": "boolean", "description": "True to enable overdub, False to disable"},
                },
            },
        ),
        Tool(
            name="launch_scene",
            description="Launch (fire) a scene in session view, starting all clips in that row.",
            inputSchema={
                "type": "object",
                "required": ["scene_index"],
                "properties": {
                    "scene_index": {"type": "integer", "description": "Scene index to launch (0-based)"},
                },
            },
        ),
        Tool(
            name="launch_clip",
            description="Launch (fire) a clip in a specific track and session slot.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Target track index (0-based)"},
                    "slot_index": {"type": "integer", "description": "Session slot/scene index (0-based)"},
                },
            },
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
        Tool(
            name="analyze_and_warp",
            description="Analyze an audio clip for BPM and key, then auto-set warp markers. Pass detected BPM and key from the audio_analyzer tool. Sets warp on, warp mode, and appends key to clip name.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "slot_index"],
                "properties": {
                    "track_index": {"type": "integer"},
                    "slot_index": {"type": "integer"},
                    "bpm": {"type": "number", "description": "Detected BPM from audio_analyzer"},
                    "key": {"type": "string", "description": "Detected key (e.g. 'Fm', 'C')"},
                    "warp_mode": {"type": "integer", "description": "0=beats, 1=tones, 2=texture, 3=re-pitch, 4=complex (default), 5=complex pro", "default": 4},
                },
            },
        ),
        Tool(
            name="analyze_audio_file",
            description="Analyze an audio file on disk for BPM, musical key, duration, and beat positions. Uses librosa for signal analysis. Returns detailed info for auto-warping.",
            inputSchema={
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to audio file"},
                },
            },
        ),
        Tool(
            name="detect_pitch",
            description="Detect the fundamental pitch of a one-shot audio sample (kick, snare, etc). Returns note name, frequency, octave, duration, sample type classification (oneshot/short_loop/medium_loop/long_loop), and whether the sample is tonal or atonal.",
            inputSchema={
                "type": "object",
                "required": ["file_path"],
                "properties": {
                    "file_path": {"type": "string", "description": "Absolute path to audio file"},
                },
            },
        ),
        Tool(
            name="analyze_folder",
            description="Analyze all audio files in a folder for BPM, key, pitch, and sample type (oneshot/loop classification by duration). Returns results sorted by pitch (note number). Use mode='pitch' for quick one-shot sorting. Filter by sample_type to find only one-shots or only loops.",
            inputSchema={
                "type": "object",
                "required": ["folder_path"],
                "properties": {
                    "folder_path": {"type": "string", "description": "Absolute path to folder"},
                    "mode": {"type": "string", "description": "Analysis mode: 'full' (BPM+key+pitch), 'pitch', 'key', 'bpm'", "default": "full"},
                    "sample_type": {"type": "string", "description": "Filter by sample type: 'oneshot', 'short_loop', 'medium_loop', 'long_loop'. Omit for all.", "enum": ["oneshot", "short_loop", "medium_loop", "long_loop"]},
                },
            },
        ),
        Tool(
            name="find_compatible_samples",
            description="Find samples in a folder that are harmonically compatible with a target key using the Camelot Wheel. Perfect for finding kicks/snares that match your song's key.",
            inputSchema={
                "type": "object",
                "required": ["folder_path", "target_key"],
                "properties": {
                    "folder_path": {"type": "string", "description": "Absolute path to folder containing samples"},
                    "target_key": {"type": "string", "description": "Target key (e.g. 'Fm', 'C', 'Am')"},
                    "mode": {"type": "string", "description": "Analysis mode", "default": "full"},
                },
            },
        ),
        Tool(
            name="create_smart_folder",
            description="Create a smart folder in Ableton's browser with symlinks to samples that are harmonically compatible with a target key. The folder appears under User Library > Samples > NI Samples > _smart > [Key]. Use this so compatible samples show up directly in Ableton's browser.",
            inputSchema={
                "type": "object",
                "required": ["target_key"],
                "properties": {
                    "target_key": {"type": "string", "description": "Target key (e.g. 'Fm', 'C', 'Am')"},
                    "categories": {"type": "array", "items": {"type": "string"}, "description": "Sample categories to scan (e.g. ['Kick', 'Snare']). Default: all"},
                    "base_path": {"type": "string", "description": "Base NI Samples path. Default: auto-detected"},
                },
            },
        ),
        Tool(
            name="create_drum_rack",
            description="Create a MIDI track with a usable Drum Rack. By default loads 808 Core Kit.adg so pads 36-51 already have chains that samples can be replaced into. Set empty=true only when you explicitly want an empty Drum Rack.",
            inputSchema={
                "type": "object",
                "required": [],
                "properties": {
                    "track_index": {"type": "integer", "description": "Track index to create at. -1 = end of track list (default)"},
                    "name": {"type": "string", "description": "Track name (default: 'Drum Rack')"},
                    "kit_name": {"type": "string", "description": "Drum rack preset from Ableton's Drums browser root (default: '808 Core Kit.adg')", "default": "808 Core Kit.adg"},
                    "empty": {"type": "boolean", "description": "Load an empty Drum Rack instead of a kit template. Empty racks cannot receive samples until a pad chain exists.", "default": False},
                },
            },
        ),
        Tool(
            name="load_sample_to_pad",
            description="Load a browser-indexed sample file onto a Drum Rack pad by loading it as a Simpler then moving it into the pad chain. Requires a pad chain/template; create_drum_rack's default 808 kit provides pads 36-51. Pad index is MIDI note number: 36=C1 kick, 38=snare, 42=closed hat, 46=open hat.",
            inputSchema={
                "type": "object",
                "required": ["track_index", "pad_index", "file_path"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Track containing the Drum Rack"},
                    "pad_index": {"type": "integer", "description": "MIDI note number for the Drum Rack pad. Use 36-51 for the visible 4x4 pad bank; 36=C1 kick.", "default": 36},
                    "file_path": {"type": "string", "description": "Absolute path to a sample file that Ableton Browser can find/index"},
                    "drum_rack_index": {"type": "integer", "description": "Device index of Drum Rack (default: 0)", "default": 0},
                    "reset_effects": {"type": "boolean", "description": "Delete all devices in the pad chain before moving the new Simpler. If false, only the first instrument device is replaced and later effects are kept.", "default": False},
                },
            },
        ),
        Tool(
            name="inspect_drum_rack",
            description="Inspect a Drum Rack's pad structure. Returns pad names, active state, chain devices, and sample file paths for debugging.",
            inputSchema={
                "type": "object",
                "required": ["track_index"],
                "properties": {
                    "track_index": {"type": "integer", "description": "Track containing the Drum Rack"},
                    "drum_rack_index": {"type": "integer", "description": "Device index of Drum Rack (default: 0)", "default": 0},
                    "pad_range": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Pad range to inspect [start, end] (default: [0, 16])",
                        "default": [0, 16],
                    },
                },
            },
        ),
        Tool(
            name="eval",
            description="Evaluate a Python expression in LiveAgent's Ableton Live context. Returns the result. Available variables: Live, song, app, os, json. Use for read-only queries. SECURITY: Disabled by default. Set LIVEAGENT_ENABLE_UNSAFE=1 environment variable before launching Ableton to enable.",
            inputSchema={
                "type": "object",
                "required": ["expr"],
                "properties": {
                    "expr": {"type": "string", "description": "Python expression to evaluate"},
                },
            },
        ),
        Tool(
            name="exec",
            description="Execute a Python statement in LiveAgent's Ableton Live context. Available variables: Live, song, app, os, json. Use for mutations. SECURITY: Disabled by default. Set LIVEAGENT_ENABLE_UNSAFE=1 environment variable before launching Ableton to enable.",
            inputSchema={
                "type": "object",
                "required": ["stmt"],
                "properties": {
                    "stmt": {"type": "string", "description": "Python statement to execute"},
                },
            },
        ),
        Tool(
            name="batch",
            description="Execute multiple LiveAgent commands as a single undo step. All operations can be undone with one Ctrl+Z. Stops on first error but keeps the undo group intact (user can undo everything done so far). Example: commands=[{'command':'create_midi_track','payload':{'index':-1}}, {'command':'create_session_clip','payload':{'track_index':0,'slot_index':0}}]",
            inputSchema={
                "type": "object",
                "required": ["commands"],
                "properties": {
                    "commands": {
                        "type": "array",
                        "description": "List of command objects to execute in order",
                        "items": {
                            "type": "object",
                            "required": ["command"],
                            "properties": {
                                "command": {"type": "string", "description": "LiveAgent command name (e.g. 'create_midi_track', 'write_midi_notes')"},
                                "payload": {"type": "object", "description": "Command arguments"},
                            },
                        },
                    },
                },
            },
        ),
    ]
    return _inject_dry_run(tools)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return all MCP tools with dry_run auto-injected for destructive ones."""
    return _build_tools()


@app.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    args = arguments or {}

    # ── Dry run interception ──
    if args.get("dry_run") and name in DESTRUCTIVE_TOOLS:
        preview = DESTRUCTIVE_TOOLS[name](args)
        result = {"dry_run": True, "safe": True, **preview}
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    # Handle audio analysis locally (not through Ableton socket)
    if name == "analyze_audio_file":
        try:
            import sys
            sys.path.insert(0, REPO_DIR)
            from audio_analyzer import AudioAnalyzer
            result = AudioAnalyzer.analyze(args["file_path"])
        except Exception as e:
            result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    if name == "detect_pitch":
        try:
            import sys
            sys.path.insert(0, REPO_DIR)
            from audio_analyzer import AudioAnalyzer
            result = AudioAnalyzer.detect_pitch(args["file_path"])
        except Exception as e:
            result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    if name == "analyze_folder":
        try:
            import sys
            sys.path.insert(0, REPO_DIR)
            from audio_analyzer import AudioAnalyzer
            result = AudioAnalyzer.analyze_folder(args["folder_path"], mode=args.get("mode", "full"))
            # Apply sample_type filter if specified
            sample_type_filter = args.get("sample_type")
            if sample_type_filter:
                result = [r for r in result if r.get("sample_type") == sample_type_filter]
        except Exception as e:
            result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    if name == "find_compatible_samples":
        try:
            import sys
            sys.path.insert(0, REPO_DIR)
            from audio_analyzer import AudioAnalyzer
            result = AudioAnalyzer.find_compatible_samples(args["folder_path"], args["target_key"], mode=args.get("mode", "full"))
        except Exception as e:
            result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    if name == "create_smart_folder":
        try:
            import sys
            sys.path.insert(0, REPO_DIR)
            from audio_analyzer import AudioAnalyzer
            result = AudioAnalyzer.create_smart_folder(
                args["target_key"],
                categories=args.get("categories"),
                base_path=args.get("base_path"),
            )
        except Exception as e:
            result = {"error": str(e)}
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
    
    # Strip dry_run before forwarding to LiveAgent (it's an MCP-layer parameter)
    args.pop("dry_run", None)

    result = liveagent_send(name, args)
    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


# ── Main ──────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
