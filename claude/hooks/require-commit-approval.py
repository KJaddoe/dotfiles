#!/usr/bin/env python3
"""PreToolUse(Bash) gate: a commit needs the user's explicit approval of the change first.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Git & GitHub): the
user sees what is about to be committed and approves it BEFORE the commit is made. A commit
carries the user's name into branches colleagues review, so "it is only local" is not a reason
to skip sign-off. A change that has to be rewritten later costs the reviewer, not the author.

Every commit invocation is intercepted, amends included, decided from the command with heredoc
bodies stripped, so writing a script that merely mentions committing does not raise a prompt.
What is about to land goes INTO the approval prompt (`--stat` of the staged tree, plus the
tracked-but-unstaged changes that `-a` would sweep in). The user approves a change, not a
command line.

Permission mode decides how that is delivered, because "ask" is only honoured where a prompt can
actually render:

- `default` / `plan`: permissionDecision "ask", and the prompt carries the summary.
- anything else (`auto`, `acceptEdits`, `dontAsk`, `bypassPermissions`): the prompt would be
  auto-approved, so the call is DENIED instead, with instructions to get approval in the
  conversation and re-run from `default`. Silently allowing is the one outcome the rule forbids.

`bypassPermissions` ignores hook decisions outright; nothing this file does can gate that mode.

Deliberately unconfigurable, with no env switch. An off-switch is the failure it exists to prevent.
"""

import sys

from _hookutil import (
    COMMIT_SUBCOMMAND,
    approval_decision,
    clip_summary,
    emit_decision,
    read_bash_payload,
    repo_root,
    run_git,
    short_flag,
    strip_heredocs,
)


def sweeps_tracked(cmd):
    """Report whether the invocation stages tracked changes on the user's behalf.

    `-a` / `--all` commit modified tracked files that were never staged, so the staged diff
    alone would understate what the commit contains.

    :param cmd: full shell command
    :return: True when tracked-but-unstaged changes would be included
    """
    return "--all" in cmd or short_flag(cmd, "a")


def pending_summary(repo, cmd):
    """Summarise what the invocation would actually record.

    :param repo: repository root path, or None when not inside a repository
    :param cmd: full shell command
    :return: human-readable summary of the pending change
    """
    if repo is None:
        return "Not inside a git repository, cannot show what would be committed."

    sections = []
    staged = run_git(repo, "diff", "--cached", "--stat").rstrip()
    if staged:
        sections.append(f"Staged:\n{staged}")

    if sweeps_tracked(cmd):
        unstaged = run_git(repo, "diff", "--stat").rstrip()
        if unstaged:
            sections.append(f"Tracked but unstaged, swept in by -a:\n{unstaged}")

    if not sections:
        return "Nothing staged: git reports no pending changes."
    return clip_summary("\n\n".join(sections))


def main():
    """Turn a commit invocation into an approval decision the user controls."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    code = strip_heredocs(cmd)
    if not COMMIT_SUBCOMMAND.search(code):
        sys.exit(0)

    summary = pending_summary(repo_root(data.get("cwd") or "."), code)
    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "commit", summary))
    sys.exit(0)


if __name__ == "__main__":
    main()
