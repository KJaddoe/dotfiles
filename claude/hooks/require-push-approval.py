#!/usr/bin/env python3
"""PreToolUse(Bash) gate: publishing to a remote needs the user's explicit approval.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Acting as the user):
a push is a PUBLIC, identity-attributed action, so the user signs off on what is being published
before it leaves the machine. Unlike a commit, a push cannot be quietly amended away afterwards:
colleagues, CI and the branch's public history all see it immediately.

`push.autoSetupRemote = true` in this repo's git config makes the gap sharper: a bare `git push`
on a branch with no upstream silently CREATES that branch on the remote. Nothing about the
command line says "publish", which is exactly the shape of action that should not be automatic.

The prompt carries the branch, the resolved target, the commits that would be published, and a
loud warning when history is being rewritten (`--force`, `-f`, `--force-with-lease`).

Mode handling matches the commit gate. See `approval_decision` in `_hookutil`: prompt where a
prompt renders, deny where it would be auto-approved, never allow.

Deliberately unconfigurable, with no env switch. An off-switch is the failure it exists to prevent.
"""

import re
import sys

from _hookutil import (
    GIT_FLAGS,
    approval_decision,
    clip_summary,
    emit_decision,
    read_bash_payload,
    repo_root,
    run_git,
    short_flag,
    strip_heredocs,
)

PUSH_SUBCOMMAND = re.compile(rf"\bgit\b{GIT_FLAGS}\s+push\b", re.IGNORECASE)

FALLBACK_BASES = ("origin/main", "origin/master", "main", "master")

COMMIT_LIST_LIMIT = 30


def rewrites_history(cmd):
    """Report whether the push would overwrite what the remote already has.

    :param cmd: full shell command
    :return: True when a force variant is present
    """
    return "--force" in cmd or short_flag(cmd, "f")


def is_dry_run(cmd):
    """Report whether the push only reports what it would do.

    A dry run publishes nothing, so gating it would be friction with no protection.

    :param cmd: full shell command
    :return: True when --dry-run is present
    """
    return bool(re.search(r"(?<![\w-])--dry-run(?![\w-])", cmd))


def current_branch(repo):
    """Resolve the checked-out branch name.

    :param repo: repository root path
    :return: branch name, or "" when detached or unresolvable
    """
    branch = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    return "" if branch in ("", "HEAD") else branch


def publish_base(repo):
    """Find the ref the pushed commits should be compared against.

    The upstream is the honest baseline when one exists. A branch that has never been pushed has
    none, and that is the case worth showing most clearly, so fall back to the default branch,
    and report when even that cannot be resolved rather than listing the entire history.

    :param repo: repository root path
    :return: (ref, description) pair, with ref empty when nothing resolves
    """
    upstream = run_git(repo, "rev-parse", "--abbrev-ref", "@{upstream}").strip()
    if upstream:
        return upstream, f"already on {upstream}"

    for base in FALLBACK_BASES:
        if run_git(repo, "rev-parse", "--verify", "--quiet", base).strip():
            return base, f"not yet on any remote; compared against {base}"

    return "", "no upstream and no default branch to compare against"


def push_summary(repo, cmd):
    """Summarise what the push would publish.

    :param repo: repository root path, or None when not inside a repository
    :param cmd: full shell command
    :return: human-readable summary of what would leave the machine
    """
    if repo is None:
        return "Not inside a git repository, cannot show what would be pushed."

    branch = current_branch(repo) or "a detached HEAD"
    base, note = publish_base(repo)

    lines = [f"Branch: {branch} ({note})"]
    if rewrites_history(cmd):
        lines.append("FORCE PUSH: this overwrites history already on the remote.")

    if not base:
        lines.append("Commits: cannot be determined without a baseline.")
        return "\n".join(lines)

    commits = run_git(repo, "log", "--oneline", f"--max-count={COMMIT_LIST_LIMIT}", f"{base}..HEAD")
    commits = commits.rstrip()
    if commits:
        lines.append(f"Commits that would be published:\n{commits}")
    else:
        lines.append("Nothing new to publish: the remote is already up to date.")

    return clip_summary("\n".join(lines))


def main():
    """Turn a push invocation into an approval decision the user controls."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    code = strip_heredocs(cmd)
    if not PUSH_SUBCOMMAND.search(code) or is_dry_run(code):
        sys.exit(0)

    summary = push_summary(repo_root(data.get("cwd") or "."), code)
    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "push", summary))
    sys.exit(0)


if __name__ == "__main__":
    main()
