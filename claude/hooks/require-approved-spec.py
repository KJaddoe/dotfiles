#!/usr/bin/env python3
"""PreToolUse(Write|Edit|NotebookEdit|Bash) gate: issue work needs an approved spec and plan.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Working method):
issue work runs spec, user review, plan, user review, then code. The rule alone did not hold.
Work on an issue went from reading code straight to editing it, and the mistakes that followed
were sequencing ones a reviewed plan would have caught.

The gate applies on a branch named the way `gh issue develop` names one (`<number>-<slug>`).
Any other branch, and any path outside a git repository, passes. On an issue branch an edit
inside the repository is refused until the project's session folder
(`~/.claude/projects/<mapped>/specs/`) holds a Markdown document whose front matter reads
`issue: <number>`, `kind: spec`, `status: approved`, and another with `kind: plan`.

Only the user approves. A Write or Edit that would leave a document in a session `specs/` folder
reading `status: approved` is refused, so an approved document is frozen to Claude. When the user
asks to change one, Claude first sets it back to draft with an edit that touches only the status,
says so, and then revises it; approving it again stays the user's. That reopening is refused once
work on the issue has started: a branch for it has commits beyond the default branch, or is checked
out with uncommitted changes. Changing course then takes a new plan or undoing the work.

Under Bash the gate is a heuristic against drift, not a sandbox. It refuses redirects into the
repository, `tee`, in-place `sed`/`perl`, and a heredoc fed to an interpreter; a script written
to `/tmp` and then run is not caught. A `>` inside a quoted argument reads as a redirect and
fails closed.

Exit 2 + stderr blocks the tool call and feeds the reason back to the model. Deliberately
unconfigurable, with no bypass: an off-switch is the failure it exists to prevent.
"""

import re
import sys
from pathlib import Path

from _hookutil import (
    command_directory,
    command_segments,
    nearest_existing_dir,
    read_payload,
    read_text_or_empty,
    redirect_targets,
    repo_root,
    run_git,
    session_project_dir,
    strip_heredocs,
    strip_printed_text,
)

GATED_TOOLS = {"Write", "Edit", "NotebookEdit", "Bash"}

ISSUE_BRANCH = re.compile(r"^(\d+)-")

REQUIRED_KINDS = ("spec", "plan")

RULE_REFERENCE = "~/.claude/CLAUDE.md (Working Preferences -> Working method)"

INTERPRETER_HEREDOC = re.compile(r"\b(?:python3?|node|ruby|perl|sh|bash|zsh)\b[^\n;&|]*<<")

IN_PLACE_EDITORS = {"sed", "perl"}

IN_PLACE_FLAG = re.compile(r"^(?:--in-place|-[A-Za-z]*i)")

DISCARD_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr"}

APPROVED_LINE = re.compile(r"^status:\s*approved\s*$", re.IGNORECASE | re.MULTILINE)

APPROVED_WORD = re.compile(r"\bapproved\b", re.IGNORECASE)

SESSION_SPECS = re.compile(r"\.claude/projects/\S*specs")

DEFAULT_BRANCHES = ("origin/HEAD", "origin/main", "origin/master", "main", "master")

APPROVAL_REASON = (
    "BLOCKED by user policy: only the user marks a spec or plan approved. Leave it as "
    "`status: draft`, show it to the user and wait for them to change it. An approved document "
    "is frozen: when the user asks to change one before work on it has started, first Edit its "
    f"status line alone to `status: draft`, tell the user, then revise it. See {RULE_REFERENCE}."
)

REOPEN_REASON = (
    "BLOCKED by user policy: an approved spec or plan stays approved once work on its issue has "
    "started, and for issue {issue} {evidence}. Tell the user the change needs a new plan, or "
    f"the work undone first. See {RULE_REFERENCE}."
)


def front_matter(text):
    """Parse a document's leading `---` block into lowercased keys and values.

    :param text: the document
    :return: (fields, error); fields is None when there is no usable front matter, and error
        names what is malformed, or is None
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, None

    fields = {}
    for number, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return fields, None
        content = line.split("#", 1)[0].strip()
        if not content:
            continue
        key, separator, value = content.partition(":")
        if not separator or not key.strip():
            return None, f"line {number} is not `key: value`"
        fields[key.strip().lower()] = value.strip().lower()

    return None, "front matter is never closed with `---`"


def issue_documents(specs_dir, issue):
    """Sort one issue's documents by whether they are approved.

    :param specs_dir: the session specs folder
    :param issue: the issue number, as a string
    :return: (approved kinds, draft kinds, list of "name: problem" for unparseable documents)
    """
    approved, drafts, malformed = set(), set(), []
    if not specs_dir.is_dir():
        return approved, drafts, malformed

    for path in sorted(specs_dir.glob("*.md")):
        fields, error = front_matter(read_text_or_empty(path))
        if error:
            malformed.append(f"{path.name}: {error}")
            continue
        if not fields or fields.get("issue") != issue:
            continue
        kind = fields.get("kind")
        if kind not in REQUIRED_KINDS:
            continue
        (approved if fields.get("status") == "approved" else drafts).add(kind)

    return approved, drafts, malformed


def gaps(approved, drafts):
    """Name what stands between the issue and an unblocked edit.

    :param approved: kinds with an approved document
    :param drafts: kinds with only unapproved documents
    :return: list of gaps, empty when nothing is missing
    """
    return [
        f"{kind} not approved" if kind in drafts else f"no {kind}"
        for kind in REQUIRED_KINDS
        if kind not in approved
    ]


def resolve(path, cwd):
    """Resolve a possibly relative path against the session directory.

    :param path: file path
    :param cwd: the session's working directory
    :return: the absolute Path
    """
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and cwd:
        candidate = Path(cwd).expanduser() / candidate
    return candidate


def writes_opaquely(invoked):
    """Report whether a command writes files where its text does not say.

    :param invoked: the command with heredoc bodies and printed text stripped
    :return: True for tee, an in-place editor, or an interpreter fed a heredoc
    """
    if INTERPRETER_HEREDOC.search(invoked):
        return True
    for tokens in command_segments(invoked):
        if not tokens:
            continue
        name = Path(tokens[0]).name
        if name == "tee":
            return True
        if name in IN_PLACE_EDITORS and any(IN_PLACE_FLAG.match(token) for token in tokens[1:]):
            return True
    return False


def shell_write_dirs(command, cwd):
    """List the directories a shell command would write into.

    A redirect names its own target, relative to where the command runs after any `cd`. An
    in-place editor, tee or an interpreter writes wherever its arguments or script say, so the
    directory the command runs in answers for it.

    :param command: the shell command
    :param cwd: the session's working directory
    :return: existing directories the command writes into
    """
    invoked = strip_printed_text(strip_heredocs(command))
    runs_in = str(command_directory(invoked, cwd))
    dirs = [
        nearest_existing_dir(resolve(target, runs_in).parent)
        for target in redirect_targets(command)
        if target not in DISCARD_TARGETS
    ]
    if writes_opaquely(invoked):
        dirs.append(Path(runs_in))
    return dirs


def target_dirs(tool, tool_input, cwd):
    """List the directories a tool call would write into.

    :param tool: tool name
    :param tool_input: the tool's input payload
    :param cwd: the session's working directory
    :return: existing directories the write lands in, empty when it writes nothing
    """
    if tool == "Bash":
        return shell_write_dirs(tool_input.get("command") or "", cwd)
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path:
        return []
    return [nearest_existing_dir(resolve(path, cwd).parent)]


def gated_issue(directory):
    """Report the repository and issue when a directory sits on an issue branch.

    :param directory: an existing directory
    :return: (repository root, issue number) or None when the gate does not apply
    """
    root = repo_root(directory)
    if root is None:
        return None
    match = ISSUE_BRANCH.match(run_git(root, "branch", "--show-current").strip())
    return (root, match.group(1)) if match else None


def gate_reason(issue, specs_dir, missing, malformed):
    """Explain a refused edit and what unblocks it.

    :param issue: the issue number
    :param specs_dir: the folder that was searched
    :param missing: the gaps found
    :param malformed: unparseable documents in that folder
    :return: the message fed back to the model
    """
    lines = [
        f"BLOCKED by user policy: this branch is work on issue {issue}, and editing the "
        f"repository needs an approved spec AND an approved plan first ({'; '.join(missing)}).",
        f"Looked in {specs_dir} for Markdown whose front matter reads `issue: {issue}`, "
        "`kind: spec` or `kind: plan`, and `status: approved`.",
        "Write the missing document there with `status: draft`, show it to the user and wait: "
        f"only the user sets it to approved. See {RULE_REFERENCE}.",
    ]
    if malformed:
        lines.append("Unreadable front matter: " + "; ".join(malformed))
    return "\n".join(lines)


def block(reason):
    """Refuse the tool call with a reason for the model.

    :param reason: the message to feed back
    """
    print(reason, file=sys.stderr)
    sys.exit(2)


def in_session_specs(path):
    """Report whether a path sits in a session specs folder under `~/.claude/projects/`.

    :param path: absolute file path
    :return: True for a session spec or plan
    """
    projects = Path.home() / ".claude" / "projects"
    candidate = Path(path).expanduser()
    return candidate.is_relative_to(projects) and "specs" in candidate.parts


def self_approves(tool, tool_input, cwd):
    """Report whether a tool call would leave a session spec or plan approved.

    :param tool: tool name
    :param tool_input: the tool's input payload
    :param cwd: the session's working directory
    :return: True when the call must be refused
    """
    if tool == "Bash":
        command = tool_input.get("command") or ""
        return bool(
            SESSION_SPECS.search(command)
            and APPROVED_WORD.search(command)
            and shell_writes(command)
        )

    path = str(resolve(tool_input.get("file_path") or "", cwd))
    if not in_session_specs(path):
        return False

    if tool == "Write":
        result = tool_input.get("content") or ""
    elif tool == "Edit":
        existing = read_text_or_empty(path)
        old, new = tool_input.get("old_string") or "", tool_input.get("new_string") or ""
        count = -1 if tool_input.get("replace_all") else 1
        result = existing.replace(old, new, count)
    else:
        return False

    return bool(APPROVED_LINE.search(result))


def reopened_document(tool, tool_input, cwd):
    """Find the approved session spec or plan a tool call would set back to draft.

    Runs after `self_approves`, so any Write or Edit still touching an approved document leaves
    it a draft.

    :param tool: tool name
    :param tool_input: the tool's input payload
    :param cwd: the session's working directory
    :return: (path, issue number) or None when the call reopens nothing tied to an issue
    """
    if tool not in ("Write", "Edit"):
        return None
    path = resolve(tool_input.get("file_path") or "", cwd)
    if not in_session_specs(str(path)):
        return None
    existing = read_text_or_empty(path)
    if not APPROVED_LINE.search(existing):
        return None
    fields, _ = front_matter(existing)
    issue = (fields or {}).get("issue")
    return (path, issue) if issue else None


def work_started(path, issue, cwd):
    """Name the work already done on an issue, which keeps its approved documents frozen.

    :param path: the document being reopened
    :param issue: its issue number
    :param cwd: the session's working directory
    :return: what shows the work has started, or "" when nothing has
    """
    root = repo_root(nearest_existing_dir(Path(cwd or ".").expanduser()))
    if root is None or not path.is_relative_to(session_project_dir(root) / "specs"):
        return "this session runs outside the document's repository, so that cannot be ruled out"

    base = next(
        (ref for ref in DEFAULT_BRANCHES if run_git(root, "rev-parse", "--verify", "--quiet", ref)),
        "",
    )
    current = run_git(root, "branch", "--show-current").strip()
    pattern = f"refs/heads/{issue}-*"
    for branch in run_git(root, "for-each-ref", "--format=%(refname:short)", pattern).split():
        if not base:
            return f"branch {branch} exists and there is no default branch to compare it with"
        ahead = run_git(root, "rev-list", "--count", f"{base}..{branch}").strip()
        if ahead not in ("", "0"):
            return f"branch {branch} has {ahead} commit(s) beyond {base}"
        if branch == current and run_git(root, "status", "--porcelain").strip():
            return f"branch {branch} has uncommitted changes"
    return ""


def shell_writes(command):
    """Report whether a shell command writes a file by any form the gate recognises.

    :param command: the shell command
    :return: True when it redirects somewhere real or writes opaquely
    """
    real = [target for target in redirect_targets(command) if target not in DISCARD_TARGETS]
    return bool(real) or writes_opaquely(strip_printed_text(strip_heredocs(command)))


def main():
    """Refuse an edit on an issue branch that has no approved spec and plan."""
    data = read_payload()
    if data is None:
        sys.exit(0)

    tool = data.get("tool_name") or ""
    if tool not in GATED_TOOLS:
        sys.exit(0)

    tool_input = data.get("tool_input") or {}
    cwd = data.get("cwd") or ""
    if self_approves(tool, tool_input, cwd):
        block(APPROVAL_REASON)

    reopened = reopened_document(tool, tool_input, cwd)
    if reopened:
        evidence = work_started(*reopened, cwd)
        if evidence:
            block(REOPEN_REASON.format(issue=reopened[1], evidence=evidence))

    for directory in target_dirs(tool, tool_input, cwd):
        gated = gated_issue(directory)
        if gated is None:
            continue
        root, issue = gated
        specs_dir = session_project_dir(root) / "specs"
        approved, drafts, malformed = issue_documents(specs_dir, issue)
        missing = gaps(approved, drafts)
        if missing:
            block(gate_reason(issue, specs_dir, missing, malformed))

    sys.exit(0)


if __name__ == "__main__":
    main()
