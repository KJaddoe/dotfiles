#!/usr/bin/env python3
"""UserPromptSubmit nudge: offer a fresh session once this one has grown heavy.

Enforces nothing. It measures how much transcript a session is carrying so that, past a
threshold, the model can be told to judge whether the incoming prompt actually depends on the
conversation so far.

The split is deliberate. "How heavy is this session" is mechanical and belongs here. "Does this
prompt need the previous context" is semantic and belongs to the model, so it lives in injected
text rather than in a regex.

It never blocks, never denies, and exits 0 on every path including failure. A hook whose only
job is a suggestion must not be able to break a prompt.
"""

import json
import os
import sys
import time
from pathlib import Path

DEFAULT_STATE_DIR = Path.home() / ".claude" / "state" / "fresh-session"

DEFAULT_THRESHOLD_BYTES = 600_000

# Claude Code's own `cleanupPeriodDays` sweep does not cover ~/.claude/state, so markers are
# swept here. A marker is disposable: absent means "measure from zero", the safe default.
MARKER_MAX_AGE_SECONDS = 14 * 24 * 60 * 60

VALID_MODES = {"on", "off", "dry-run"}


def mode():
    """Read the hook's mode, defaulting rather than failing on an unknown value.

    An unrecognised value falls back to `on`: a typo in an env var must not silently disable
    the hook, which would be indistinguishable from it working and finding nothing.

    :return: one of "on", "off", "dry-run"
    """
    value = (os.environ.get("FRESH_SESSION_HOOK_MODE") or "on").strip().lower()
    return value if value in VALID_MODES else "on"


def threshold():
    """Read the byte threshold, defaulting rather than failing on a non-numeric value.

    :return: the byte count at or above which the note is injected
    """
    raw = os.environ.get("FRESH_SESSION_HOOK_BYTES")
    if not raw:
        return DEFAULT_THRESHOLD_BYTES
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD_BYTES
    return value if value > 0 else DEFAULT_THRESHOLD_BYTES


def state_dir():
    """Locate the marker directory, overridable so the suite never writes to the real one.

    :return: directory holding this hook's markers
    """
    override = os.environ.get("FRESH_SESSION_STATE_DIR")
    return Path(override) if override else DEFAULT_STATE_DIR


def marker_path(session_id):
    """Locate a session's marker file.

    :param session_id: the session's id
    :return: path the marker would occupy
    """
    return state_dir() / f"{session_id}.json"


def read_marker(session_id):
    """Read a session's recorded byte offset.

    Every failure reads as 0, which means "measure from the start". The marker is disposable by
    construction, so losing one costs an overstated measurement, never a broken prompt.

    :param session_id: the session's id
    :return: the recorded offset, or 0 when absent or unreadable
    """
    try:
        data = json.loads(marker_path(session_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return 0
    offset = data.get("offset") if isinstance(data, dict) else 0
    return offset if isinstance(offset, int) and offset > 0 else 0


def write_marker(session_id, transcript_path, offset):
    """Record where a session's post-compaction transcript begins.

    The transcript path is stored alongside the offset so the sweep can tell a live marker from
    one whose session has already been cleaned up.

    :param session_id: the session's id
    :param transcript_path: the session's transcript
    :param offset: byte length of the transcript at compaction time
    """
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        marker_path(session_id).write_text(
            json.dumps({"offset": offset, "transcript_path": str(transcript_path)}),
            encoding="utf-8",
        )
    except OSError:
        pass


def sweep():
    """Delete markers whose session is gone or which have simply aged out.

    Claude Code's built-in `cleanupPeriodDays` retention covers ~/.claude/projects, tasks,
    shell-snapshots and backups. It does not cover ~/.claude/state, so this directory sweeps
    itself. A corrupt marker counts as stale: it can no longer be read, so it can only grow.
    """
    try:
        markers = list(state_dir().glob("*.json"))
    except OSError:
        return

    cutoff = time.time() - MARKER_MAX_AGE_SECONDS
    for path in markers:
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            transcript = data.get("transcript_path") if isinstance(data, dict) else None
            if not transcript or not Path(transcript).exists():
                path.unlink()
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
            try:
                path.unlink()
            except OSError:
                continue


def measure(transcript_path, offset):
    """Count the bytes and real user turns a transcript carries after an offset.

    Tool results and meta injections both carry `type: user` and are not turns; counting them
    would report a session as several times heavier than it reads.

    :param transcript_path: path to the session's .jsonl transcript
    :param offset: byte offset to measure from, 0 for the whole file
    :return: (bytes after the offset, real user turns after the offset)
    """
    try:
        size = transcript_path.stat().st_size
    except OSError:
        return 0, 0

    start = offset if 0 < offset <= size else 0

    turns = 0
    try:
        with transcript_path.open("rb") as handle:
            if start:
                handle.seek(start - 1)
                if handle.read(1) != b"\n":
                    handle.readline()
            for line in handle:
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                    continue
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") != "user":
                    continue
                if "toolUseResult" in entry or entry.get("isMeta"):
                    continue
                turns += 1
    except OSError:
        return 0, 0

    return size - start, turns


def main():
    """Exit without acting; the invocations are wired in a later commit."""
    sys.exit(0)


if __name__ == "__main__":
    main()
