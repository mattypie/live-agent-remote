/**
 * LiveAgent Remote Client — JavaScript / Node.js
 * ================================================
 * Connects to LiveAgent running inside Ableton Live.
 *
 * Usage:
 *   const { LiveAgentClient } = require('./live_agent_client');
 *   const client = new LiveAgentClient();
 *   const state = await client.ping();
 *   const tracks = await client.list_tracks();
 *   await client.loadDevice(1, 'Massive');
 *   client.close();
 */

const net = require('net');

class LiveAgentClient {
  constructor(host = '127.0.0.1', port = 8765, timeout = 10000) {
    this.host = host;
    this.port = port;
    this.timeout = timeout;
  }

  _send(command, payload = null) {
    return new Promise((resolve, reject) => {
      const sock = net.createConnection({ host: this.host, port: this.port }, () => {
        const request = payload ? { command, payload } : { command };
        sock.write(JSON.stringify(request) + '\n');
      });

      let buf = '';
      const timer = setTimeout(() => {
        sock.destroy();
        reject(new Error('Connection timed out'));
      }, this.timeout);

      sock.on('data', (data) => {
        buf += data.toString();
        if (buf.includes('\n')) {
          clearTimeout(timer);
          sock.destroy();
          try {
            const resp = JSON.parse(buf.trim());
            if (!resp.ok) {
              reject(new Error(resp.error || 'Unknown error'));
            } else {
              resolve(resp.result);
            }
          } catch (e) {
            reject(e);
          }
        }
      });

      sock.on('error', (err) => {
        clearTimeout(timer);
        reject(err);
      });
    });
  }

  // ── Commands ────────────────────────────────────────────

  ping()                           { return this._send('ping'); }
  getLiveState()                   { return this._send('get_live_state'); }
  listTracks()                     { return this._send('list_tracks'); }
  createMidiTrack(index = -1)      { return this._send('create_midi_track', { index }); }

  // ── Transport & Playback ──────────────────────────────

  getTransportState()              { return this._send('get_transport_state'); }
  startPlaying()                   { return this._send('start_playing'); }
  stopPlaying()                    { return this._send('stop_playing'); }
  stopAllClips()                   { return this._send('stop_all_clips'); }
  setTempo(tempo)                  { return this._send('set_tempo', { tempo }); }
  tapTempo()                       { return this._send('tap_tempo'); }

  setTimeSignature(opts) {
    const payload = {};
    if (opts.numerator != null) payload.numerator = opts.numerator;
    if (opts.denominator != null) payload.denominator = opts.denominator;
    return this._send('set_time_signature', payload);
  }

  setMetronome(enabled)            { return this._send('set_metronome', { enabled }); }
  setOverdub(enabled)              { return this._send('set_overdub', { enabled }); }
  launchScene(sceneIndex)          { return this._send('launch_scene', { scene_index: sceneIndex }); }

  launchClip(opts) {
    return this._send('launch_clip', {
      track_index: opts.trackIndex,
      slot_index: opts.slotIndex,
    });
  }

  // ── Mixer ──────────────────────────────────────────────

  setTrackVolume(opts) {
    return this._send('set_track_volume', {
      track_index: opts.trackIndex,
      volume: opts.volume,
    });
  }

  setTrackPan(opts) {
    return this._send('set_track_pan', {
      track_index: opts.trackIndex,
      pan: opts.pan,
    });
  }

  setTrackMute(opts) {
    return this._send('set_track_mute', {
      track_index: opts.trackIndex,
      mute: opts.mute,
    });
  }

  setTrackSolo(opts) {
    return this._send('set_track_solo', {
      track_index: opts.trackIndex,
      solo: opts.solo,
    });
  }

  setTrackArm(opts) {
    return this._send('set_track_arm', {
      track_index: opts.trackIndex,
      arm: opts.arm,
    });
  }

  setTrackSend(opts) {
    return this._send('set_track_send', {
      track_index: opts.trackIndex,
      send_index: opts.sendIndex,
      value: opts.value,
    });
  }

  setTrackMonitoring(opts) {
    return this._send('set_track_monitoring', {
      track_index: opts.trackIndex,
      monitoring: opts.monitoring,
    });
  }

  setCrossfader(position) {
    return this._send('set_crossfader', { position });
  }

  createSessionClip(opts) {
    return this._send('create_session_clip', {
      track_index: opts.trackIndex,
      slot_index: opts.slotIndex,
      length_beats: opts.lengthBeats || 16,
      name: opts.name || '',
      replace: opts.replace !== false,
    });
  }

  writeMidiNotes(opts) {
    return this._send('write_midi_notes', {
      track_index: opts.trackIndex,
      slot_index: opts.slotIndex,
      notes: opts.notes,
    });
  }

  readClipNotes(opts) {
    return this._send('read_clip_notes', {
      track_index: opts.trackIndex,
      slot_index: opts.slotIndex,
      length_beats: opts.lengthBeats || 16,
    });
  }

  clearClipNotes(opts) {
    return this._send('clear_clip_notes', {
      track_index: opts.trackIndex,
      slot_index: opts.slotIndex,
    });
  }

  listDevices(trackIndex) {
    return this._send('list_devices', { track_index: trackIndex });
  }

  setParameterValue(opts) {
    const payload = { track_index: opts.trackIndex, value: opts.value };
    if (opts.deviceIndex != null) payload.device_index = opts.deviceIndex;
    if (opts.deviceName) payload.device_name = opts.deviceName;
    if (opts.parameterIndex != null) payload.parameter_index = opts.parameterIndex;
    if (opts.parameterName) payload.parameter_name = opts.parameterName;
    return this._send('set_parameter_value', payload);
  }

  writeClipAutomation(opts) {
    const payload = {
      track_index: opts.trackIndex,
      slot_index: opts.slotIndex,
      points: opts.points,
      step_duration: opts.stepDuration || 0.25,
    };
    if (opts.deviceIndex != null) payload.device_index = opts.deviceIndex;
    if (opts.deviceName) payload.device_name = opts.deviceName;
    if (opts.parameterIndex != null) payload.parameter_index = opts.parameterIndex;
    if (opts.parameterName) payload.parameter_name = opts.parameterName;
    return this._send('write_clip_automation', payload);
  }

  loadDevice(trackIndex, deviceName, browserType = 'plug-in') {
    return this._send('load_device', {
      track_index: trackIndex,
      device_name: deviceName,
      browser_type: browserType,
    });
  }

  listBrowserDevices(browserType = 'plug-in', query = '', maxResults = 100) {
    return this._send('list_browser_devices', {
      browser_type: browserType,
      query,
      max_results: maxResults,
    });
  }
}

module.exports = { LiveAgentClient };
