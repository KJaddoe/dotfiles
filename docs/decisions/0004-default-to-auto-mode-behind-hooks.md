# ADR 0004: Default to auto permission mode, with the gates denying rather than asking

- Status: accepted
- Date: 2026-08-27

## Context

`permissions.defaultMode` was `default`, so every Bash call raised a permission prompt unless it
matched one of five allowlist entries. In practice that meant approving `git log`, `git diff` and
`gh issue list` many times a session. The stated preference is narrower than the prompt is: reading
and searching should be automatic, and only things other people can see should need a look first.

`default` mode cannot express that. It gates by tool, not by consequence, so it charges the same
prompt for `git diff` as for `git push`.

Four PreToolUse gates already existed for the consequential actions: attribution, commit, push and
`gh` writes. But `approval_decision` in `_hookutil.py` treats only `default` and `plan` as modes
where a prompt renders. In every other mode it returns **deny**, on the reasoning that an "ask"
which gets auto-approved is an "allow" wearing a disguise.

That left one real hole. `CLAUDE.md` requires explicit confirmation before a destructive or
hard-to-reverse operation, and nothing enforced it: the permission prompt was doing that job
silently. Switching to `auto` would have removed the prompt and replaced it with nothing, so
`rm -rf` would have run unattended while `git commit` was blocked. The protection was inverted.

## Decision

Set `permissions.defaultMode` to `auto` in `claude/settings.json`, and first add
`claude/hooks/require-destructive-approval.py` to cover the surface the prompt had been covering
by accident.

Keep the deny-in-non-prompting-mode behaviour exactly as it is. In `auto`, a commit, a push, a
`gh` write or a destructive command fails with an explanation naming what it wanted to do, and
proceeding means switching to `default`. That switch is the review checkpoint. It is the feature,
not a cost to engineer away.

`claude/settings.json` is symlinked to `~/.claude/settings.json`, so it is user settings. This
matters: a project-level `.claude/settings.json` cannot grant `auto` at all, and Claude Code
ignores the value if one tries.

The destructive gate is a DENYLIST, unlike `require-gh-approval.py`, which is an allowlist and
says so loudly. There is no enumerable set of safe shell commands to allowlist against. It is
therefore a safety net over the known-destructive set, not a boundary, and it errs toward gating:
a false positive costs one approval, a false negative costs work git cannot recover.

Rejected:

- **Widening `permissions.allow` and staying in `default`.** Fixes the symptom for the reads
  someone thought to list, and leaves every unanticipated read prompting. It also grows a list
  that has to be maintained forever.
- **`acceptEdits` instead of `auto`.** It auto-accepts edits while Bash still prompts, which looks
  like the targeted fix. But `approval_decision` already treats `acceptEdits` as non-prompting, so
  the gates deny there too, and the mode's advantage disappears. Revisiting it means first
  verifying whether a Bash-tool "ask" is genuinely auto-approved under `acceptEdits`; that premise
  is currently asserted in `docs/configuration.md` and has not been tested.
- **Making the gates ask instead of deny in `auto`.** This is the one that will get re-proposed,
  because the denial is mildly annoying. It reintroduces exactly the failure the deny exists to
  prevent: in a mode that auto-approves prompts, an "ask" is an "allow".
- **`bypassPermissions`.** Ignores hook decisions entirely, so every gate in this repo stops
  existing.

## Consequences

- Reads, searches and local file edits no longer prompt. This is most of the friction, gone.
- Committing, pushing and publishing to GitHub now require a deliberate mode switch. Sessions that
  end in a commit have one extra step, and it lands at the moment the diff should be read anyway.
- Any rule that relied on a permission prompt rather than a hook has stopped holding. The
  destructive gate closes the case that was known; if another turns up, the fix is another hook,
  not reverting the mode.
- Local file edits land unreviewed between commits. `CLAUDE.md` already exempts local edits from
  the sign-off rule, so this is consistent, but the commit diff is now the first time edits get
  looked at as a set.
- The denylist will need occasional extension as new tooling arrives. `docs/configuration.md`
  lists what it covers today.
