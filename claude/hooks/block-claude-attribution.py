#!/usr/bin/env python3
"""PreToolUse(Bash) guard: block git commits that carry Claude attribution or gpg-sign.

Enforces the binding rules in ~/.claude/CLAUDE.md ("Working Preferences"):
- no "Co-Authored-By: Claude" / "Generated with Claude Code" / 🤖 trailers
- never --gpg-sign / -S on the user's behalf
Exit 2 + stderr blocks the tool call and feeds the reason back to the model.
"""
import json
import re
import sys


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    cmd = (data.get("tool_input") or {}).get("command") or ""
    low = cmd.lower()

    # Only inspect git commit commands (handles compound commands like `cd x && git commit …`)
    if "commit" not in low or "git" not in low:
        sys.exit(0)

    attribution = [
        "co-authored-by: claude",
        "generated with claude code",
        "🤖",
        "noreply@anthropic.com",
    ]
    hit = next((p for p in attribution if p in low), None)

    # --gpg-sign, or -S in a short-flag cluster (-S, -Sm, -amS). Case-sensitive: -s is --signoff, allowed.
    gpg = ("--gpg-sign" in cmd) or bool(re.search(r"(?<![\w-])-[A-Za-z]*S[A-Za-z]*(?![\w-])", cmd))

    if hit or gpg:
        reasons = []
        if hit:
            reasons.append(f'Claude attribution ("{hit}")')
        if gpg:
            reasons.append("--gpg-sign / -S")
        msg = (
            "BLOCKED by user policy: git commit must not include "
            + " or ".join(reasons)
            + ".\nSee ~/.claude/CLAUDE.md (Working Preferences): no Claude attribution trailers, and "
            "never gpg-sign on the user's behalf. Remove it and retry."
        )
        print(msg, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
