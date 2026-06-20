#!/usr/bin/env python3
"""
Example: Build a drum beat, set the tempo, then launch it.

Demonstrates the transport commands: set_tempo, launch_clip, start_playing.
Assumes track 1 exists and has a Drum Rack (run create_drum_rack first, or
point PAD samples at your own kit).

Pad layout (General MIDI percussion):
  36 = Kick, 38 = Snare, 42 = Closed Hat
"""

import time

from live_agent_client import LiveAgentClient

# 16-step grid. Each step = a 16th note. 4 beats per bar = 16 steps.
STEPS = 16
KICK = 36
SNARE = 38
HAT = 42

# Simple four-on-the-floor: kick on 1/5/9/13, snare on 5/13, hats every step.
PATTERN = {
    KICK:  [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
    SNARE: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    HAT:   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
}

TEMPO = 124.0


def build_notes():
    """Convert the step grid into LiveAgent note objects."""
    notes = []
    for pitch, hits in PATTERN.items():
        for step, on in enumerate(hits):
            if on:
                notes.append({
                    "pitch": pitch,
                    "start": step * 0.25,        # 16th note = 0.25 beats
                    "duration": 0.2,
                    "velocity": 100 if pitch == SNARE else 110,
                })
    return notes


def main():
    client = LiveAgentClient()

    # Check connection
    print("Ping:", client.ping())

    # Set the tempo before playing
    client.set_tempo(TEMPO)
    print(f"Tempo set to {TEMPO} BPM")

    # Create a 1-bar clip on track 1, slot 0 and write the beat
    client.create_session_clip(track_index=1, slot_index=0, length_beats=4)
    result = client.write_midi_notes(track_index=1, slot_index=0, notes=build_notes())
    print(f"Wrote {result['note_count']} drum hits")

    # Launch the clip and start the transport
    client.launch_clip(track_index=1, slot_index=0)
    print("Clip launched")

    # Give Live a moment to register the launch, then confirm transport state
    time.sleep(0.5)
    state = client.get_transport_state()
    print("Transport state:", state)

    # Let it play for a few bars, then stop
    print("Playing for ~8 seconds...")
    time.sleep(8)
    client.stop_all_clips()
    client.stop_playing()
    print("Stopped.")

    client.close()


if __name__ == "__main__":
    main()
