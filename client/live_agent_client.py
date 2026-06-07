"""
LiveAgent Remote Client — Python
=================================
Connects to LiveAgent running inside Ableton Live and sends JSON commands.

Usage:
    from live_agent_client import LiveAgentClient

    client = LiveAgentClient()
    state = client.ping()
    tracks = client.list_tracks()
    client.load_device(track_index=1, device_name="Massive")
    client.close()
"""

import json
import socket


class LiveAgentClient:
    """Thin wrapper around the LiveAgent socket protocol."""

    def __init__(self, host="127.0.0.1", port=8765, timeout=10):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._sock.connect((host, port))

    # ── low-level ──────────────────────────────────────────────

    def _send(self, command, payload=None):
        request = {"command": command}
        if payload:
            request["payload"] = payload
        data = (json.dumps(request, separators=(",", ":")) + "\n").encode()
        self._sock.sendall(data)

        buf = b""
        while True:
            chunk = self._sock.recv(65536)
            if not chunk:
                break
            buf += chunk
            if b"\n" in buf:
                break

        resp = json.loads(buf.decode().strip())
        if not resp.get("ok"):
            raise Exception(resp.get("error", "Unknown error"))
        return resp.get("result")

    # ── commands ───────────────────────────────────────────────

    def ping(self):
        return self._send("ping")

    def get_live_state(self):
        return self._send("get_live_state")

    def list_tracks(self):
        return self._send("list_tracks")

    def create_midi_track(self, index=-1):
        return self._send("create_midi_track", {"index": index})

    def create_session_clip(self, track_index, slot_index, length_beats=16,
                            name="", color=None, replace=True):
        payload = {
            "track_index": track_index,
            "slot_index": slot_index,
            "length_beats": length_beats,
            "replace": replace,
        }
        if name:
            payload["name"] = name
        if color is not None:
            payload["color"] = color
        return self._send("create_session_clip", payload)

    def write_midi_notes(self, track_index, slot_index, notes):
        """
        notes: list of dicts with keys: pitch, start, duration, velocity (optional), muted (optional)
        """
        return self._send("write_midi_notes", {
            "track_index": track_index,
            "slot_index": slot_index,
            "notes": notes,
        })

    def read_clip_notes(self, track_index, slot_index, length_beats=16):
        return self._send("read_clip_notes", {
            "track_index": track_index,
            "slot_index": slot_index,
            "length_beats": length_beats,
        })

    def clear_clip_notes(self, track_index, slot_index):
        return self._send("clear_clip_notes", {
            "track_index": track_index,
            "slot_index": slot_index,
        })

    def list_devices(self, track_index):
        return self._send("list_devices", {"track_index": track_index})

    def set_parameter_value(self, track_index, device_index=None, device_name=None,
                            parameter_index=None, parameter_name=None, value=0.0):
        payload = {"track_index": track_index, "value": value}
        if device_index is not None:
            payload["device_index"] = device_index
        if device_name:
            payload["device_name"] = device_name
        if parameter_index is not None:
            payload["parameter_index"] = parameter_index
        if parameter_name:
            payload["parameter_name"] = parameter_name
        return self._send("set_parameter_value", payload)

    def write_clip_automation(self, track_index, slot_index, points,
                              device_index=None, device_name=None,
                              parameter_index=None, parameter_name=None,
                              step_duration=0.25):
        payload = {
            "track_index": track_index,
            "slot_index": slot_index,
            "points": points,
            "step_duration": step_duration,
        }
        if device_index is not None:
            payload["device_index"] = device_index
        if device_name:
            payload["device_name"] = device_name
        if parameter_index is not None:
            payload["parameter_index"] = parameter_index
        if parameter_name:
            payload["parameter_name"] = parameter_name
        return self._send("write_clip_automation", payload)

    def load_device(self, track_index, device_name, browser_type="plug-in"):
        return self._send("load_device", {
            "track_index": track_index,
            "device_name": device_name,
            "browser_type": browser_type,
        })

    def list_browser_devices(self, browser_type="plug-in", query="", max_results=100):
        return self._send("list_browser_devices", {
            "browser_type": browser_type,
            "query": query,
            "max_results": max_results,
        })

    # ── lifecycle ──────────────────────────────────────────────

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass
