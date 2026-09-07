# ADR 0005: Let the gates ask wherever a hook's "ask" actually prompts

- Status: accepted
- Date: 2026-09-07
- Supersedes: ADR 0004 (the mode half; the choice of `auto` as `defaultMode` stands)

## Context

ADR 0004 set `permissions.defaultMode` to `auto` and kept every approval gate DENYING outside
`default` and `plan`. The reasoning was one sentence: in a mode that auto-approves prompts, an
"ask" is an "allow" wearing a disguise. That premise was never tested. ADR 0004 said so itself,
and left the verification as the precondition for revisiting the decision.

The premise is false. A throwaway PreToolUse hook was registered that returned `"ask"` for a
single marker command and appended the `permission_mode` it was handed to a log, so that "the hook
fired and the ask was auto-approved" could be told apart from "the hook never ran", which are
otherwise indistinguishable from outside.

| Mode                | Result                          | How it was established                           |
|---------------------|---------------------------------|--------------------------------------------------|
| `default`, `plan`   | prompts                         | already relied on                                |
| `auto`              | prompts                         | dialog rendered, log recorded `mode=auto`        |
| `acceptEdits`       | prompts                         | dialog rendered, log recorded `mode=acceptEdits` |
| `dontAsk`           | unmeasured                      | not probed, see below                            |
| `bypassPermissions` | hook decisions ignored outright | documented behaviour; no hook reaches it         |

Both dialogs carried the hook's own `permissionDecisionReason`, so the summary a gate builds does
reach the user. The prompt was available in `auto` all along.

`dontAsk` was left unmeasured on purpose. It cannot be reached from the interactive mode cycle,
only by launching a session with `claude --permission-mode dontAsk`, and nothing here runs in it.
Leaving it in the deny branch is wrong only in the safe direction.

## Decision

`PROMPTING_MODES` in `_hookutil.py` gains `auto` and `acceptEdits`, so all four gates ask in the
modes where asking is measured to put a dialog in front of the user. `dontAsk` and
`bypassPermissions` keep denying. An unknown mode denies, so a mode added upstream fails closed.
Allowing remains not a legal outcome of any gate, in any mode.

What ADR 0004 called the review checkpoint moves from the mode switch to the prompt itself. The
prompt is the thing that was ever doing the reviewing; the switch was a consequence of a mistaken
belief about where prompts render.

Rejected:

- **Keeping deny everywhere.** Its only argument was the premise now measured false. Retaining it
  would charge a mode switch for every commit in exchange for nothing.
- **Treating every mode as prompting.** Simplest code, but it asserts something about `dontAsk`
  that nothing has measured, and `bypassPermissions` ignores hook output regardless.
- **Probing `dontAsk` first.** It needs a separate session launched with a CLI flag, and no work
  here runs in that mode. Recorded as unmeasured instead, which is cheap to correct later.

## Consequences

- Committing, pushing, publishing to GitHub and running a destructive command no longer require a
  mode switch. They raise a prompt carrying the summary, and the user approves or rejects in place.
- The gates' denial text no longer claims that a prompt "would be auto-approved" in the mode it
  names, because for the two remaining modes that is not why they deny.
- A pending prompt does not lapse into approval. One was left unanswered for about three minutes
  and was still waiting, so an unattended interactive session blocks rather than proceeds.
- What a hook's `"ask"` does in a session with nowhere to render a dialog (print mode, background,
  a subagent) is unmeasured. The safe assumption is that it fails closed, but it is an assumption,
  and a session that runs unattended should not be assumed to be gated by a prompt.
- ADR 0004's consequence that "sessions ending in a commit have one extra step" no longer holds.
  Its other consequences, including why the destructive gate had to exist before `auto` was safe,
  are unaffected.
