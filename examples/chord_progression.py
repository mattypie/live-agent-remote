#!/usr/bin/env python3
"""
Example: Create a chord progression on track 1, slot 0
"""

from live_agent_client import LiveAgentClient

# Chord voicings (MIDI note numbers)
CHORDS = {
    "Cmaj7": [48, 52, 55, 59],
    "Dm7":   [50, 53, 57, 60],
    "Em7":   [52, 55, 59, 62],
    "Fmaj7": [53, 57, 60, 64],
    "G7":    [55, 59, 62, 65],
    "Am7":   [57, 60, 64, 67],
}

def main():
    client = LiveAgentClient()

    # Check connection
    print("Ping:", client.ping())

    # Create a 4-bar clip
    progression = ["Cmaj7", "Dm7", "Em7", "Am7"]
    client.create_session_clip(
        track_index=1, slot_index=0,
        length_beats=16, name="ii-V-I Practice"
    )

    # Write chord notes (each chord = 1 bar = 4 beats)
    notes = []
    for i, chord_name in enumerate(progression):
        for pitch in CHORDS[chord_name]:
            notes.append({
                "pitch": pitch,
                "start": i * 4,
                "duration": 3.9,
                "velocity": 80,
            })

    result = client.write_midi_notes(track_index=1, slot_index=0, notes=notes)
    print(f"Wrote {result['note_count']} notes to clip")

    # List devices on the track
    devices = client.list_devices(track_index=1)
    print("Devices:", [d["name"] for d in devices["track"]["devices"]])

    client.close()


if __name__ == "__main__":
    main()
