#!/usr/bin/env python3
"""PreToolUse(Bash) guard: block commands that record Claude attribution or gpg-sign.

Enforces the binding rules in ~/.claude/CLAUDE.md ("Working Preferences"):
- no "Co-Authored-By: Claude" / "Generated with Claude Code" / 🤖 trailers
- no session-link trailer, in either the "Claude-Session:" key or a bare claude.ai/code/session URL
- never --gpg-sign / -S on the user's behalf
Exit 2 + stderr blocks the tool call and feeds the reason back to the model.

The session link is the harness's own default, not something the model chooses, so it reappears
every session no matter what the model was told last time. That is exactly the kind of rule a hook
has to carry rather than a prompt.

Scope is both halves of the rule's "commits, PR/issue bodies": git subcommands that record a
message, and `gh` invocations that write to GitHub (classified by `gh_writes_to_github`, so a
read like `gh issue list` is never scanned). A body passed by FILE (`gh pr create -F body.md`)
is out of reach here, since the text never appears in the command; the rule text still covers it.

On the git side that means the subcommands recording a message (commit, merge, tag, revert,
cherry-pick, am, rebase, notes, stash), not the substring "commit", so read-only history
inspection (`git log … | grep`, and prose like "commits ahead") is never blocked, while
attribution can no longer slip through `git merge -m` or `git tag -a -m`. The gpg check stays
scoped to `git commit`, which is what the rule names.

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
    gh_invocations,
    gh_writes_to_github,
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


def publishes_to_github(cmd):
    """Report whether a shell command contains a gh invocation that writes to GitHub.

    An issue or PR body is the other place the rule names, and it never passes through git.
    Reads are excluded so that inspecting GitHub, including searching it for attribution,
    is never blocked.

    :param cmd: full shell command, heredoc bodies already stripped
    :return: True when a writing gh invocation is present
    """
    return any(gh_writes_to_github(tokens) for tokens in gh_invocations(cmd))


def main():
    """Block an invocation that would record Claude attribution or gpg-sign a commit."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    low = cmd.lower()
    code = strip_heredocs(cmd)

    if not (writes_history(code) or publishes_to_github(code)):
        sys.exit(0)

    attribution = [
        "co-authored-by: claude",
        "generated with claude code",
        "🤖",
        "noreply@anthropic.com",
        "claude-session:",
        "claude.ai/code/session",
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
            "BLOCKED by user policy: a command that records or publishes text under the "
            "user's name must not include "
            + " or ".join(reasons)
            + ".\nSee ~/.claude/CLAUDE.md (Working Preferences): no Claude attribution "
            "trailers, and never gpg-sign on the user's behalf. Remove it and retry."
        )
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
