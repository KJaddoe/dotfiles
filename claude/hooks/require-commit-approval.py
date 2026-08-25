#!/usr/bin/env python3
"""PreToolUse(Bash) gate: a commit needs the user's explicit approval of the change first.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Git & GitHub): the
user sees what is about to be committed and approves it BEFORE the commit is made. A commit
carries the user's name into branches colleagues review, so "it is only local" is not a reason
to skip sign-off — a change that has to be rewritten later costs the reviewer, not the author.

Every commit invocation is intercepted, amends included — decided from the command with heredoc
bodies stripped, so writing a script that merely mentions committing does not raise a prompt.
What is about to land goes INTO the approval prompt (`--stat` of the staged tree, plus the
tracked-but-unstaged changes that `-a` would sweep in). The user approves a change, not a
command line.

Permission mode decides how that is delivered, because "ask" is only honoured where a prompt can
actually render:

- `default` / `plan`: permissionDecision "ask" — the prompt carries the summary.
- anything else (`auto`, `acceptEdits`, `dontAsk`, `bypassPermissions`): the prompt would be
  auto-approved, so the call is DENIED instead, with instructions to get approval in the
  conversation and re-run from `default`. Silently allowing is the one outcome the rule forbids.

`bypassPermissions` ignores hook decisions outright; nothing this file does can gate that mode.

Deliberately unconfigurable — no env switch. An off-switch is the failure it exists to prevent.
"""

import json
import sys

from _hookutil import (
    COMMIT_SUBCOMMAND,
    read_bash_payload,
    repo_root,
    run_git,
    short_flag,
    strip_heredocs,
)

PROMPTING_MODES = {"default", "plan"}

SUMMARY_LINE_LIMIT = 40

RULE = "~/.claude/CLAUDE.md -> Working Preferences -> Git & GitHub"


def sweeps_tracked(cmd):
    """Report whether the invocation stages tracked changes on the user's behalf.

    `-a` / `--all` commit modified tracked files that were never staged, so the staged diff
    alone would understate what the commit contains.

    :param cmd: full shell command
    :return: True when tracked-but-unstaged changes would be included
    """
    return "--all" in cmd or short_flag(cmd, "a")


def clip(text):
    """Trim a diff summary to a length that stays readable inside a prompt.

    :param text: full summary text
    :return: the text, truncated with a count of the omitted lines
    """
    lines = text.splitlines()
    if len(lines) <= SUMMARY_LINE_LIMIT:
        return text
    hidden = len(lines) - SUMMARY_LINE_LIMIT
    return "\n".join(lines[:SUMMARY_LINE_LIMIT] + [f"... {hidden} more lines"])


def pending_summary(repo, cmd):
    """Summarise what the invocation would actually record.

    :param repo: repository root path, or None when not inside a repository
    :param cmd: full shell command
    :return: human-readable summary of the pending change
    """
    if repo is None:
        return "Not inside a git repository — cannot show what would be committed."

    sections = []
    staged = run_git(repo, "diff", "--cached", "--stat").rstrip()
    if staged:
        sections.append(f"Staged:\n{staged}")

    if sweeps_tracked(cmd):
        unstaged = run_git(repo, "diff", "--stat").rstrip()
        if unstaged:
            sections.append(f"Tracked but unstaged, swept in by -a:\n{unstaged}")

    if not sections:
        return "Nothing staged — git reports no pending changes."
    return clip("\n\n".join(sections))


def decide(mode, summary):
    """Build the permission decision for the session's mode.

    :param mode: the session's reported permission mode
    :param summary: summary of the pending change
    :return: (permissionDecision, permissionDecisionReason) pair
    """
    if mode in PROMPTING_MODES:
        reason = (
            f"This commit needs your explicit approval ({RULE}).\n\n{summary}\n\n"
            "Approve only if this is the change you reviewed."
        )
        return "ask", reason

    reason = (
        f"BLOCKED: permission mode is '{mode}', where an approval prompt is auto-approved, so "
        f"this commit cannot be put to the user ({RULE}).\n\n"
        f"{summary}\n\n"
        "Show this change to the user, get explicit approval in the conversation, and re-run "
        "the commit in 'default' permission mode."
    )
    return "deny", reason


def main():
    """Turn a commit invocation into an approval decision the user controls."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    code = strip_heredocs(cmd)
    if not COMMIT_SUBCOMMAND.search(code):
        sys.exit(0)

    summary = pending_summary(repo_root(data.get("cwd") or "."), code)
    decision, reason = decide(data.get("permission_mode") or "default", summary)

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
