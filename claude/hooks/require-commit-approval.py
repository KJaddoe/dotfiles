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

Because this runs BEFORE the command, the index it reads predates any staging chained onto the
same line, so `git add X && git commit` once summarised whatever happened to be staged a moment
earlier. A `git add` ahead of the commit is therefore resolved through `git add --dry-run`, which
is git's own answer to what it would stage and leaves the index untouched. Staging that cannot
be read that way is NAMED in the prompt rather than passed over, because a summary that quietly
omits part of the change is the failure this gate exists to prevent.

Permission mode decides how that is delivered, because "ask" is only honoured where a prompt can
actually render:

- `default` / `plan`: permissionDecision "ask", and the prompt carries the summary.
- anything else (`auto`, `acceptEdits`, `dontAsk`, `bypassPermissions`): the prompt would be
  auto-approved, so the call is DENIED instead, with instructions to get approval in the
  conversation and re-run from `default`. Silently allowing is the one outcome the rule forbids.

`bypassPermissions` ignores hook decisions outright; nothing this file does can gate that mode.

Deliberately unconfigurable, with no env switch. An off-switch is the failure it exists to prevent.
"""

import shlex
import sys

from _hookutil import (
    COMMIT_SUBCOMMAND,
    approval_decision,
    clip_summary,
    command_directory,
    command_segments,
    emit_decision,
    read_bash_payload,
    repo_root,
    run_git,
    short_flag,
    strip_heredocs,
)

# git subcommands that change what a commit would record.
INDEX_VERBS = {"add", "rm", "mv", "restore", "reset", "stash", "apply"}

# Global flags that carry their value as a separate token, so the value is not the subcommand.
GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

# Flags that make an add a conversation rather than a fixed set of paths, which `--dry-run`
# cannot answer for.
INTERACTIVE_FLAGS = {"-i", "--interactive", "-p", "--patch", "-e", "--edit"}


def git_verb(tokens):
    """Locate the subcommand in a git invocation.

    :param tokens: one command's tokens, starting with `git`
    :return: (subcommand, its index in `tokens`), or ("", -1) when the invocation names none
    """
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in GIT_VALUE_FLAGS:
            index += 2
        elif token.startswith("-"):
            index += 1
        else:
            return token, index
    return "", -1


def staging_ahead(cmd):
    """Return the git invocations that would change the index before the commit runs.

    :param cmd: full shell command, heredoc bodies already stripped
    :return: list of token lists, one per staging invocation preceding the commit
    """
    ahead = []
    for tokens in command_segments(cmd):
        if tokens[0] != "git":
            continue
        verb, _ = git_verb(tokens)
        if verb == "commit":
            break
        if verb in INDEX_VERBS:
            ahead.append(tokens)
    return ahead


def would_stage(repo, tokens):
    """Ask git what an add would stage, without staging it.

    `--dry-run` goes directly after the subcommand, so a `--` later in the invocation cannot
    swallow it as a pathspec.

    :param repo: repository root path
    :param tokens: the add invocation's tokens, starting with `git`
    :return: git's report of what it would stage, empty when it would stage nothing or fails
    """
    _, index = git_verb(tokens)
    args = [*tokens[1 : index + 1], "--dry-run", *tokens[index + 1 :]]
    return run_git(repo, *args).rstrip()


def chained_staging_sections(repo, cmd):
    """Describe the staging that happens between this summary and the commit.

    An add reporting nothing contributes no section: either it stages nothing, or it fails and
    `&&` stops the commit ever running. Either way the staged tree below is the whole story.

    :param repo: repository root path
    :param cmd: full shell command, heredoc bodies already stripped
    :return: list of summary sections, empty when nothing stages ahead of the commit
    """
    sections, unreadable = [], []
    for tokens in staging_ahead(cmd):
        verb, _ = git_verb(tokens)
        if verb == "add" and not INTERACTIVE_FLAGS.intersection(tokens):
            report = would_stage(repo, tokens)
            if report:
                sections.append(f"Staged first by `{shlex.join(tokens)}`:\n{report}")
            continue
        unreadable.append(shlex.join(tokens))

    if unreadable:
        sections.append(
            "Also runs before the commit and changes what it records, beyond what this "
            "summary can read:\n" + "\n".join(unreadable)
        )
    return sections


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

    sections.extend(chained_staging_sections(repo, cmd))

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

    where = command_directory(code, data.get("cwd") or ".")
    summary = pending_summary(repo_root(where), code)
    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "commit", summary))
    sys.exit(0)


if __name__ == "__main__":
    main()
