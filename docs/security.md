# Security Model

LiveAgent Remote is designed to control a digital audio workstation (Ableton Live)
from external scripts and AI agents. Because the control surface executes
arbitrary commands against a live DAW session — and potentially the host
operating system — the security model is layered to prevent accidental damage
and limit the blast radius of any misuse.

## Threat Model Summary

| Surface                 | Exposure             | Mitigation                                        |
|-------------------------|----------------------|---------------------------------------------------|
| TCP listener            | Local network        | Binds to `127.0.0.1` only — not reachable remotely |
| Destructive commands    | State mutation       | `dry_run` preview on all 9 destructive operations |
| Arbitrary code execution| Full host access     | `eval` / `exec` disabled by default               |
| Multi-step operations   | Cascading changes    | `batch()` groups into a single undo step          |
| Unknown / malformed input| Injection           | Every command is validated before execution       |

---

## 1. Localhost-Only TCP Listener

The LiveAgent control surface opens a single TCP socket for command ingress:

```python
# LiveAgent/LiveAgent.py
HOST = "127.0.0.1"
PORT = 8765
```

- The socket is bound to **`127.0.0.1`** (loopback), not `0.0.0.0`.
- It is **not** reachable from other machines on the LAN, VPN, or the public internet.
- The listener is only active while Ableton Live is running with the LiveAgent
  control surface selected.
- The socket has a 10-second per-connection timeout to prevent resource
  exhaustion from idle clients.

If you need remote access (e.g., from a headless build server), **do not** change
the bind address. Instead, tunnel through SSH or run an MCP server on the same
machine and expose that through your own authenticated transport.

---

## 2. `eval` / `exec` — Disabled by Default

LiveAgent exposes two commands — `eval` and `exec` — that evaluate arbitrary
Python inside Ableton's embedded interpreter. These have access to the full
**Live Object Model** (`song`, `app`) and the `os` / `json` modules, making them
extremely powerful but also dangerous.

### Default state: OFF

```python
# LiveAgent/LiveAgent.py
self._unsafe_enabled = os.environ.get("LIVEAGENT_ENABLE_UNSAFE", "0") == "1"
```

Unless the environment variable **`LIVEAGENT_ENABLE_UNSAFE=1`** is set *before*
Ableton launches, both `eval` and `exec` return an error:

```json
{
  "error": "eval is disabled. Set LIVEAGENT_ENABLE_UNSAFE=1 environment variable to enable.",
  "security": "This command allows arbitrary code execution and is disabled by default."
}
```

### How to enable

The environment variable must be set in the process that *launches Ableton*,
because the control surface script inherits Ableton's environment:

**macOS (Terminal):**
```bash
LIVEAGENT_ENABLE_UNSAFE=1 open -a "Ableton Live 12 Standard"
```

**macOS (persistent, via launchd or shell profile):**
```bash
export LIVEAGENT_ENABLE_UNSAFE=1
```

### Restricted namespaces (even when enabled)

When enabled, the namespaces are still restricted:

- **`eval`** — Runs with `__builtins__: {}` and a whitelist of safe builtins
  (`len`, `str`, `int`, `float`, `list`, `dict`, `range`, `getattr`, `type`,
  `repr`, etc.). No access to `self`, `import`, `open`, or `__builtins__`.
- **`exec`** — Has access to `Live`, `song`, `app`, `os`, `json`. Intended for
  assignments and mutations (e.g., setting `song.view.selected_track`). Does
  **not** have access to `self` or the LiveAgent module internals.

> **⚠️ Warning:** Even with restricted builtins, `exec` with `os` access can
> modify files on disk. Only enable `LIVEAGENT_ENABLE_UNSAFE=1` on trusted
> machines and never expose the TCP port to untrusted networks.

---

## 3. Destructive Operations — `dry_run` Preview

Nine commands can mutate the Live set in ways that are not trivially
reversible. Each of these accepts a **`dry_run`** parameter that previews the
action without executing it:

| #  | Command                | What it does                                          |
|----|------------------------|-------------------------------------------------------|
| 1  | `delete_clip`          | Removes a clip from a track slot                      |
| 2  | `clear_clip_notes`     | Erases all MIDI notes from a clip                     |
| 3  | `set_parameter_value`  | Changes a device parameter (knob/slider/fader)        |
| 4  | `load_device`          | Loads a VST/AU plugin or built-in device onto a track |
| 5  | `load_sample_to_pad`   | Replaces a sample in a Drum Rack pad                  |
| 6  | `write_midi_notes`     | Overwrites the note content of a MIDI clip            |
| 7  | `write_clip_automation`| Writes automation envelope points to a clip           |
| 8  | `set_clip_warp`        | Changes warp on/off and warp mode on an audio clip    |
| 9  | `set_clip_properties`  | Modifies clip name, color, loop, pitch, or gain       |

### How dry_run works

The `dry_run` flag is intercepted **at the MCP layer** (`mcp_server.py`) before
the command is ever sent over TCP to Ableton:

```python
# mcp_server.py — call_tool handler
if args.get("dry_run") and name in DESTRUCTIVE_TOOLS:
    preview = DESTRUCTIVE_TOOLS[name](args)
    result = {"dry_run": True, "safe": True, **preview}
    return [TextContent(type="text", text=json.dumps(result, ...))]
```

The `dry_run` parameter is then **stripped** before forwarding any non-dry-run
command to LiveAgent, so the control surface never sees it:

```python
args.pop("dry_run", None)
result = liveagent_send(name, args)
```

### Example: previewing a destructive write

```json
{
  "command": "write_midi_notes",
  "track_index": 0,
  "slot_index": 0,
  "notes": [{"pitch": 60, "start": 0, "duration": 1, "velocity": 96}],
  "dry_run": true
}
```

Response:
```json
{
  "dry_run": true,
  "safe": true,
  "would_do": "Write 1 MIDI notes",
  "target": "Track 0 / Slot 0"
}
```

AI agents should use `dry_run: true` on the first call when uncertain about
track indices, slot indices, or parameter ranges.

---

## 4. `batch()` — Single Undo Step

The `batch` command executes a list of commands as an **atomic undo group**.
This means a complex multi-step operation (e.g., "create a track, create a
clip, write notes, load a device") can be undone with a single `Ctrl+Z`.

### Implementation

```python
# LiveAgent/LiveAgent.py — _batch()
self.song().begin_undo_step()
try:
    for i, cmd_spec in enumerate(commands):
        result = self._execute({"command": cmd, "payload": cmd_payload})
        results.append({"index": i, "command": cmd, "ok": True, "result": result})
        ...
except ...:
    # Stop on first error
    break
finally:
    self.song().end_undo_step()
```

### Key behaviors

- **All-or-nothing undo:** Every command in the batch is wrapped in a single
  `begin_undo_step()` / `end_undo_step()` pair. One `Ctrl+Z` reverts the entire
  batch.
- **Stops on first error:** If command N fails, commands N+1…end are skipped.
  However, the partial results are still grouped — the user can `Ctrl+Z` to
  undo everything done up to the failure point.
- **`finally` guarantees close:** `end_undo_step()` is always called, even if
  an exception escapes the loop. A stuck open undo step would corrupt Live's
  undo history.
- **Supports `dry_run`:** The batch command itself is in the
  `DESTRUCTIVE_TOOLS` map, so `dry_run: true` previews the full command list
  without executing any of them.

### Example

```json
{
  "command": "batch",
  "payload": {
    "commands": [
      {"command": "create_midi_track", "payload": {"index": -1}},
      {"command": "create_session_clip", "payload": {"track_index": 0, "slot_index": 0}},
      {"command": "write_midi_notes", "payload": {"track_index": 0, "slot_index": 0, "notes": [{"pitch": 60, "start": 0, "duration": 1}]}}
    ]
  }
}
```

---

## 5. Command Validation

Every command is validated before it touches the Live Object Model.

### Command whitelist

The `_execute()` method dispatches on a fixed set of known command names:

```python
def _execute(self, request):
    command = request.get("command")
    if command == "ping":
        return ...
    if command == "create_midi_track":
        return self._create_midi_track(payload)
    ...
    raise Exception("Unknown command: %s" % command)
```

Unknown commands raise immediately — there is no generic dispatch or `getattr`
fallback.

### Type coercion and bounds checking

Each handler coerces arguments to the expected type and validates bounds:

- `int(payload.get("index", -1))` — track indices are always integers
- `float(payload.get("value"))` — parameter values are always floats
- `bool(payload.get("replace", False))` — flags are always booleans
- MIDI pitches are cast to `int`, velocities to `int`, start/duration to `float`
- Track/slot existence is checked before access (`_track_and_slot`)
- MIDI-only operations verify the track has MIDI input (`_require_midi_track`)

### Thread-safety model

Socket I/O runs on background threads, but **no Live Object Model access
happens on those threads**. Requests are enqueued and drained on Live's main
thread via `schedule_message`:

```python
# Background thread: enqueue only
self._command_queue.put((request, conn))

# Main thread: execute and respond
def _drain_commands(self):
    request, conn = self._command_queue.get(False)
    response = self._safe_execute(request)
    self._send_response(conn, response)
```

This prevents race conditions and ensures all LOM mutations are serialized.

### Error containment

`_safe_execute()` wraps every command in `try/except`:

```python
def _safe_execute(self, request):
    try:
        result = self._execute(request)
        return {"id": request_id, "ok": True, "result": result}
    except Exception as err:
        return {"ok": False, "error": str(err), "traceback": traceback.format_exc()}
```

- Errors are returned to the caller as JSON, never crash the control surface.
- The traceback is included for debugging (visible to the MCP client / TCP
  caller, not to the end user in Ableton's UI).
- The drain loop continues processing subsequent commands after an error.

---

## Quick Reference: Security Checklist

- [ ] Only run LiveAgent on a **trusted local machine**
- [ ] Do **not** change `HOST` from `127.0.0.1`
- [ ] Leave `LIVEAGENT_ENABLE_UNSAFE` **unset** unless you need `eval`/`exec`
- [ ] Use `dry_run: true` on destructive commands when indices are uncertain
- [ ] Use `batch()` for multi-step mutations so they share a single undo step
- [ ] If exposing via MCP, ensure the MCP server runs on the same machine as
      Ableton (the TCP bridge is localhost-only)
