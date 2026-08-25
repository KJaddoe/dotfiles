#!/usr/bin/env python3
"""Git helpers and command patterns shared by the hooks in this directory.

The hooks keep needing the same handful of things: run a git command without letting a failure
escape, resolve the repository root for the session's cwd, and recognise a commit invocation,
and its short flags, inside a shell command. Each was duplicated across hooks before this
module existed.

Importing this works because Python puts a script's OWN directory at the front of `sys.path`,
and the hooks are invoked as `python3 ~/.claude/hooks/<name>.py`, so `~/.claude/hooks` leads
the path regardless of the cwd git happens to be run from. Loading a hook by file path instead
(`importlib.util.spec_from_file_location`, as the tests do) does NOT do that, so a caller taking
that route has to put this directory on `sys.path` itself.

The leading underscore marks it as internal to the hooks directory: it is not a hook, and
`settings.json` never invokes it.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

GIT_TIMEOUT_SECONDS = 8

GIT_FLAGS = r"(?:\s+-{1,2}[\w-]+(?:[= ]\S+)?)*"

COMMIT_SUBCOMMAND = re.compile(rf"\bgit\b{GIT_FLAGS}\s+commit\b", re.IGNORECASE)

HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


PROMPTING_MODES = {"default", "plan"}

SUMMARY_LINE_LIMIT = 40

RULE_REFERENCE = "~/.claude/CLAUDE.md -> Working Preferences"


def clip_summary(text):
    """Trim a summary to a length that stays readable inside a permission prompt.

    :param text: full summary text
    :return: the text, truncated with a count of the omitted lines
    """
    lines = text.splitlines()
    if len(lines) <= SUMMARY_LINE_LIMIT:
        return text
    hidden = len(lines) - SUMMARY_LINE_LIMIT
    return "\n".join(lines[:SUMMARY_LINE_LIMIT] + [f"... {hidden} more lines"])


def approval_decision(mode, action, summary):
    """Build the PreToolUse decision that puts an action to the user for approval.

    "ask" is only honoured where a prompt can render. In the modes that auto-approve, asking
    would silently become allowing, precisely where the model runs unsupervised, so the action
    is denied instead, with instructions to get approval in the conversation and re-run from
    `default`. Allowing is never an outcome.

    :param mode: the session's reported permission mode
    :param action: what is being gated, named for the user ("commit", "push")
    :param summary: summary of what the action would do
    :return: (permissionDecision, permissionDecisionReason) pair
    """
    if mode in PROMPTING_MODES:
        return "ask", (
            f"This {action} needs your explicit approval ({RULE_REFERENCE}).\n\n{summary}\n\n"
            "Approve only if this is what you reviewed."
        )

    return "deny", (
        f"BLOCKED: permission mode is '{mode}', where an approval prompt is auto-approved, so "
        f"this {action} cannot be put to the user ({RULE_REFERENCE}).\n\n"
        f"{summary}\n\n"
        f"Show this to the user, get explicit approval in the conversation, and re-run the "
        f"{action} in 'default' permission mode."
    )


def emit_decision(decision, reason):
    """Print a PreToolUse decision in the shape the harness expects.

    :param decision: "ask", "deny" or "allow"
    :param reason: text shown to the user, or fed back to the model on a denial
    """
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


def read_payload():
    """Read a PreToolUse payload from stdin.

    A malformed payload is reported as absent rather than raised, so a guard can never take a
    tool call down with it.

    :return: the parsed payload, or None when stdin does not carry one
    """
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None


def read_bash_payload():
    """Read a PreToolUse payload from stdin, for the guards that only care about Bash.

    Every PreToolUse(Bash) guard opens the same way: parse stdin, ignore other tools, pull the
    command out.

    :return: (payload, command) for a Bash tool call, or (None, "") for anything else
    """
    data = read_payload()
    if data is None or data.get("tool_name") != "Bash":
        return None, ""

    return data, (data.get("tool_input") or {}).get("command") or ""


def strip_heredocs(cmd):
    """Return `cmd` with heredoc bodies removed, leaving the commands themselves.

    A heredoc body is data the shell feeds to a program (a script being written, a document,
    a payload), not something the shell executes. Matching command patterns against it is how a
    guard ends up blocking a script that merely *mentions* the thing it guards against.

    The delimiter lines are kept so the surrounding command text stays intact. Callers that care
    about the CONTENT of a command (a commit message passed on stdin, say) must scan the original
    string; this is for deciding what is being INVOKED.

    :param cmd: full shell command, possibly multi-line
    :return: the command with heredoc bodies elided
    """
    lines = cmd.split("\n")
    kept = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        match = HEREDOC_START.search(line)
        index += 1
        if not match:
            continue
        delimiter = match.group(2)
        while index < len(lines) and lines[index].strip() != delimiter:
            index += 1
        if index < len(lines):
            kept.append(lines[index])
            index += 1
    return "\n".join(kept)


def short_flag(cmd, letter):
    """Report whether `letter` is present as a short flag in `cmd`.

    Matches the bare flag and clustered forms (`-a`, `-am`, `-vam`) while ignoring long flags
    that merely contain the letter, so `--amend` does not read as `-a`. Matching is
    case-sensitive, keeping opposites like signing and sign-off distinct.

    :param cmd: full shell command
    :param letter: single flag letter to look for
    :return: True when the letter is present as a short flag
    """
    return bool(re.search(rf"(?<![\w-])-[A-Za-z]*{re.escape(letter)}[A-Za-z]*(?![\w-])", cmd))


def run_git(repo, *args):
    """Run a git command in `repo`, returning stdout or "" if git fails.

    :param repo: repository root path
    :param args: git arguments following the subcommand
    :return: decoded stdout, empty on any failure
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def repo_root(cwd):
    """Resolve the git repository root containing `cwd`.

    :param cwd: directory to resolve from
    :return: Path to the repo root, or None when not inside a git repo
    """
    top = run_git(cwd, "rev-parse", "--show-toplevel").strip()
    return Path(top) if top else None
