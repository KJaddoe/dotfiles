#!/usr/bin/env python3
"""UserPromptSubmit nudge: offer a fresh session once this one has grown heavy.

Enforces nothing. It measures how much transcript this session is carrying and, past a
threshold, injects a note telling the model to judge whether the incoming prompt actually
depends on the conversation so far, and to ask the user about /clear when it does not.

The split is deliberate. "How heavy is this session" is mechanical and belongs here. "Does this
prompt need the previous context" is semantic and belongs to the model, so it lives in
`build_note` rather than in a regex. There is no state file recording whether the user already
declined: the conversation records that, and the conversation is the only thing that knows
whether the topic has since moved.

Invoked two ways. Without arguments it is the UserPromptSubmit path. With `--mark` it is the
SessionStart path for `compact` only: /clear rotates to a new session id and a new transcript
file, so there is nothing to offset from there.

It never blocks, never denies, and exits 0 on every path including failure. A hook whose only
job is a suggestion must not be able to break a prompt.
"""

import json
import os
import sys
import time
from pathlib import Path

from _hookutil import read_payload

DEFAULT_LOG_PATH = Path.home() / ".claude" / "logs" / "fresh-session-hook.log"

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


def log_path():
    """Locate the dry-run log, overridable so the suite never writes to the real one.

    :return: file the dry-run mode appends to
    """
    override = os.environ.get("FRESH_SESSION_LOG_PATH")
    return Path(override) if override else DEFAULT_LOG_PATH


def human_bytes(count):
    """Render a byte count the way a person reads one.

    :param count: number of bytes
    :return: a short string such as "1.2MB"
    """
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}MB"
    if count >= 1_000:
        return f"{count / 1_000:.0f}KB"
    return f"{count}B"


def build_note(turns, size):
    """Build the context injected into a heavy session.

    Two of the design's decisions live in this text rather than in code, because they are model
    behaviour rather than program behaviour: hand the prompt back on acceptance, and note an
    unacted acceptance once without re-asking. Changing how the model behaves means changing
    this string, so the test suite asserts the load-bearing phrases are present.

    :param turns: real user turns measured
    :param size: bytes measured
    :return: the note to inject
    """
    return (
        f"Session weight: {turns} user turns, {human_bytes(size)} of transcript. "
        "Before answering, judge whether this prompt depends on anything earlier in this "
        "conversation. If it does not, do not start work: ask the user via AskUserQuestion "
        "whether to /clear first, and on acceptance reply with nothing but their prompt handed "
        "back verbatim in a copyable block, since you cannot run /clear yourself. If you already "
        "asked during the current thread and they declined, stay silent until the topic shifts "
        "again. If they accepted a clear that has not happened, say in one line that it is still "
        "pending and answer normally; do not ask again."
    )


def log_dry_run(note):
    """Append what would have been injected, for tuning the threshold against real sessions.

    :param note: the note that `on` mode would have emitted
    """
    try:
        target = log_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with target.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} {note}\n")
    except OSError:
        pass


def transcript_from(data):
    """Pull the transcript path out of a payload.

    :param data: the hook payload
    :return: the transcript path, or None when the payload does not carry a usable one
    """
    raw = data.get("transcript_path")
    return Path(raw) if raw else None


def run_mark(data):
    """Record a compaction boundary, sweeping stale markers first.

    :param data: the SessionStart payload
    """
    sweep()
    transcript = transcript_from(data)
    session_id = data.get("session_id")
    if not transcript or not session_id:
        return
    try:
        size = transcript.stat().st_size
    except OSError:
        return
    write_marker(session_id, transcript, size)


def run_nudge(data):
    """Measure the session and inject the note when it has grown heavy.

    :param data: the UserPromptSubmit payload
    """
    current = mode()
    if current == "off":
        return

    transcript = transcript_from(data)
    if not transcript:
        return

    size, turns = measure(transcript, read_marker(data.get("session_id") or ""))
    if size < threshold():
        return

    note = build_note(turns, size)
    if current == "dry-run":
        log_dry_run(note)
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": note,
                }
            }
        )
    )


def main():
    """Dispatch to the mark or the nudge path, never failing either way."""
    data = read_payload()
    if data is None:
        sys.exit(0)

    try:
        if "--mark" in sys.argv[1:]:
            run_mark(data)
        else:
            run_nudge(data)
    # Deliberately broad: this runs on every prompt submission, so an unexpected failure must
    # cost a missing suggestion, never the user's ability to send the prompt at all.
    except Exception:  # pylint: disable=broad-except
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
