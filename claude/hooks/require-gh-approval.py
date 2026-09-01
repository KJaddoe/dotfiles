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

`gh api graphql` is the one endpoint that rule cannot classify, and gating it was a false positive
rather than a safe default: GraphQL is always a POST and always carries its document in a field
flag, so every read looked like a write, and every project-board read (`projectV2` has no REST
endpoint) asked for approval. Reading GitHub has to stay friction-free or the gate gets switched
off, so a graphql call is classified by the OPERATION its document declares instead. That is not a
weaker test: an executable document's top level holds only operations and fragments, and the one
unlabelled form, the `{ ... }` shorthand, is a query by definition. Ambiguity fails closed here as
everywhere else: a document passed by file, or hidden behind a shell variable, cannot be read at
all, so it is gated.

`--help` is read whatever verb it names, because gh prints usage and exits without reaching the
API. Only the LONG form counts (`gh auth login -h` is `--hostname`, not help), and it must be the
FIRST flag-like token, so a `--help` bound as another flag's VALUE (`gh issue create -t --help`,
which titles a real issue `--help`) still gates.

The remaining carve-outs are all steps ~/.claude/CLAUDE.md mandates at the START of issue work: creating the
branch, assigning the issue, putting it on the board and setting its Status. Gating a step the
rules require every time would only teach the user to click through prompts.

`gh issue develop` publishes a branch name for an issue the user already decided to work on, and
notifies nobody; `gh project item-add` places an issue on a board, which notifies nobody either.
Both are carved out by verb, because nothing those verbs can do publishes prose.

Assigning an issue and setting a board field are the same kind of bookkeeping, but neither can be
carved out by verb: `gh issue edit` also rewrites titles and bodies, and `gh project item-edit`
also rewrites a DRAFT issue's title and body. Both are therefore carved out by FLAG
(`only_reassigns_to_self` and `only_edits_board_fields` in `_hookutil`), and both fail closed on
any flag they do not recognise. Assigning someone ELSE stays gated: that puts work in a
colleague's queue and notifies them, which is not mundane.

Board Status has no REST endpoint, so it is also set through `gh api graphql`. A mutation whose
root selection holds nothing but `updateProjectV2ItemFieldValue` / `clearProjectV2ItemFieldValue`
is the same bookkeeping and is carved out; every other mutation is gated. The test is the whole
root selection, not its first field, so a board mutation cannot smuggle a second one alongside it,
and an alias resolves to the field it names. A document declaring more than one operation, a
subscription, or root fields hidden behind a fragment spread all fail closed, because the
selection read would not be provably the one that writes.

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
