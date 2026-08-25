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

`gh issue develop` is deliberately allowed: it publishes only a branch name for an issue the user
already decided to work on, notifies nobody, and ~/.claude/CLAUDE.md mandates it for every tracked
issue. Gating a step the rules require on every issue would only teach the user to ignore prompts.

Mode handling matches the commit and push gates. See `approval_decision` in `_hookutil`: prompt
where a prompt renders, deny where it would be auto-approved, never allow.

Deliberately unconfigurable, with no env switch. An off-switch is the failure it exists to prevent.
"""

import re
import shlex
import sys

from _hookutil import (
    approval_decision,
    clip_summary,
    emit_decision,
    read_bash_payload,
    repo_root,
    run_git,
    strip_heredocs,
)

SEPARATORS = re.compile(r"&&|\|\||;|\||\n")

# Every top-level `gh` command, so the subcommand can be located without guessing which tokens
# are flag values. A command absent from this set is unrecognised and therefore gated.
TOP_LEVEL = {
    "alias",
    "api",
    "attestation",
    "auth",
    "browse",
    "cache",
    "codespace",
    "completion",
    "config",
    "extension",
    "gist",
    "gpg-key",
    "issue",
    "label",
    "org",
    "pr",
    "project",
    "release",
    "repo",
    "ruleset",
    "run",
    "search",
    "secret",
    "ssh-key",
    "status",
    "variable",
    "workflow",
}

# Top-level commands that only ever read.
READ_ONLY_COMMANDS = {"browse", "completion", "search", "status"}

# Verbs that only read, whichever group they belong to. `clone` and `checkout` write locally
# but publish nothing. `gh project` spells its read verbs with a hyphen, and every other
# hyphenated project verb (item-create, field-delete, …) writes.
READ_ONLY_VERBS = {
    "checkout",
    "checks",
    "clone",
    "diff",
    "download",
    "field-list",
    "item-list",
    "list",
    "status",
    "view",
    "watch",
}

# `gh issue develop` publishes a branch name and nothing else. See the module docstring.
ALLOWED_PAIRS = {("issue", "develop")}

API_PAYLOAD_FLAGS = {"-f", "--raw-field", "-F", "--field", "--input"}

METHOD_FLAGS = {"-X", "--method"}


def gh_invocations(cmd):
    """Split a shell command into the argument list of each `gh` invocation it contains.

    :param cmd: full shell command, heredoc bodies already stripped
    :return: list of token lists, one per gh invocation, each excluding the `gh` itself
    """
    found = []
    for chunk in SEPARATORS.split(cmd):
        try:
            tokens = shlex.split(chunk)
        except ValueError:
            tokens = chunk.split()
        for index, token in enumerate(tokens):
            if token == "gh":
                found.append(tokens[index + 1 :])
                break
    return found


def subcommand(tokens):
    """Resolve the (command, verb) pair a gh invocation targets.

    The command is matched against the known top-level set rather than taken positionally, so a
    global flag and its value (`gh --repo X pr view`) cannot be mistaken for the subcommand.

    :param tokens: gh arguments, excluding `gh`
    :return: (command, verb) with either element empty when it cannot be resolved
    """
    command = next((token for token in tokens if token in TOP_LEVEL), "")
    if not command:
        return "", ""

    rest = tokens[tokens.index(command) + 1 :]
    verb = next((token for token in rest if not token.startswith("-")), "")
    return command, verb


def api_writes(tokens):
    """Report whether a `gh api` invocation sends anything other than a GET.

    :param tokens: gh arguments, excluding `gh`
    :return: True when the request would write
    """
    for index, token in enumerate(tokens):
        if token in METHOD_FLAGS and index + 1 < len(tokens):
            return tokens[index + 1].upper() != "GET"
        if token.startswith("--method="):
            return token.split("=", 1)[1].upper() != "GET"

    return any(token.split("=", 1)[0] in API_PAYLOAD_FLAGS for token in tokens)


def writes_to_github(tokens):
    """Report whether a gh invocation would change anything on GitHub.

    :param tokens: gh arguments, excluding `gh`
    :return: True when the invocation writes
    """
    if not tokens:
        return False

    command, verb = subcommand(tokens)
    if not command:
        return True

    if command == "api":
        return api_writes(tokens)

    if (command, verb) in ALLOWED_PAIRS:
        return False

    if command in READ_ONLY_COMMANDS:
        return False

    return verb not in READ_ONLY_VERBS


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
        command, verb = subcommand(tokens)
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
    writing = [tokens for tokens in gh_invocations(code) if writes_to_github(tokens)]
    if not writing:
        sys.exit(0)

    summary = gh_summary(repo_root(data.get("cwd") or "."), writing)
    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "GitHub action", summary))
    sys.exit(0)


if __name__ == "__main__":
    main()
