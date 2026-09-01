#!/usr/bin/env python3
"""PreToolUse(Artifact) guard: never publish an artifact, build it as a local file instead.

Enforces the user's standing preference that generated pages (plans, designs, reports) are
written to disk and reviewed there, never pushed to claude.ai as a hosted page. Publishing
distributes the content and mints a shareable URL; the user decides if and when that happens,
so the model does not get to make that call on their behalf.

Where a local file belongs is already settled by ~/.claude/CLAUDE.md: generated planning
artifacts go to the untracked session dir `~/.claude/projects/<mapped-path>/specs/`, and
project docs are a repo deliverable. When neither fits, the model asks rather than guessing.

The tool is not blocked wholesale. Reading an artifact the user was shared, listing what
exists, and managing watches all stay available, because none of them send local content
anywhere. What is blocked is the set of actions that push bytes from this machine to the
hosted service:

    publish        creates or updates a hosted page (this is also the action when `action`
                   is omitted entirely, which is the common call shape)
    upload_asset   pushes a local image, video, PDF, font or text file into a hosted page

An action this guard does not recognise is blocked too. New actions get added to the tool
over time, and one that publishes would otherwise sail through until someone noticed. Failing
closed costs a one-line allowlist edit; failing open costs a page the user never agreed to.

Exit 2 + stderr blocks the tool call and feeds the reason back to the model.
"""

import sys

from _hookutil import read_payload

# Actions that neither create a hosted page nor send local content to one. Everything else is
# blocked, including an absent action (which means publish) and anything not listed here.
READ_ONLY_ACTIONS = {
    "comments",
    "list",
    "list_assets",
    "read",
    "read_asset",
    "status",
    "unwatch",
    "watch",
}

# Blocked actions this guard can name precisely in its message. Anything else that is not in
# READ_ONLY_ACTIONS is still blocked, just described generically.
PUBLISHING_ACTIONS = {
    "publish": "create or update a hosted page on claude.ai",
    "upload_asset": "push a local file into a hosted artifact",
}

WHERE_TO_WRITE = (
    "Write the page to a local .html file instead and hand the user the path:\n"
    "  - generated plans, specs and design docs -> "
    "~/.claude/projects/<mapped-path>/specs/\n"
    "  - project documentation -> the repo's own docs location (it is a committed deliverable)\n"
    "  - throwaway scratch -> the session scratchpad\n"
    "If none of those fit, ask the user where to put it rather than guessing."
)


def requested_action(data):
    """Resolve the Artifact action a tool call is asking for.

    An omitted `action` means publish, which is the shape most publish calls take, so the
    default here has to be the blocked one rather than a harmless placeholder.

    :param data: the PreToolUse payload
    :return: the action name, defaulting to "publish" when absent or blank
    """
    tool_input = data.get("tool_input") or {}
    return (tool_input.get("action") or "publish").strip()


def describe(action):
    """Describe what a blocked action would have done, for the message shown to the model.

    :param action: the resolved action name
    :return: a phrase naming the effect, or a generic one for an unrecognised action
    """
    known = PUBLISHING_ACTIONS.get(action)
    if known:
        return known

    return (
        f"run the unrecognised Artifact action '{action}', which this guard cannot confirm "
        "keeps content local"
    )


def main():
    """Block any Artifact action that would publish local content to claude.ai."""
    data = read_payload()
    if data is None or data.get("tool_name") != "Artifact":
        sys.exit(0)

    action = requested_action(data)
    if action in READ_ONLY_ACTIONS:
        sys.exit(0)

    print(
        f"BLOCKED by user policy: artifacts are never published. This call would "
        f"{describe(action)}.\n\n"
        f"{WHERE_TO_WRITE}\n\n"
        "Only the user publishes. Do not suggest another route to hosting it, and do not "
        "retry this call.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
