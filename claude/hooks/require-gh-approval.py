#!/usr/bin/env python3
"""PreToolUse(Bash) gate: a `gh` command that writes to GitHub needs explicit approval.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Acting as the user):
a GitHub issue, PR, comment, review or release is PUBLIC and identity-attributed. Authorization
for the task is not authorization for the content, and unlike a local commit it cannot be quietly
amended away: colleagues are notified the moment it lands.

Classification is an ALLOWLIST, not a denylist of write verbs. `gh` gains subcommands regularly,
and a denylist fails open on every one of them; an allowlist fails closed, which is the right
direction for actions that speak as the user. Ambiguity fails closed for the same reason: when the
subcommand cannot be parsed out of the flags, the command is gated rather than assumed harmless.

`gh api` is classified by METHOD rather than by verb, because it is the bypass a verb list misses:

    gh api repos/OWNER/REPO/issues -f title=... -f body=...

creates a real issue with no write verb anywhere in it. `gh api` defaults to GET, but adding
`-f/--raw-field`, `-F/--field` or `--input` makes it a POST unless `--method GET` says otherwise.

Two carve-outs exist, both for steps ~/.claude/CLAUDE.md mandates at the START of issue work.
Gating a step the rules require every time would only teach the user to click through prompts.

`gh issue develop` publishes a branch name for an issue the user already decided to work on, and
notifies nobody. Assigning that issue to themselves is the same kind of bookkeeping, but it cannot
be carved out by verb: `gh issue edit` also rewrites titles and bodies, which IS publishing. So the
assignment carve-out is by FLAG (`only_reassigns_to_self` in `_hookutil`) and fails closed on any
flag it does not recognise. Assigning someone ELSE stays gated: that puts work in a colleague's
queue and notifies them, which is not mundane.

Mode handling matches the commit and push gates. See `approval_decision` in `_hookutil`: prompt
where a prompt renders, deny where it would be auto-approved, never allow.

Deliberately unconfigurable, with no env switch. An off-switch is the failure it exists to prevent.
"""

import shlex
import sys

from _hookutil import (
    approval_decision,
    clip_summary,
    emit_decision,
    gh_invocations,
    gh_subcommand,
    gh_writes_to_github,
    read_bash_payload,
    repo_root,
    run_git,
    strip_heredocs,
)


def target_repo(repo, tokens):
    """Resolve which repository the invocation would act on.

    :param repo: repository root path, or None when not inside one
    :param tokens: gh arguments, excluding `gh`
    :return: a description of the target
    """
    for index, token in enumerate(tokens):
        if token in ("-R", "--repo") and index + 1 < len(tokens):
            return tokens[index + 1]
        if token.startswith("--repo="):
            return token.split("=", 1)[1]

    if repo is None:
        return "unknown, not inside a git repository"

    origin = run_git(repo, "remote", "get-url", "origin").strip()
    return origin or "unknown, no origin remote"


def gh_summary(repo, invocations):
    """Summarise what the gh invocations would publish.

    :param repo: repository root path, or None when not inside one
    :param invocations: token lists of the writing gh invocations
    :return: human-readable summary
    """
    sections = []
    for tokens in invocations:
        command, verb = gh_subcommand(tokens)
        action = f"gh {command} {verb}".strip() or "gh (unrecognised subcommand)"
        sections.append(
            f"Action: {action}\n"
            f"Repo:   {target_repo(repo, tokens)}\n"
            f"Full:   gh {shlex.join(tokens)}"
        )
    return clip_summary("\n\n".join(sections))


def main():
    """Turn a writing gh invocation into an approval decision the user controls."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    code = strip_heredocs(cmd)
    writing = [tokens for tokens in gh_invocations(code) if gh_writes_to_github(tokens)]
    if not writing:
        sys.exit(0)

    summary = gh_summary(repo_root(data.get("cwd") or "."), writing)
    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "GitHub action", summary))
    sys.exit(0)


if __name__ == "__main__":
    main()
