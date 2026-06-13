# Troubleshooting

Common issues and their solutions. If your problem isn't listed here, check the
[SKILL.md](../SKILL.md) pitfalls section or open an issue on
[GitHub](https://github.com/happytown-s/live-agent-remote/issues).

---

## Table of Contents

1. [Ableton Live Not Detected](#1-ableton-live-not-detected)
2. [LiveAgent Not in MIDI Remote Scripts](#2-liveagent-not-in-midi-remote-scripts)
3. [Connection Refused on Port 8765](#3-connection-refused-on-port-8765)
4. [Preferences.cfg Must NOT Be Deleted](#4-preferencescfg-must-not-be-deleted)
5. [Drum Rack Empty Pad Has No Chain](#5-drum-rack-empty-pad-has-no-chain)
6. [VST Parameter Configure Mode](#6-vst-parameter-configure-mode)
7. [macOS Permissions for Ableton](#7-macos-permissions-for-ableton)
8. [MCP Server Not Starting](#8-mcp-server-not-starting)
9. [eval / exec Return "Disabled"](#9-eval--exec-return-disabled)

---

## 1. Ableton Live Not Detected

### Symptom

`ping` or `get_live_state` returns an error like:

```
Cannot connect to Ableton Live. Is LiveAgent control surface active?
```

Or the MCP server fails to list tools.

### Cause

The LiveAgent control surface is not active in Ableton, so no TCP listener is
running on port 8765.

### Solution

1. **Open Ableton Live.**
2. Go to **Preferences → Link/Tempo/MIDI** (the "Link, Tempo & MIDI" tab).
3. Scroll to the **Control Surfaces** section.
4. Check that **LiveAgent** appears in the list with an assigned row.
5. If not present, click the **dropdown** under "Control Surface" and select
   **LiveAgent**.

   ![Control Surface dropdown](https://ableton.com/views/common/images/link-tempo-midi.png)

6. **Input** and **Output** can be left as "None" — LiveAgent does not require
   a MIDI device, it only needs to be selected as a control surface.

### Verification

From a terminal:

```bash
echo '{"command":"ping"}' | nc 127.0.0.1 8765
```

Expected response:

```json
{"id": null, "ok": true, "result": {"pong": true, "time": 1718000000.0}}
```

If you get `Connection refused`, see
[Section 3](#3-connection-refused-on-port-8765).

---

## 2. LiveAgent Not in MIDI Remote Scripts

### Symptom

**LiveAgent** does not appear in the Control Surface dropdown at all.

### Cause

The `LiveAgent` folder has not been copied into Ableton's MIDI Remote Scripts
directory, or Ableton hasn't been restarted since the copy.

### Solution

#### Find your Ableton version's Remote Scripts directory

**macOS:**
```
/Applications/Ableton Live [version]/Contents/App-Resources/MIDI Remote Scripts/
```

**Windows:**
```
C:\ProgramData\Ableton\Live [version]\Resources\MIDI Remote Scripts\
```

#### Copy the LiveAgent folder

The entire `LiveAgent/` directory (containing `__init__.py` and
`LiveAgent.py`) must be placed inside the `MIDI Remote Scripts/` folder:

```
MIDI Remote Scripts/
├── LiveAgent/
│   ├── __init__.py
│   └── LiveAgent.py
├── Push2/
├── ...
```

```bash
# macOS example
cp -r /path/to/live-agent-remote/LiveAgent \
  "/Applications/Ableton Live 12 Standard/Contents/App-Resources/MIDI Remote Scripts/"
```

#### Restart Ableton

Ableton scans for control surface scripts **only at launch**. You must fully
quit and relaunch:

```bash
# macOS — fully quit, then relaunch
osascript -e 'quit app "Ableton Live 12 Standard"'
sleep 2
open -a "Ableton Live 12 Standard"
```

After relaunch, LiveAgent should appear in the Control Surface dropdown.

### Common mistakes

- **Copying `LiveAgent.py` as a single file** — it must be the whole
  `LiveAgent/` *folder* (Ableton treats each subdirectory as a control surface
  module).
- **Wrong Ableton version path** — if you have multiple versions installed
  (e.g., Live 11 and Live 12), make sure you copy to the correct one.
- **Permissions** — on macOS, the `MIDI Remote Scripts` folder is inside the
  app bundle. You may need to authenticate with an admin password when copying.

---

## 3. Connection Refused on Port 8765

### Symptom

```bash
$ echo '{"command":"ping"}' | nc 127.0.0.1 8765
nc: connectx to 127.0.0.1 port 8765 (tcp) failed: Connection refused
```

### Checklist

| Check | How to verify |
|-------|---------------|
| **Is Ableton running?** | Check Dock / Activity Monitor for "Ableton Live" |
| **Is LiveAgent selected as Control Surface?** | Preferences → Link/Tempo/MIDI → Control Surfaces |
| **Did you wait for full boot?** | Wait 15–30 seconds after launch before connecting |
| **Is port 8765 already in use?** | Run `lsof -i :8765` in terminal |
| **Is there a stuck "Save changes?" dialog?** | Check Ableton's window for modal popups |

### Detailed causes

#### Ableton not running

The TCP listener only exists while Ableton is running with LiveAgent active.
Quit Ableton → the port closes. Relaunch Ableton → the port reopens.

#### Stuck save dialog

If Ableton was force-quit or crashed, it may present a **"Save changes?"**
dialog on next launch. This modal dialog blocks LiveAgent initialization.
**Dismiss the dialog** (Save, Don't Save, or Cancel) and LiveAgent will start
listening.

#### Port conflict

If another process is using port 8765, LiveAgent's `bind()` will fail silently
(errors are logged but the control surface doesn't crash). Check:

```bash
lsof -i :8765
```

If a stale process holds the port, kill it and restart Ableton.

#### Boot delay

Ableton's control surfaces initialize asynchronously after the UI loads. Even
if the Ableton window is visible, LiveAgent may need an additional 10–20
seconds to bind the socket. Wait and retry.

---

## 4. Preferences.cfg Must NOT Be Deleted

### ⚠️ Critical Warning

**Never delete Ableton's `Preferences.cfg` file** as a troubleshooting step.

### Why this matters

Ableton stores control surface assignments (including LiveAgent) and many other
preferences in `Preferences.cfg`. Deleting it will:

- **Remove the LiveAgent control surface assignment** — you'll have to
  re-select it from the dropdown every time.
- **Reset all MIDI mappings** — any custom MIDI controller mappings are lost.
- **Reset audio interface settings** — input/output device, sample rate, buffer
  size all revert to defaults.
- **Reset the file browser** — custom Places and favorites are cleared.

### Location

**macOS:**
```
~/Library/Preferences/Ableton/[Live x.x.x]/Preferences.cfg
```

**Windows:**
```
%APPDATA%\Ableton\[Live x.x.x]\Preferences\Preferences.cfg
```

### If you already deleted it

1. Re-select **LiveAgent** in Preferences → Link/Tempo/MIDI → Control Surface.
2. Reconfigure your audio interface and sample rate.
3. Re-add any custom Places in the browser.
4. Recreate MIDI mappings if you had custom controller assignments.

### Correct troubleshooting alternatives

Instead of deleting `Preferences.cfg`, try these in order:

1. **Deselect and reselect LiveAgent** in the Control Surface dropdown.
2. **Restart Ableton** (full quit, not just close window).
3. **Check the LiveAgent log** — Ableton writes control surface log messages
   to `Log.txt` in the same preferences folder.
4. **Re-copy the LiveAgent folder** to MIDI Remote Scripts (in case the script
   file was corrupted).

---

## 5. Drum Rack Empty Pad Has No Chain

### Symptom

`load_sample_to_pad` fails with an error like:

```
IndexError: list index out of range
```

Or:

```
AttributeError: 'NoneType' object has no attribute 'devices'
```

### Cause

An **empty Drum Rack** (created with `create_drum_rack` and `empty=true`, or a
factory empty rack) has pads with **no chains**. The pad's `chains` Vector is
empty, and it is **read-only** — you cannot `append()` a chain to it.

```python
pad = drum_rack.drum_pads[36]
pad.chains  # → [] (empty, and read-only)
pad.chains.append(some_chain)  # → fails
```

### Solution: Load a kit template first

Always create a Drum Rack from a **preset kit** (`.adg` file) rather than an
empty rack. The default `create_drum_rack` tool loads `808 Core Kit.adg`,
which provides pre-existing chains on pads 36–51:

```python
# Correct: creates a Drum Rack WITH chains on pads 36-51
mcp_liveagent_create_drum_rack(
    track_index=-1,
    name="My Kit",
    kit_name="808 Core Kit.adg",  # default — provides chains
    empty=False                   # default — MUST be False
)
```

Then replace individual pad samples:

```python
mcp_liveagent_load_sample_to_pad(
    track_index=0,
    pad_index=36,       # C1 — Kick
    file_path="/path/to/kick.wav"
)
```

### If you must use an empty rack

You can manually create a chain on an empty pad using `eval` / `exec` (requires
`LIVEAGENT_ENABLE_UNSAFE=1`):

```python
# This is complex and fragile — prefer the kit template approach
mcp_liveagent_exec(stmt='''
drum_rack = song.view.selected_track.devices[0]
pad = drum_rack.drum_pads[36]
# ... chain creation logic
''')
```

In practice, **always start from a kit template.** The kit provides chains,
routing, and device slots. You then hotswap the Simpler sample within each pad.

### Verify pad structure before loading

```python
mcp_liveagent_inspect_drum_rack(track_index=0, pad_range=[36, 51])
```

This returns the chain count and device names for each pad. If a pad shows
`chains: []`, it has no chain and cannot receive a sample directly.

---

## 6. VST Parameter Configure Mode

### Symptom

You can see a VST plugin's parameters via `list_devices`, but only a few (or
just one) are exposed — the rest show as generic "Unassigned" or are missing
entirely.

### Cause

Ableton only exposes VST parameters that have been **configured** (mapped to
the rack/track). When you click "Configure" in a VST's window and then turn a
knob, Ableton registers **only the last-touched parameter**. Each configure
session adds one parameter.

This is an Ableton limitation, not a LiveAgent bug.

### Solution

#### Manual configuration (most reliable)

1. Double-click the VST to open its GUI.
2. Click the **"Configure"** button (gear icon / "Config" in the plugin window
   header).
3. **Turn the knob / move the slider** for each parameter you want to control.
4. Each touched parameter is added to the configured parameters list.
5. Close the configure mode.
6. The parameters are now visible to `list_devices` and controllable via
   `set_parameter_value`.

#### Reading configured parameters

```python
mcp_liveagent_list_devices(track_index=0)
```

Only the parameters you configured will appear with meaningful names. Unmapped
parameters may show as "Macro 1", "Macro 2", etc.

#### Limitations

- **VST GUIs are invisible to macOS Accessibility** — screen readers and
  automation tools cannot read knob positions from the VST's custom UI.
- **No LOM API to configure parameters programmatically** — you must touch
  them manually in the GUI.
- **Only the LAST-touched parameter** is registered per Configure session — if
  you turn knob A then knob B then close Configure, only knob B is added.

### Workaround: Use Macro / Rack mapping

If you need programmatic control over many VST parameters:

1. Wrap the VST in an **Audio Effect Rack** (or Drum Rack for instruments).
2. Map each desired VST parameter to a **Macro** knob.
3. Macro knobs are always exposed and controllable via `set_parameter_value`.

---

## 7. macOS Permissions for Ableton

### Symptom

Ableton launches but LiveAgent fails to start, or browser operations
(`load_device`, `load_sample_to_pad`) fail silently, or audio analysis can't
read files.

### Required permissions

#### Full Disk Access (for file operations)

If LiveAgent or the audio analyzer needs to read files outside Ableton's
sandbox (e.g., sample libraries on external drives, `~/Desktop`, `~/Downloads`):

1. Open **System Settings → Privacy & Security → Full Disk Access**.
2. Click **+** and add **Ableton Live** (from `/Applications/`).
3. Restart Ableton.

This is especially important for:
- `import_audio_clip` reading files from restricted locations
- `audio_analyzer.py` scanning sample folders
- `create_smart_folder` creating symlinks in the User Library

#### Microphone (for audio input)

If using live audio input tracks:

1. **System Settings → Privacy & Security → Microphone**.
2. Enable **Ableton Live**.

#### Music / Media (for Apple Music integration)

Not typically needed for LiveAgent, but if you use Ableton's Apple Music
browser integration:

1. **System Settings → Privacy & Security → Media & Apple Music**.
2. Enable **Ableton Live**.

#### Automation (for script-based control)

If you control Ableton via AppleScript (`osascript`) or other automation:

1. **System Settings → Privacy & Security → Automation**.
2. Allow your terminal/agent app to control **Ableton Live**.

### App Sandbox / Gatekeeper issues

If you downloaded Ableton outside the Mac App Store and it's quarantined:

```bash
# Remove quarantine attribute (only if you trust the source)
xattr -dr com.apple.quarantine "/Applications/Ableton Live 12 Standard.app"
```

### Verifying permissions are working

```bash
# Test file access from the audio analyzer
python3 audio_analyzer.py ~/Desktop/test.wav

# If this fails with "Operation not permitted", Full Disk Access is missing
```

---

## 8. MCP Server Not Starting

### Symptom

Your MCP client (Claude Desktop, Cursor, etc.) reports the Ableton Live server
as failed or shows no tools.

### Checklist

1. **Verify the venv Python path** — use the absolute path to the project's
   virtual environment:
   ```json
   "command": "/path/to/live-agent-remote/.venv/bin/python3"
   ```
   Not `/usr/bin/python3` or `python` (the system Python may lack `mcp`).

2. **Install MCP dependencies:**
   ```bash
   cd live-agent-remote
   python3 -m venv .venv
   .venv/bin/pip install "mcp[cli]" librosa soundfile numpy scipy
   ```

3. **Test the server manually:**
   ```bash
   /path/to/live-agent-remote/.venv/bin/python3 /path/to/live-agent-remote/mcp_server.py
   ```
   It should start and wait for stdin (no output, no crash). Press `Ctrl+C` to
   exit.

4. **Check the config file path:**
   - Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Cursor: `.cursor/mcp.json` (in your project root)

5. **Restart the MCP client** after editing the config.

See [mcp-clients.md](mcp-clients.md) for detailed per-client setup.

---

## 9. eval / exec Return "Disabled"

### Symptom

```
"eval is disabled. Set LIVEAGENT_ENABLE_UNSAFE=1 environment variable to enable."
```

### Cause

This is expected behavior. `eval` and `exec` are disabled by default for
security. See [security.md](security.md#2-eval--exec--disabled-by-default)
for details.

### Solution

Set `LIVEAGENT_ENABLE_UNSAFE=1` **before launching Ableton**:

```bash
LIVEAGENT_ENABLE_UNSAFE=1 open -a "Ableton Live 12 Standard"
```

Then verify in the LiveAgent log (check Ableton's `Log.txt`) that it reports
`unsafe=True`.

> **⚠️ Only enable this on trusted machines.** See the
> [Security Model](security.md) for the implications.
