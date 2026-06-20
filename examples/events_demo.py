#!/usr/bin/env python3
"""
Example: Subscribe to Live state-change events and print them.

Demonstrates the event-push feature (phase 4/C). LiveAgent snapshots
transport/mixer/clip state every 250ms and pushes change events to
subscribers on port 8766.

Run this, then change tempo / play-stop / move faders in Ableton — the
changes print here in real time. Press Ctrl+C to stop.
"""

import sys
import time

from live_agent_client import LiveAgentSubscriber


def main():
    print("Connecting to LiveAgent event stream on 127.0.0.1:8766 ...")
    try:
        sub = LiveAgentSubscriber()
    except (ConnectionError, OSError) as err:
        print("Could not connect: %s" % err)
        print("Is Ableton Live running with the LiveAgent control surface active?")
        sys.exit(1)

    # Register handlers for each event type.
    sub.on("transport_changed", lambda data: print("  [transport] %s" % data))
    sub.on("mixer_changed", lambda data: print("  [mixer]      %s" % data))
    sub.on("clip_launched", lambda data: print("  [clip▶]      track %s slot %s" % (data.get("track_index"), data.get("slot_index"))))
    sub.on("clip_stopped", lambda data: print("  [clip■]      track %s slot %s" % (data.get("track_index"), data.get("slot_index"))))

    # Catch-all for anything unexpected.
    sub.on("*", lambda name, data: None)  # already handled above; no-op

    sub.listen()
    print("Subscribed! Change something in Ableton (tempo, play/stop, faders).")
    print("Press Ctrl+C to stop.\n")

    try:
        # The listener runs in a daemon thread; block the main thread.
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping.")
        sub.close()


if __name__ == "__main__":
    main()
