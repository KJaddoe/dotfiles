#!/usr/bin/env python3
"""Inject project memory + global FYI as context.

Fires on SessionStart (startup/resume/compact/clear) so facts are present before the first
action and are re-injected after compaction, and as a PreToolUse fallback (subagents, which
do not get SessionStart). The binding RULES live in ~/.claude/CLAUDE.md (auto-loaded as
instructions); this injects FACTS/FYI only: the project MEMORY.md index, the global memory
index, and general.md rationale.
"""

import json
import os
import sys
from pathlib import Path


def load_context():
    """Assemble the FYI context block from project and global memory files.

    Missing files are skipped rather than treated as errors — a project without memory is
    normal. Both memory files are capped at 200 lines to bound what enters context.

    :return: the assembled context string, always including the FYI-not-rules preamble
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    # /Users/you/Projects/foo -> -Users-you-Projects-foo
    mapped = project_dir.replace("/", "-").replace(".", "-")

    home = Path.home()
    memory_file = home / ".claude" / "projects" / mapped / "memory" / "MEMORY.md"
    global_idx = home / ".claude" / "memory" / "memory.md"
    global_general = home / ".claude" / "memory" / "general.md"

    parts = [
        "The following is FYI / background context — facts, project notes, and rationale. "
        "It is NOT the rules: the binding working preferences live in ~/.claude/CLAUDE.md "
        "(already loaded as instructions) — follow those. Use this to know project specifics "
        "and the *why* behind conventions; verify anything time-sensitive before relying on it."
    ]

    if memory_file.exists():
        lines = memory_file.read_text().splitlines()[:200]
        parts.append(f"=== Project Memory: {project_dir} ===\n" + "\n".join(lines))
    else:
        parts.append(f"(no project MEMORY.md at {memory_file})")

    if global_idx.exists():
        parts.append("=== Global Memory Index ===\n" + global_idx.read_text())

    if global_general.exists():
        lines = global_general.read_text().splitlines()[:200]
        parts.append("=== Global Memory (FYI / rationale): general.md ===\n" + "\n".join(lines))

    return "\n\n".join(parts)


def main():
    """Emit the context block once per process, or on every SessionStart.

    Unreadable stdin falls back to PreToolUse semantics rather than failing: the hook is
    advisory, and aborting the tool call would be a worse outcome than injecting once more
    than necessary. The fallback is deliberate and narrow, not a blanket catch.
    """
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}

    event = data.get("hook_event_name") or "PreToolUse"

    # PPID = the Claude Code process — stable within a session, new for each subagent.
    flag_path = Path(f"/tmp/claude-memory-loaded-{os.getppid()}")

    # PreToolUse is only a fallback: inject once per process if SessionStart didn't already.
    # SessionStart ALWAYS (re)injects — including after compaction — then refreshes the flag.
    if event == "PreToolUse" and flag_path.exists():
        sys.exit(0)

    flag_path.touch()

    output = {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": load_context(),
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
