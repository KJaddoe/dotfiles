#!/usr/bin/env python3
"""Tests for the suggest-fresh-session hook.

Run: python3 claude/hooks/tests/test_suggest_fresh_session.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "suggest-fresh-session.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("suggest_fresh_session", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def write_transcript(path, user_turns=0, tool_results=0, meta=0, padding=0):
    """Write a transcript whose entry mix is known, for measuring against.

    :param path: file to write
    :param user_turns: real user messages, the only entries that count as turns
    :param tool_results: `type: user` entries carrying `toolUseResult`, which must not count
    :param meta: `type: user` entries flagged `isMeta`, which must not count
    :param padding: assistant entries, present only to add bytes
    :return: the file's byte length
    """
    lines = []
    for i in range(user_turns):
        lines.append({"type": "user", "message": {"role": "user", "content": f"turn {i}"}})
    for i in range(tool_results):
        lines.append({"type": "user", "toolUseResult": {"stdout": f"out {i}"}})
    for i in range(meta):
        lines.append({"type": "user", "isMeta": True, "message": {"content": f"meta {i}"}})
    for _ in range(padding):
        lines.append({"type": "assistant", "message": {"content": "x" * 200}})
    body = "\n".join(json.dumps(line) for line in lines) + "\n"
    path.write_text(body, encoding="utf-8")
    return len(body.encode("utf-8"))


class TestMeasure(unittest.TestCase):
    """Weight is counted from the transcript, from an offset, excluding non-turns."""

    def test_counts_real_user_turns(self):
        """A real user message is a turn."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            size = write_transcript(path, user_turns=3)
            self.assertEqual(hook.measure(path, 0), (size, 3))

    def test_excludes_tool_results_and_meta(self):
        """`toolUseResult` and `isMeta` entries carry `type: user` but are not turns."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            write_transcript(path, user_turns=2, tool_results=5, meta=4)
            self.assertEqual(hook.measure(path, 0)[1], 2)

    def test_offset_excludes_everything_before_it(self):
        """Measuring from an offset ignores the prefix."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            first = write_transcript(path, user_turns=4)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"type": "user", "message": {"content": "after"}}) + "\n")
            self.assertEqual(hook.measure(path, first)[1], 1)

    def test_offset_past_end_is_treated_as_zero(self):
        """A rotated or truncated transcript must not measure negative."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            size = write_transcript(path, user_turns=2)
            self.assertEqual(hook.measure(path, size + 10_000)[1], 2)

    def test_unparsable_line_is_skipped_not_raised(self):
        """A partial trailing write must not take the hook down."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            write_transcript(path, user_turns=2)
            with path.open("a", encoding="utf-8") as handle:
                handle.write('{"type": "user", "mess')
            self.assertEqual(hook.measure(path, 0)[1], 2)

    def test_missing_file_is_zero(self):
        """An absent transcript measures as empty rather than raising."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(hook.measure(Path(tmp) / "nope.jsonl", 0), (0, 0))


class TestConfiguration(unittest.TestCase):
    """Both env vars fall back to their default rather than failing."""

    def setUp(self):
        """Start each case from a clean environment."""
        self._clear()
        self.addCleanup(self._clear)

    def _clear(self):
        """Remove the vars a case set."""
        for name in ("FRESH_SESSION_HOOK_MODE", "FRESH_SESSION_HOOK_BYTES"):
            os.environ.pop(name, None)

    def test_mode_defaults_to_on(self):
        """An unset mode injects."""
        self.assertEqual(hook.mode(), "on")

    def test_mode_reads_the_env_var(self):
        """A valid mode is honoured."""
        os.environ["FRESH_SESSION_HOOK_MODE"] = "dry-run"
        self.assertEqual(hook.mode(), "dry-run")

    def test_unknown_mode_falls_back_to_on(self):
        """A typo must not silently disable the hook."""
        os.environ["FRESH_SESSION_HOOK_MODE"] = "enforce"
        self.assertEqual(hook.mode(), "on")

    def test_threshold_defaults(self):
        """An unset threshold uses the tuned default."""
        self.assertEqual(hook.threshold(), hook.DEFAULT_THRESHOLD_BYTES)

    def test_threshold_reads_the_env_var(self):
        """A numeric threshold is honoured."""
        os.environ["FRESH_SESSION_HOOK_BYTES"] = "900000"
        self.assertEqual(hook.threshold(), 900_000)

    def test_non_numeric_threshold_falls_back(self):
        """Garbage must not crash a prompt."""
        os.environ["FRESH_SESSION_HOOK_BYTES"] = "lots"
        self.assertEqual(hook.threshold(), hook.DEFAULT_THRESHOLD_BYTES)


class TestMarkers(unittest.TestCase):
    """A marker records a byte offset and is swept once it is stale."""

    def setUp(self):
        """Point the hook's state directory at a temporary one."""
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.state = self.tmp / "state"
        os.environ["FRESH_SESSION_STATE_DIR"] = str(self.state)
        self.addCleanup(os.environ.pop, "FRESH_SESSION_STATE_DIR", None)

    def _marker(self, session_id, transcript, offset=0, age_seconds=0):
        """Write a marker directly, optionally backdating its mtime.

        :param session_id: session the marker belongs to
        :param transcript: transcript path the marker records
        :param offset: byte offset the marker records
        :param age_seconds: how far in the past to set the marker's mtime
        :return: the marker's path
        """
        self.state.mkdir(parents=True, exist_ok=True)
        path = self.state / f"{session_id}.json"
        path.write_text(
            json.dumps({"offset": offset, "transcript_path": str(transcript)}),
            encoding="utf-8",
        )
        if age_seconds:
            stamp = time.time() - age_seconds
            os.utime(path, (stamp, stamp))
        return path

    def test_write_then_read_round_trips_the_offset(self):
        """A recorded offset comes back."""
        transcript = self.tmp / "t.jsonl"
        write_transcript(transcript, user_turns=1)
        hook.write_marker("abc", transcript, 1234)
        self.assertEqual(hook.read_marker("abc"), 1234)

    def test_absent_marker_reads_as_zero(self):
        """No marker means measure from the start."""
        self.assertEqual(hook.read_marker("nothing"), 0)

    def test_corrupt_marker_reads_as_zero(self):
        """A truncated write must not raise."""
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "bad.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(hook.read_marker("bad"), 0)

    def test_sweep_deletes_marker_whose_transcript_is_gone(self):
        """Claude Code's own retention removes transcripts; the marker follows."""
        path = self._marker("dead", self.tmp / "gone.jsonl")
        hook.sweep()
        self.assertFalse(path.exists())

    def test_sweep_deletes_marker_older_than_the_age_cap(self):
        """A marker outliving its usefulness is removed on age alone."""
        transcript = self.tmp / "t.jsonl"
        write_transcript(transcript, user_turns=1)
        path = self._marker("old", transcript, age_seconds=hook.MARKER_MAX_AGE_SECONDS + 60)
        hook.sweep()
        self.assertFalse(path.exists())

    def test_sweep_keeps_a_live_recent_marker(self):
        """The sweep must not delete what is still in use."""
        transcript = self.tmp / "t.jsonl"
        write_transcript(transcript, user_turns=1)
        path = self._marker("live", transcript)
        hook.sweep()
        self.assertTrue(path.exists())

    def test_sweep_deletes_a_corrupt_marker(self):
        """An unreadable marker is stale by definition."""
        self.state.mkdir(parents=True, exist_ok=True)
        path = self.state / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        hook.sweep()
        self.assertFalse(path.exists())

    def test_sweep_on_absent_directory_is_a_noop(self):
        """First run has no state directory yet."""
        hook.sweep()
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
