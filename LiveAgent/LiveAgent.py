from __future__ import absolute_import, print_function

import json
import socket
import threading
import time
import traceback

try:
    import queue
except ImportError:
    import Queue as queue

from _Framework.ControlSurface import ControlSurface


HOST = "127.0.0.1"
PORT = 8765


class LiveAgent(ControlSurface):
    """Small JSON socket bridge for chat-driven Ableton commands.

    Socket threads never touch Live's object model. They enqueue requests, then
    the ControlSurface drains them on Live's main thread with schedule_message.
    """

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._running = True
        self._server_socket = None
        self._command_queue = queue.Queue()
        self._server_thread = threading.Thread(target=self._run_server)
        self._server_thread.daemon = True
        self._server_thread.start()
        self.log_message("[LiveAgent] listening on %s:%s" % (HOST, PORT))
        self.schedule_message(1, self._drain_commands)

    def disconnect(self):
        self._running = False
        try:
            if self._server_socket:
                self._server_socket.close()
        except Exception:
            pass
        self.log_message("[LiveAgent] disconnected")
        ControlSurface.disconnect(self)

    def _run_server(self):
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((HOST, PORT))
            server.listen(8)
            server.settimeout(0.5)
            self._server_socket = server
        except Exception:
            self._log_exception("server startup failed")
            return

        while self._running:
            try:
                conn, _addr = self._server_socket.accept()
                thread = threading.Thread(target=self._handle_client, args=(conn,))
                thread.daemon = True
                thread.start()
            except socket.timeout:
                continue
            except Exception:
                if self._running:
                    self._log_exception("accept failed")
                break

    def _handle_client(self, conn):
        conn.settimeout(10)
        buffer = b""
        try:
            while self._running:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        request = json.loads(line.decode("utf-8"))
                    except Exception as err:
                        self._send_response(conn, {"ok": False, "error": "Invalid JSON: %s" % err})
                        continue
                    self._command_queue.put((request, conn))
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _drain_commands(self):
        handled = 0
        while self._running and handled < 50:
            try:
                request, conn = self._command_queue.get(False)
            except queue.Empty:
                break

            response = self._safe_execute(request)
            self._send_response(conn, response)
            handled += 1

        if self._running:
            self.schedule_message(1, self._drain_commands)

    def _safe_execute(self, request):
        request_id = request.get("id")
        try:
            result = self._execute(request)
            return {"id": request_id, "ok": True, "result": result}
        except Exception as err:
            self._log_exception("command failed")
            return {
                "id": request_id,
                "ok": False,
                "error": str(err),
                "traceback": traceback.format_exc(),
            }

    def _send_response(self, conn, response):
        try:
            payload = (json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8")
            conn.sendall(payload)
        except Exception:
            pass

    def _execute(self, request):
        command = request.get("command")
        payload = request.get("payload") or {}

        if command == "ping":
            return {"pong": True, "time": time.time()}
        if command == "get_live_state":
            return self._live_state()
        if command == "list_tracks":
            return {"tracks": self._track_summaries()}
        if command == "create_midi_track":
            return self._create_midi_track(payload)
        if command == "create_session_clip":
            return self._create_session_clip(payload)
        if command == "write_midi_notes":
            return self._write_midi_notes(payload)
        if command == "read_clip_notes":
            return self._read_clip_notes(payload)
        if command == "clear_clip_notes":
            return self._clear_clip_notes(payload)
        if command == "list_devices":
            return self._list_devices(payload)
        if command == "set_parameter_value":
            return self._set_parameter_value(payload)
        if command == "write_clip_automation":
            return self._write_clip_automation(payload)
        if command == "load_device":
            return self._load_device(payload)
        if command == "list_browser_devices":
            return self._list_browser_devices(payload)
        if command == "import_audio_clip":
            return self._import_audio_clip(payload)
        if command == "get_clip_info":
            return self._get_clip_info(payload)
        if command == "set_clip_properties":
            return self._set_clip_properties(payload)
        if command == "duplicate_clip":
            return self._duplicate_clip(payload)
        if command == "delete_clip":
            return self._delete_clip(payload)
        if command == "create_audio_track":
            return self._create_audio_track(payload)
        if command == "set_clip_warp":
            return self._set_clip_warp(payload)

        raise Exception("Unknown command: %s" % command)

    def _live_state(self):
        song = self.song()
        return {
            "application": "Ableton Live",
            "tempo": song.tempo,
            "is_playing": song.is_playing,
            "tracks": self._track_summaries(),
            "scenes": [{"index": i, "name": scene.name} for i, scene in enumerate(song.scenes)],
            "selected_track_index": self._track_index(song.view.selected_track),
        }

    def _track_summaries(self):
        return [self._track_summary(i, track) for i, track in enumerate(self.song().tracks)]

    def _track_summary(self, index, track):
        track_type = "midi" if self._safe_attr(track, "has_midi_input", False) else "audio"
        devices = []
        for device_index, device in enumerate(getattr(track, "devices", [])):
            devices.append(
                {
                    "index": device_index,
                    "name": device.name,
                    "class_name": self._safe_attr(device, "class_name", ""),
                    "parameters": [
                        {
                            "index": parameter_index,
                            "name": parameter.name,
                            "value": self._safe_attr(parameter, "value", None),
                            "min": self._safe_attr(parameter, "min", None),
                            "max": self._safe_attr(parameter, "max", None),
                            "is_enabled": self._safe_attr(parameter, "is_enabled", True),
                        }
                        for parameter_index, parameter in enumerate(getattr(device, "parameters", []))
                    ],
                }
            )

        clip_slots = []
        for slot_index, slot in enumerate(getattr(track, "clip_slots", [])):
            clip = slot.clip if slot.has_clip else None
            clip_slots.append(
                {
                    "index": slot_index,
                    "has_clip": bool(slot.has_clip),
                    "clip": self._clip_summary(clip) if clip else None,
                }
            )

        return {
            "index": index,
            "name": track.name,
            "type": track_type,
            "has_midi_input": self._safe_attr(track, "has_midi_input", False),
            "has_audio_input": self._safe_attr(track, "has_audio_input", False),
            "can_be_armed": self._safe_attr(track, "can_be_armed", False),
            "arm": self._safe_attr(track, "arm", False),
            "mute": self._safe_attr(track, "mute", False),
            "solo": self._safe_attr(track, "solo", False),
            "devices": devices,
            "clip_slots": clip_slots,
        }

    def _clip_summary(self, clip):
        return {
            "name": clip.name,
            "length": self._safe_attr(clip, "length", None),
            "loop_start": self._safe_attr(clip, "loop_start", None),
            "loop_end": self._safe_attr(clip, "loop_end", None),
            "is_midi_clip": self._safe_attr(clip, "is_midi_clip", False),
            "color": self._safe_attr(clip, "color", None),
        }

    def _create_midi_track(self, payload):
        index = int(payload.get("index", -1))
        self.song().create_midi_track(index)
        return {"tracks": self._track_summaries()}

    def _create_session_clip(self, payload):
        track, slot = self._track_and_slot(payload)
        self._require_midi_track(track)

        length = float(payload.get("length_beats", 16))
        replace = bool(payload.get("replace", False))

        if slot.has_clip:
            if not replace:
                raise Exception("Clip slot already contains a clip")
            slot.delete_clip()

        slot.create_clip(length)
        clip = slot.clip
        clip.loop_start = 0
        clip.loop_end = length
        if payload.get("name"):
            clip.name = payload.get("name")
        if payload.get("color") is not None:
            clip.color = int(payload.get("color"))
        return {"clip": self._clip_summary(clip)}

    def _write_midi_notes(self, payload):
        track, slot = self._track_and_slot(payload)
        self._require_midi_track(track)
        if not slot.has_clip:
            length = float(payload.get("length_beats", 16))
            slot.create_clip(length)
        clip = slot.clip
        if not self._safe_attr(clip, "is_midi_clip", False):
            raise Exception("Target clip is not a MIDI clip")

        notes = []
        for note in payload.get("notes", []):
            notes.append(
                (
                    int(note.get("pitch")),
                    float(note.get("start")),
                    float(note.get("duration")),
                    int(note.get("velocity", 96)),
                    bool(note.get("muted", False)),
                )
            )

        clip.select_all_notes()
        clip.replace_selected_notes(tuple(notes))
        clip.deselect_all_notes()
        return {"clip": self._clip_summary(clip), "note_count": len(notes)}

    def _read_clip_notes(self, payload):
        _track, slot = self._track_and_slot(payload)
        if not slot.has_clip:
            return {"notes": []}
        clip = slot.clip
        end = float(payload.get("length_beats", self._safe_attr(clip, "length", 16)))
        raw_notes = clip.get_notes(0, 0, end, 128)
        notes = [
            {
                "pitch": int(note[0]),
                "start": float(note[1]),
                "duration": float(note[2]),
                "velocity": int(note[3]),
                "muted": bool(note[4]),
            }
            for note in raw_notes
        ]
        return {"notes": notes}

    def _clear_clip_notes(self, payload):
        _track, slot = self._track_and_slot(payload)
        if not slot.has_clip:
            return {"note_count": 0}
        clip = slot.clip
        clip.select_all_notes()
        clip.replace_selected_notes(tuple())
        clip.deselect_all_notes()
        return {"clip": self._clip_summary(clip), "note_count": 0}

    def _list_devices(self, payload):
        track = self._track_by_index(payload.get("track_index", 0))
        return {"track": self._track_summary(self._track_index(track), track)}

    def _set_parameter_value(self, payload):
        device, parameter = self._device_and_parameter(payload)
        value = float(payload.get("value"))
        parameter.value = value
        return {
            "device": device.name,
            "parameter": parameter.name,
            "value": parameter.value,
        }

    def _write_clip_automation(self, payload):
        _track, slot = self._track_and_slot(payload)
        if not slot.has_clip:
            raise Exception("Target slot has no clip")
        clip = slot.clip
        device, parameter = self._device_and_parameter(payload)
        points = payload.get("points", [])
        step_duration = float(payload.get("step_duration", 0.25))

        if hasattr(clip, "clear_envelope"):
            try:
                clip.clear_envelope(parameter)
            except Exception:
                pass

        envelope = None
        if hasattr(clip, "create_automation_envelope"):
            try:
                envelope = clip.create_automation_envelope(parameter)
            except Exception:
                envelope = None

        if envelope is None and hasattr(clip, "automation_envelope"):
            envelope = clip.automation_envelope(parameter)

        if envelope is None or not hasattr(envelope, "insert_step"):
            raise Exception(
                "Clip automation envelope writing is not available in this Live Python API. "
                "Parameter listing and set_parameter_value still work."
            )

        inserted = 0
        for point in points:
            envelope.insert_step(float(point.get("time")), step_duration, float(point.get("value")))
            inserted += 1

        return {
            "clip": self._clip_summary(clip),
            "device": device.name,
            "parameter": parameter.name,
            "point_count": inserted,
        }

    def _load_device(self, payload):
        """Load a device onto a track via Ableton's browser tree.

        Uses the Live Browser API to navigate Plugins/Instruments and load
        the specified device onto the target track.
        """
        import Live
        track = self._track_by_index(payload.get("track_index", 0))
        device_name = payload.get("device_name", "")
        browser_type = payload.get("browser_type", "plug-in")  # plug-in, instrument, audio_effect, midi_effect

        if not device_name:
            raise Exception("device_name is required")

        # Select the target track so the browser loads onto it
        song = self.song()
        song.view.selected_track = track

        # Navigate Ableton's browser to find and load the device
        browser = song.browser
        
        # Try to find the right browser category
        target_category = None
        for category in browser.categories:
            cat_name = category.name.lower()
            if browser_type.lower() == "plug-in" and "plug-in" in cat_name:
                target_category = category
                break
            elif browser_type.lower() == "instrument" and "instrument" in cat_name:
                target_category = category
                break
            elif browser_type.lower() == "audio effect" and "audio effect" in cat_name:
                target_category = category
                break
            elif browser_type.lower() == "midi effect" and "midi effect" in cat_name:
                target_category = category
                break

        if target_category is None:
            # Fallback: try Plug-ins category
            for category in browser.categories:
                if "plug" in category.name.lower():
                    target_category = category
                    break

        if target_category is None:
            raise Exception(
                "Could not find browser category '%s'. Available: %s"
                % (browser_type, [c.name for c in browser.categories])
            )

        # Search for the device in the category tree
        device_item = self._find_browser_item(target_category, device_name)

        if device_item is None:
            raise Exception(
                "Could not find device '%s' in category '%s'"
                % (device_name, target_category.name)
            )

        # Load the device onto the selected track
        device_item.load()
        
        # Small wait then check if device appeared
        time.sleep(0.3)
        
        # Return updated track info
        idx = self._track_index(track)
        return {
            "track": self._track_summary(idx, track),
            "loaded_device": device_name,
        }

    def _list_browser_devices(self, payload):
        """List available devices from Ableton's browser.

        Optionally filter by browser_type and search query.
        """
        browser_type = payload.get("browser_type", "plug-in")
        query = payload.get("query", "").lower()
        max_results = int(payload.get("max_results", 100))

        song = self.song()
        browser = song.browser

        # Find the matching browser category
        target_category = None
        for category in browser.categories:
            cat_name = category.name.lower()
            if browser_type.lower() == "plug-in" and "plug-in" in cat_name:
                target_category = category
                break
            elif browser_type.lower() == "instrument" and "instrument" in cat_name:
                target_category = category
                break
            elif browser_type.lower() == "audio effect" and "audio effect" in cat_name:
                target_category = category
                break
            elif browser_type.lower() == "midi effect" and "midi effect" in cat_name:
                target_category = category
                break

        if target_category is None:
            for category in browser.categories:
                if "plug" in category.name.lower():
                    target_category = category
                    break

        if target_category is None:
            raise Exception(
                "Could not find browser category '%s'. Available: %s"
                % (browser_type, [c.name for c in browser.categories])
            )

        # Collect all loadable devices from the browser tree
        devices = []
        self._collect_browser_items(target_category, devices, query, max_results, path=[])

        return {
            "category": target_category.name,
            "query": payload.get("query", ""),
            "count": len(devices),
            "devices": devices,
        }

    def _collect_browser_items(self, node, results, query, max_results, path):
        """Recursively collect loadable items from browser tree."""
        if len(results) >= max_results:
            return

        node_name = self._safe_attr(node, "name", "")

        # Build current path
        current_path = path + [node_name] if node_name else path

        # Check if this node is loadable
        is_loadable = self._safe_attr(node, "is_loadable", False)
        if is_loadable and node_name:
            if not query or query in node_name.lower():
                results.append({
                    "name": node_name,
                    "path": " > ".join(current_path),
                })
                if len(results) >= max_results:
                    return

        # Recurse into children
        children = self._safe_attr(node, "children", None)
        if children:
            for child in children:
                self._collect_browser_items(child, results, query, max_results, current_path)
                if len(results) >= max_results:
                    return

        # Check items list
        items = self._safe_attr(node, "items", None)
        if items:
            for item in items:
                if len(results) >= max_results:
                    return
                item_name = self._safe_attr(item, "name", "")
                item_loadable = self._safe_attr(item, "is_loadable", False)
                if item_loadable and item_name:
                    if not query or query in item_name.lower():
                        results.append({
                            "name": item_name,
                            "path": " > ".join(current_path + [item_name]),
                        })

    def _find_browser_item(self, category, target_name):
        """Recursively search browser tree for a device by name."""
        target_lower = target_name.lower()
        
        # Check items directly in this category
        if hasattr(category, "children"):
            for child in category.children:
                result = self._search_browser_node(child, target_lower)
                if result is not None:
                    return result
        
        # Some categories have items directly
        if hasattr(category, "items"):
            for item in category.items:
                if hasattr(item, "name") and item.name and target_lower in item.name.lower():
                    if self._safe_attr(item, "is_loadable", True):
                        return item

        return None

    def _search_browser_node(self, node, target_lower):
        """Recursively search a browser node."""
        node_name = self._safe_attr(node, "name", "")
        
        if node_name and target_lower in node_name.lower():
            if self._safe_attr(node, "is_loadable", True):
                return node

        # Check children
        children = self._safe_attr(node, "children", None)
        if children:
            for child in children:
                result = self._search_browser_node(child, target_lower)
                if result is not None:
                    return result

        # Check items
        items = self._safe_attr(node, "items", None)
        if items:
            for item in items:
                item_name = self._safe_attr(item, "name", "")
                if item_name and target_lower in item_name.lower():
                    if self._safe_attr(item, "is_loadable", True):
                        return item

        return None

    def _track_and_slot(self, payload):
        track = self._track_by_index(payload.get("track_index", 0))
        slot_index = int(payload.get("slot_index", 0))
        self._ensure_scene(slot_index)
        return track, track.clip_slots[slot_index]

    def _track_by_index(self, index):
        tracks = list(self.song().tracks)
        index = int(index)
        if index < 0 or index >= len(tracks):
            raise Exception("Track index out of range: %s" % index)
        return tracks[index]

    def _ensure_scene(self, slot_index):
        song = self.song()
        while slot_index >= len(song.scenes):
            song.create_scene(-1)

    def _require_midi_track(self, track):
        if not self._safe_attr(track, "has_midi_input", False):
            raise Exception('Track "%s" is not a MIDI track' % track.name)

    def _device_and_parameter(self, payload):
        track = self._track_by_index(payload.get("track_index", 0))
        device = self._find_by_index_or_name(
            track.devices,
            payload.get("device_index"),
            payload.get("device_name"),
            "device",
        )
        parameter = self._find_by_index_or_name(
            device.parameters,
            payload.get("parameter_index"),
            payload.get("parameter_name"),
            "parameter",
        )
        return device, parameter

    def _find_by_index_or_name(self, items, index, name, label):
        items = list(items)
        if index is not None:
            index = int(index)
            if index < 0 or index >= len(items):
                raise Exception("%s index out of range: %s" % (label, index))
            return items[index]

        if name:
            target = str(name).lower()
            for item in items:
                if item.name.lower() == target:
                    return item
            for item in items:
                if target in item.name.lower():
                    return item

        raise Exception("Could not find %s: %s" % (label, name if name else index))

    def _track_index(self, track):
        for index, candidate in enumerate(self.song().tracks):
            if candidate == track:
                return index
        return None

    def _safe_attr(self, obj, attr, default):
        try:
            return getattr(obj, attr)
        except Exception:
            return default

    def _log_exception(self, label):
        try:
            self.log_message("[LiveAgent] %s: %s" % (label, traceback.format_exc()))
        except Exception:
            pass

    # ── Audio Clip Commands ──────────────────────────────────

    def _create_audio_track(self, payload):
        """Create a new audio track."""
        index = int(payload.get("index", -1))
        song = self.song()
        song.create_audio_track(index)
        actual_index = index if index >= 0 else len(song.tracks) - 1
        track = song.tracks[actual_index]
        return {"track_index": actual_index, "name": track.name}

    def _import_audio_clip(self, payload):
        """Import an audio file into a track slot."""
        import os
        file_path = payload.get("file_path", "")
        if not file_path or not os.path.isfile(file_path):
            raise Exception("Audio file not found: %s" % file_path)

        track_index = int(payload.get("track_index", 0))
        slot_index = int(payload.get("slot_index", 0))
        track = self._track_by_index(track_index)
        self._ensure_scene(slot_index)
        slot = track.clip_slots[slot_index]

        # Use Ableton's browser to import - set view focus then drag
        # The reliable method: create clip via Live's file import
        song = self.song()
        song.view.selected_track = track
        song.view.selected_scene = song.scenes[slot_index]

        # Import using Live's internal command
        # Live 11: we can use the browser's file system import
        # Most reliable: use set_file_path if available, or browser drag
        import Live
        Live.Application.get_application().open_document(file_path)

        return {
            "track_index": track_index,
            "slot_index": slot_index,
            "file": os.path.basename(file_path),
            "status": "imported",
        }

    def _get_clip_info(self, payload):
        """Get detailed info about a clip (audio or MIDI)."""
        track, slot = self._track_and_slot(payload)
        if not slot.has_clip:
            return {"has_clip": False}

        clip = slot.clip
        info = {
            "has_clip": True,
            "name": clip.name,
            "color": clip.color,
            "is_audio_clip": self._safe_attr(clip, "is_audio_clip", False),
            "is_midi_clip": self._safe_attr(clip, "is_midi_clip", False),
            "looping": clip.looping,
            "loop_start": clip.loop_start,
            "loop_end": clip.loop_end,
            "start_marker": clip.start_marker,
            "end_marker": clip.end_marker,
            "pitch": self._safe_attr(clip, "pitch_coarse", 0),
            "gain": self._safe_attr(clip, "gain", 1.0),
        }

        # Audio-specific properties
        if self._safe_attr(clip, "is_audio_clip", False):
            info["warping"] = clip.warping
            info["warp_mode"] = str(self._safe_attr(clip, "warp_mode", ""))
            info["file_path"] = self._safe_attr(clip, "file_path", "")
            info["sample_length"] = self._safe_attr(clip, "sample_length", 0.0)

        return info

    def _set_clip_properties(self, payload):
        """Set clip properties: name, color, loop, start/end, pitch, gain."""
        track, slot = self._track_and_slot(payload)
        if not slot.has_clip:
            raise Exception("No clip at track %s slot %s" % (payload.get("track_index"), payload.get("slot_index")))
        clip = slot.clip

        if "name" in payload:
            clip.name = payload["name"]
        if "color" in payload:
            clip.color = int(payload["color"])
        if "looping" in payload:
            clip.looping = bool(payload["looping"])
        if "loop_start" in payload:
            clip.loop_start = float(payload["loop_start"])
        if "loop_end" in payload:
            clip.loop_end = float(payload["loop_end"])
        if "start_marker" in payload:
            clip.start_marker = float(payload["start_marker"])
        if "end_marker" in payload:
            clip.end_marker = float(payload["end_marker"])

        # Audio-specific
        if self._safe_attr(clip, "is_audio_clip", False):
            if "pitch_coarse" in payload:
                clip.pitch_coarse = int(payload["pitch_coarse"])
            if "pitch_fine" in payload:
                clip.pitch_fine = float(payload["pitch_fine"])
            if "gain" in payload:
                clip.gain = float(payload["gain"])

        return {"updated": True, "clip": self._get_clip_info(payload)}

    def _duplicate_clip(self, payload):
        """Duplicate a clip to another slot (same or different track)."""
        src_track = self._track_by_index(int(payload.get("track_index", 0)))
        src_slot_idx = int(payload.get("slot_index", 0))
        self._ensure_scene(src_slot_idx)
        src_slot = src_track.clip_slots[src_slot_idx]
        if not src_slot.has_clip:
            raise Exception("No clip at source slot %s" % src_slot_idx)

        dst_track_idx = int(payload.get("dest_track_index", payload.get("track_index", 0)))
        dst_slot_idx = int(payload.get("dest_slot_index", src_slot_idx + 1))
        dst_track = self._track_by_index(dst_track_idx)
        self._ensure_scene(dst_slot_idx)
        dst_slot = dst_track.clip_slots[dst_slot_idx]

        src_slot.clip.duplicate_clip_to(dst_slot)

        return {
            "source": {"track": int(payload.get("track_index", 0)), "slot": src_slot_idx},
            "destination": {"track": dst_track_idx, "slot": dst_slot_idx},
        }

    def _delete_clip(self, payload):
        """Delete a clip from a slot."""
        track, slot = self._track_and_slot(payload)
        if not slot.has_clip:
            raise Exception("No clip at track %s slot %s" % (payload.get("track_index"), payload.get("slot_index")))
        clip_name = slot.clip.name
        slot.delete_clip()
        return {"deleted": True, "clip_name": clip_name}

    def _set_clip_warp(self, payload):
        """Set warp properties on an audio clip."""
        track, slot = self._track_and_slot(payload)
        if not slot.has_clip:
            raise Exception("No clip at track %s slot %s" % (payload.get("track_index"), payload.get("slot_index")))
        clip = slot.clip

        if not self._safe_attr(clip, "is_audio_clip", False):
            raise Exception("Clip is not an audio clip")

        if "warping" in payload:
            clip.warping = bool(payload["warping"])
        if "warp_mode" in payload:
            # Warp modes: 0=beats, 1=tones, 2=texture, 3=re-pitch, 4=complex, 5=complex pro
            clip.warp_mode = int(payload["warp_mode"])

        return {
            "warping": clip.warping,
            "warp_mode": str(clip.warp_mode),
        }
