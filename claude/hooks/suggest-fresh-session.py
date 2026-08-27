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
import sys


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
