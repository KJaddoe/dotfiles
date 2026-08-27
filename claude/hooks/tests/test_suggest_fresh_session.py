#!/usr/bin/env python3
"""Tests for the suggest-fresh-session hook.

Run: python3 claude/hooks/tests/test_suggest_fresh_session.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import importlib.util
import json
import os
import shutil
import subprocess
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


def run_hook(payload, args=(), env=None):
    """Invoke the hook as a subprocess, the way the harness does.

    :param payload: dict written to the hook's stdin
    :param args: extra command line arguments
    :param env: env vars to add to the child's environment
    :return: the completed process
    """
    child_env = dict(os.environ)
    child_env.update(env or {})
    return subprocess.run(
        [sys.executable, str(HOOK_PATH), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
        env=child_env,
    )


class TestInjection(unittest.TestCase):
    """A heavy session injects; a light one stays silent."""

    def setUp(self):
        """Give each case its own transcript directory."""
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.transcript = self.tmp / "t.jsonl"

    def _payload(self):
        """Build a UserPromptSubmit payload for the case's transcript.

        :return: the payload dict
        """
        return {"session_id": "s1", "transcript_path": str(self.transcript)}

    def test_light_session_emits_nothing(self):
        """Below threshold the hook is silent."""
        write_transcript(self.transcript, user_turns=2)
        result = run_hook(self._payload(), env={"FRESH_SESSION_HOOK_BYTES": "1000000"})
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)

    def test_heavy_session_injects_context(self):
        """At or above threshold the note is emitted in the UserPromptSubmit shape."""
        write_transcript(self.transcript, user_turns=40, padding=200)
        result = run_hook(self._payload(), env={"FRESH_SESSION_HOOK_BYTES": "100"})
        emitted = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(emitted["hookEventName"], "UserPromptSubmit")
        self.assertIn("40 user turns", emitted["additionalContext"])
        self.assertEqual(result.returncode, 0)

    def test_note_instructs_the_model_to_ask_not_to_clear(self):
        """The note must never tell the model to run /clear itself."""
        write_transcript(self.transcript, user_turns=5, padding=100)
        result = run_hook(self._payload(), env={"FRESH_SESSION_HOOK_BYTES": "100"})
        note = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("AskUserQuestion", note)
        self.assertIn("verbatim", note)
        self.assertIn("still pending", note)

    def test_exactly_at_threshold_injects(self):
        """The threshold is inclusive; a session ON it is heavy."""
        size = write_transcript(self.transcript, user_turns=3)
        result = run_hook(self._payload(), env={"FRESH_SESSION_HOOK_BYTES": str(size)})
        self.assertIn("hookSpecificOutput", json.loads(result.stdout))

    def test_one_byte_under_threshold_stays_silent(self):
        """The boundary is exact, not approximate."""
        size = write_transcript(self.transcript, user_turns=3)
        result = run_hook(self._payload(), env={"FRESH_SESSION_HOOK_BYTES": str(size + 1)})
        self.assertEqual(result.stdout.strip(), "")

    def test_dry_run_logs_and_emits_nothing(self):
        """dry-run is for tuning the threshold without the hook talking."""
        write_transcript(self.transcript, user_turns=4, padding=50)
        log = self.tmp / "dry.log"
        result = run_hook(
            self._payload(),
            env={
                "FRESH_SESSION_HOOK_BYTES": "100",
                "FRESH_SESSION_HOOK_MODE": "dry-run",
                "FRESH_SESSION_LOG_PATH": str(log),
            },
        )
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)
        self.assertIn("user turns", log.read_text(encoding="utf-8"))

    def test_off_mode_emits_nothing(self):
        """The off switch silences a session that would otherwise inject."""
        write_transcript(self.transcript, user_turns=40, padding=200)
        result = run_hook(
            self._payload(),
            env={"FRESH_SESSION_HOOK_BYTES": "100", "FRESH_SESSION_HOOK_MODE": "off"},
        )
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)


class TestFailureModes(unittest.TestCase):
    """Nothing the hook meets may break a prompt."""

    def _raw(self, stdin):
        """Invoke the hook with raw stdin rather than a JSON payload.

        :param stdin: exact text to write to the hook's stdin
        :return: the completed process
        """
        return subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )

    def test_malformed_stdin_exits_clean(self):
        """Garbage on stdin produces no output and exit 0."""
        result = self._raw("not json")
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)

    def test_empty_stdin_exits_clean(self):
        """No payload at all produces no output and exit 0."""
        result = self._raw("")
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)

    def test_missing_transcript_path_exits_clean(self):
        """A payload without a transcript path produces no output and exit 0."""
        result = run_hook({"session_id": "s1"})
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)

    def test_nonexistent_transcript_exits_clean(self):
        """A transcript path that does not exist produces no output and exit 0."""
        result = run_hook({"session_id": "s1", "transcript_path": "/nope/missing.jsonl"})
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)

    def test_unwritable_state_directory_exits_clean(self):
        """A state directory that cannot be created must not break a prompt."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        transcript = tmp / "t.jsonl"
        write_transcript(transcript, user_turns=2)
        blocker = tmp / "blocked"
        blocker.write_text("i am a file, not a directory", encoding="utf-8")
        result = run_hook(
            {"session_id": "s1", "transcript_path": str(transcript)},
            args=["--mark"],
            env={"FRESH_SESSION_STATE_DIR": str(blocker / "nested")},
        )
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)


class TestMarkInvocation(unittest.TestCase):
    """`--mark` records the offset and emits nothing."""

    def test_mark_writes_the_offset_and_stays_silent(self):
        """A compaction records the transcript's current length."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        transcript = tmp / "t.jsonl"
        size = write_transcript(transcript, user_turns=3)
        state = tmp / "state"
        result = run_hook(
            {"session_id": "marked", "transcript_path": str(transcript)},
            args=["--mark"],
            env={"FRESH_SESSION_STATE_DIR": str(state)},
        )
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(result.returncode, 0)
        recorded = json.loads((state / "marked.json").read_text(encoding="utf-8"))
        self.assertEqual(recorded["offset"], size)
        self.assertEqual(recorded["transcript_path"], str(transcript))


if __name__ == "__main__":
    unittest.main(verbosity=2)
