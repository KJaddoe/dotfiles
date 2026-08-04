# ADR 0002: Enforce documentation rules with hooks, not prose alone

- Status: accepted
- Date: 2026-08-04

## Context

Documentation was being skipped — most often a new env var added with no record of what it should
be set to or where to obtain the value. The obvious fix was a new rule in `claude/CLAUDE.md`.

That fix had already failed. `CLAUDE.md` held ~40 binding rules, several about documentation, and
docs still got skipped. The failure mode is *forgetting*, not *not knowing* — and a rule is only
as reliable as the model's recall of a long file. Adding rule #41 addresses the wrong problem.

The repo already contained the counter-example: `block-claude-attribution.py`. The no-attribution
rule exists in `CLAUDE.md` **and** as a hook, because a rule that must never be violated cannot
depend on recall.

## Decision

Rules that describe a "whenever X" behaviour get a hook when the condition is mechanically
checkable. Prose states the obligation; the harness enforces it.

`claude/hooks/undocumented-env-vars.py` is a `Stop` hook: it scans lines *added* during the session
for env var reads (JS/TS, .NET, Python), checks each against `.env.example`, READMEs, `docs/**` and
`CLAUDE.md`, and reports any that appear nowhere. `DOCS_ENV_HOOK_MODE` selects `dry-run` (default),
`enforce`, or `off` — see `docs/configuration.md`.

Two constraints are non-negotiable:

- **Names only, never values.** The hook captures the variable name and never the matched line, so
  a secret sitting in the diff cannot reach the log. Regression tests assert this.
- **Narrow beats broad.** Only high-confidence accessor patterns are matched. A hook that will
  eventually block must not cry wolf.

Rejected: relying on prose alone (already demonstrably insufficient); a `PreToolUse` hook on edits
(fires mid-work, before docs would reasonably be written); broad shell/`$VAR` detection (`$HOME`,
`$PATH` make it unusable).

## Consequences

- The rule fires whether or not the model remembers it. Compliance stops being a recall problem.
- Dry-run default means new detection patterns can be observed before they block. This paid for
  itself immediately: the first run flagged the hook's own test fixtures, revealing that test
  paths must be excluded — a false-positive class that would have blocked on garbage in enforce mode.
- Coverage is deliberately partial. Shell vars, .NET `IConfiguration` indexers, and compose
  `environment:` blocks are not detected; those still rely on the prose rule.
- Only *added* lines count, so pre-existing undocumented vars never nag. Legacy debt needs the
  `writing-project-docs` audit mode instead.
- Hooks are now a maintained surface: they carry tests (`claude/hooks/tests/`) and a formatter
  config, which is more machinery than a rule in a file.
