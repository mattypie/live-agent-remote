"""Tests for the event-push feature (phase 4/C).

The snapshot/diff logic lives in ``LiveAgent/LiveAgent.py``, which imports
``_Framework.ControlSurface`` (only available inside Ableton). To test the
pure diff logic without Live, we load the source and exec just the
module-level function and the static diff method, bypassing the Live import.
"""

import os
import types

# ── Load the pure functions from LiveAgent.py without importing Live ───────
# We can't `import LiveAgent.LiveAgent` in CI (no _Framework). Instead we read
# the source, extract the two pure pieces we need, and bind them.
_LIVE_AGENT_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "LiveAgent", "LiveAgent.py",
)


def _load_pure_funcs():
    """Extract ``_event_in_category`` and ``_diff_state`` from LiveAgent.py.

    ``_event_in_category`` is a module-level function; ``_diff_state`` is a
    staticmethod on the LiveAgent class. We parse the source with ``ast`` to
    pull their bodies into a throwaway module, so they're testable in CI.
    """
    import ast

    with open(_LIVE_AGENT_SRC, encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)

    # Collect the module-level _event_in_category and the class-level _diff_state.
    wanted = {"_event_in_category", "_diff_state"}
    func_defs = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            func_defs.append(ast.FunctionDef(
                name=node.name, args=node.args, body=node.body,
                decorator_list=[], returns=node.returns,
                lineno=1, col_offset=0,
            ))
            wanted.discard(node.name)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef) and node.name == "LiveAgent":
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef) and item.name in wanted:
                    func_defs.append(ast.FunctionDef(
                        name=item.name, args=item.args, body=item.body,
                        decorator_list=[], returns=item.returns,
                        lineno=1, col_offset=0,
                    ))
                    wanted.discard(item.name)

    module = types.ModuleType("_liveagent_pure")
    module.__dict__["__name__"] = "_liveagent_pure"

    # Build a module body that contains just these functions, then exec it.
    mod_tree = ast.Module(body=func_defs, type_ignores=[])
    ast.fix_missing_locations(mod_tree)
    code = compile(mod_tree, _LIVE_AGENT_SRC, "exec")
    exec(code, module.__dict__)  # noqa: S102 (intentional for test isolation)
    return module


_pure = _load_pure_funcs()
_event_in_category = _pure._event_in_category
_diff_state = _pure._diff_state


# ── _event_in_category ────────────────────────────────────────────────────


class TestEventInCategory:
    def test_transport_event_matches_transport_category(self):
        assert _event_in_category("transport_changed", ["transport"]) is True

    def test_mixer_event_matches_mixer_category(self):
        assert _event_in_category("mixer_changed", ["mixer"]) is True

    def test_clip_events_match_scenes_category(self):
        assert _event_in_category("clip_launched", ["scenes"]) is True
        assert _event_in_category("clip_stopped", ["scenes"]) is True

    def test_all_categories_match_all_events(self):
        cats = ["transport", "mixer", "scenes"]
        assert _event_in_category("transport_changed", cats) is True
        assert _event_in_category("mixer_changed", cats) is True
        assert _event_in_category("clip_launched", cats) is True

    def test_no_match_when_category_not_subscribed(self):
        assert _event_in_category("transport_changed", ["mixer"]) is False
        assert _event_in_category("mixer_changed", ["scenes"]) is False
        assert _event_in_category("clip_launched", ["transport"]) is False


# ── _diff_state ───────────────────────────────────────────────────────────


def _snapshot(transport=None, tracks=None):
    """Build a minimal snapshot dict matching _snapshot_state's shape."""
    transport = transport or {
        "tempo": 120.0, "is_playing": False,
        "signature_numerator": 4, "signature_denominator": 4,
        "metronome": False, "overdub": False,
    }
    tracks = tracks or []
    return {"transport": transport, "tracks": tracks}


class TestDiffTransport:
    def test_no_change_yields_no_events(self):
        snap = _snapshot()
        assert _diff_state(snap, snap) == []

    def test_first_snapshot_emits_full_state(self):
        """Comparing against an empty (initial) snapshot reports all fields.

        Note: the actual flood-suppression (not emitting on the first snapshot)
        happens in ``_maybe_push_events`` via the ``_baseline_set`` flag, not
        in ``_diff_state`` itself. Here we just verify the diff is complete.
        """
        snap = _snapshot()
        events = _diff_state({}, snap)
        # All transport fields are "new" → one transport_changed event.
        assert len(events) == 1
        assert events[0]["event"] == "transport_changed"
        assert "tempo" in events[0]["data"]

    def test_tempo_change_emits_transport_event(self):
        old = _snapshot()
        new = _snapshot(transport={
            "tempo": 130.0, "is_playing": False,
            "signature_numerator": 4, "signature_denominator": 4,
            "metronome": False, "overdub": False,
        })
        events = _diff_state(old, new)
        assert len(events) == 1
        assert events[0]["event"] == "transport_changed"
        assert events[0]["data"]["tempo"] == 130.0

    def test_playing_change_emits_transport_event(self):
        old = _snapshot()
        new = _snapshot(transport={
            "tempo": 120.0, "is_playing": True,
            "signature_numerator": 4, "signature_denominator": 4,
            "metronome": False, "overdub": False,
        })
        events = _diff_state(old, new)
        assert len(events) == 1
        assert events[0]["data"]["is_playing"] is True


class TestDiffMixer:
    def _track(self, index, volume=0.5, pan=0.0, mute=False, solo=False, arm=False, slots=None):
        return {
            "index": index, "volume": volume, "pan": pan,
            "mute": mute, "solo": solo, "arm": arm,
            "slots": slots or [],
        }

    def test_volume_change_emits_mixer_event(self):
        old = _snapshot(tracks=[self._track(0, volume=0.5)])
        new = _snapshot(tracks=[self._track(0, volume=0.9)])
        events = _diff_state(old, new)
        assert len(events) == 1
        assert events[0]["event"] == "mixer_changed"
        assert events[0]["data"]["track_index"] == 0
        assert events[0]["data"]["changes"]["volume"] == 0.9

    def test_mute_change_emits_mixer_event(self):
        old = _snapshot(tracks=[self._track(0, mute=False)])
        new = _snapshot(tracks=[self._track(0, mute=True)])
        events = _diff_state(old, new)
        assert events[0]["event"] == "mixer_changed"
        assert events[0]["data"]["changes"]["mute"] is True

    def test_multiple_mixer_changes_in_one_track(self):
        old = _snapshot(tracks=[self._track(0, volume=0.5, solo=False)])
        new = _snapshot(tracks=[self._track(0, volume=0.8, solo=True)])
        events = _diff_state(old, new)
        assert len(events) == 1
        changes = events[0]["data"]["changes"]
        assert changes == {"volume": 0.8, "solo": True}

    def test_no_mixer_change_no_event(self):
        old = _snapshot(tracks=[self._track(0)])
        new = _snapshot(tracks=[self._track(0)])
        assert _diff_state(old, new) == []


class TestDiffClips:
    def _slot(self, is_playing=False, is_triggered=False):
        return {"is_playing": is_playing, "is_triggered": is_triggered}

    def test_clip_launch_emits_event(self):
        old = _snapshot(tracks=[{"index": 0, "slots": [self._slot(is_playing=False)]}])
        new = _snapshot(tracks=[{"index": 0, "slots": [self._slot(is_playing=True)]}])
        events = _diff_state(old, new)
        assert len(events) == 1
        assert events[0]["event"] == "clip_launched"
        assert events[0]["data"] == {"track_index": 0, "slot_index": 0}

    def test_clip_stop_emits_event(self):
        old = _snapshot(tracks=[{"index": 1, "slots": [self._slot(is_playing=True)]}])
        new = _snapshot(tracks=[{"index": 1, "slots": [self._slot(is_playing=False)]}])
        events = _diff_state(old, new)
        assert events[0]["event"] == "clip_stopped"
        assert events[0]["data"] == {"track_index": 1, "slot_index": 0}

    def test_new_slot_added_does_not_crash(self):
        old = _snapshot(tracks=[{"index": 0, "slots": [self._slot()]}])
        new = _snapshot(tracks=[{"index": 0, "slots": [self._slot(), self._slot(is_playing=True)]}])
        events = _diff_state(old, new)
        # The second slot is new; is_playing went from (missing→False) to True.
        # old_slot.get("is_playing", False) → False, so it should fire.
        assert any(e["event"] == "clip_launched" for e in events)
