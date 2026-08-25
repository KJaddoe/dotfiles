#!/usr/bin/env python3
"""PreToolUse(Bash) guard: block git commands that record Claude attribution or gpg-sign.

Enforces the binding rules in ~/.claude/CLAUDE.md ("Working Preferences"):
- no "Co-Authored-By: Claude" / "Generated with Claude Code" / 🤖 trailers
- never --gpg-sign / -S on the user's behalf
Exit 2 + stderr blocks the tool call and feeds the reason back to the model.

Scope is the git subcommands that record a message (commit, merge, tag, revert, cherry-pick,
am, rebase, notes, stash), not the substring "commit", so read-only history inspection
(`git log … | grep`, and prose like "commits ahead") is never blocked, while attribution can
no longer slip through `git merge -m` or `git tag -a -m`. The gpg check stays scoped to
`git commit`, which is what the rule names.

Which subcommand is being INVOKED is decided from the command with heredoc bodies stripped, so
writing a script or document that merely mentions one of them is not treated as running it. The
attribution scan itself still reads the ORIGINAL text, because a heredoc is a normal way to pass
a multi-line commit message, exactly where a trailer would hide.
"""

import re
import sys

from _hookutil import (
    COMMIT_SUBCOMMAND,
    GIT_FLAGS,
    read_bash_payload,
    short_flag,
    strip_heredocs,
)

WRITE_SUBCOMMAND = re.compile(
    rf"\bgit\b{GIT_FLAGS}\s+(commit|merge|tag|revert|cherry-pick|am|rebase|notes|stash)\b",
    re.IGNORECASE,
)


def writes_history(cmd):
    """Report whether a shell command invokes a git subcommand that records a message.

    Read-only subcommands (log, show, diff, …) are excluded so that inspecting history,
    including grepping it for attribution, is never blocked. Matching the subcommand
    rather than the bare substring "commit" also stops prose like "commits ahead" from
    tripping the guard.

    :param cmd: full shell command, possibly compound
    :return: True when a history-writing git subcommand is present
    """
    return bool(WRITE_SUBCOMMAND.search(cmd))


def main():
    """Block a git invocation that would record Claude attribution or gpg-sign a commit."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    low = cmd.lower()
    code = strip_heredocs(cmd)

    if not writes_history(code):
        sys.exit(0)

    attribution = [
        "co-authored-by: claude",
        "generated with claude code",
        "🤖",
        "noreply@anthropic.com",
    ]
    hit = next((p for p in attribution if p in low), None)

    # --gpg-sign, or -S in a short-flag cluster (-S, -Sm, -amS). Case-sensitive: -s is
    # --signoff, allowed. Scoped to `git commit`: the rule names commit/--amend, not
    # tag or merge signing.
    gpg = bool(COMMIT_SUBCOMMAND.search(code)) and (("--gpg-sign" in code) or short_flag(code, "S"))

    if hit or gpg:
        reasons = []
        if hit:
            reasons.append(f'Claude attribution ("{hit}")')
        if gpg:
            reasons.append("--gpg-sign / -S")
        msg = (
            "BLOCKED by user policy: a git command that records history must not include "
            + " or ".join(reasons)
            + ".\nSee ~/.claude/CLAUDE.md (Working Preferences): no Claude attribution "
            "trailers, and never gpg-sign on the user's behalf. Remove it and retry."
        )
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
