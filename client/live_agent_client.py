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

    # ── Transport & Playback ───────────────────────────────────

    def get_transport_state(self):
        return self._send("get_transport_state")

    def start_playing(self):
        return self._send("start_playing")

    def stop_playing(self):
        return self._send("stop_playing")

    def stop_all_clips(self):
        return self._send("stop_all_clips")

    def set_tempo(self, tempo):
        return self._send("set_tempo", {"tempo": tempo})

    def tap_tempo(self):
        return self._send("tap_tempo")

    def set_time_signature(self, numerator=None, denominator=None):
        payload = {}
        if numerator is not None:
            payload["numerator"] = numerator
        if denominator is not None:
            payload["denominator"] = denominator
        return self._send("set_time_signature", payload)

    def set_metronome(self, enabled):
        return self._send("set_metronome", {"enabled": enabled})

    def set_overdub(self, enabled):
        return self._send("set_overdub", {"enabled": enabled})

    def launch_scene(self, scene_index):
        return self._send("launch_scene", {"scene_index": scene_index})

    def launch_clip(self, track_index, slot_index):
        return self._send("launch_clip", {"track_index": track_index, "slot_index": slot_index})

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

    # ── Audio Clip Commands ──────────────────────────────────

    def create_audio_track(self, index=-1):
        return self._send("create_audio_track", {"index": index})

    def import_audio_clip(self, track_index, slot_index, file_path):
        return self._send("import_audio_clip", {
            "track_index": track_index,
            "slot_index": slot_index,
            "file_path": file_path,
        })

    def get_clip_info(self, track_index, slot_index):
        return self._send("get_clip_info", {
            "track_index": track_index,
            "slot_index": slot_index,
        })

    def set_clip_properties(self, track_index, slot_index, **kwargs):
        payload = {"track_index": track_index, "slot_index": slot_index}
        payload.update(kwargs)
        return self._send("set_clip_properties", payload)

    def duplicate_clip(self, track_index, slot_index, dest_track_index=None, dest_slot_index=None):
        payload = {"track_index": track_index, "slot_index": slot_index}
        if dest_track_index is not None:
            payload["dest_track_index"] = dest_track_index
        if dest_slot_index is not None:
            payload["dest_slot_index"] = dest_slot_index
        return self._send("duplicate_clip", payload)

    def delete_clip(self, track_index, slot_index):
        return self._send("delete_clip", {
            "track_index": track_index,
            "slot_index": slot_index,
        })

    def set_clip_warp(self, track_index, slot_index, warping=None, warp_mode=None):
        payload = {"track_index": track_index, "slot_index": slot_index}
        if warping is not None:
            payload["warping"] = warping
        if warp_mode is not None:
            payload["warp_mode"] = warp_mode
        return self._send("set_clip_warp", payload)

    # ── Drum Rack Commands ──────────────────────────────────

    def create_drum_rack(self, track_index=-1, name="Drum Rack"):
        return self._send("create_drum_rack", {
            "track_index": track_index,
            "name": name,
        })

    def load_sample_to_pad(self, track_index, pad_index, file_path, drum_rack_index=0):
        return self._send("load_sample_to_pad", {
            "track_index": track_index,
            "pad_index": pad_index,
            "file_path": file_path,
            "drum_rack_index": drum_rack_index,
        })

    # ── lifecycle ──────────────────────────────────────────────

    def close(self):
        try:
            self._sock.close()
        except Exception:
            pass
