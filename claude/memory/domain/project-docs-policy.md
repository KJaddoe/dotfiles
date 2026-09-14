# Project documentation policy: history and ownership split

FYI/rationale file. Binding rule lives in `~/.claude/CLAUDE.md` -> Project documentation. All entries
below are from 2026-08-04 unless noted.

## Why the rule exists

Docs update in the SAME commit/PR as the change, never a later pass. Concrete misses that motivated
it: a new env var added without recording what the value should be or where to get it; project
structure/architecture undocumented; no deploy instructions. A purely reactive rule (fires only when
something changes) never catches what was never documented in the first place, hence the coverage
floor: what it is, setup/install + tooling versions, run, test, structure/architecture, config & env
vars, deploy/release, CHANGELOG for versioned projects, project `CLAUDE.md` on convention changes.
Filled in when work touches that area (report what's still missing), never backfilled wholesale
unasked. Removals delete the docs for the removed thing. Docs state what the code ACTUALLY does
(verified, not aspirational). Env vars need name/purpose/required/default/placeholder plus where the
real value lives: the LOCATION, never the value (ties to Confidentiality & secrets).

## Three-way ownership split (keep it strict or it drifts)

Docs knowledge is split across three places by design:

1. `CLAUDE.md` -> Project documentation: the always-on OBLIGATION (triggers, removals delete docs,
   coverage floor, verified-not-aspirational). Must stay in context or it never fires; a skill alone
   cannot fix a *forgetting* problem.
2. The `writing-project-docs` SKILL: the PROCEDURE (inline/audit/remediate modes, the
   claim-to-where-to-verify table, env-var doc fields, anti-patterns).
3. `claude/templates/docs-pointer/`: the STRUCTURE (root `CLAUDE.md` pointer + `docs/README.md`,
   `architecture.md`, `decisions/` ADRs, `erd.md` for DB projects).

Same shape as the `pending-pr-review` skill/rule split. The `docs-pointer` template is scoped "why,
not what": rationale and relations the code doesn't make obvious. It deliberately does NOT cover env
vars, deploy, setup/run/test, or API contracts; those are "what" and belong in the README or a
dedicated `docs/` page, not crammed into `architecture.md`. `claude/templates` was committed in
`d7e874a` but not linked into `~/.claude/` by dotbot until 2026-08-04.

## CHANGELOG is a different kind of doc

Every other doc describes CURRENT STATE (verifiable against code, fixable any time); a changelog is
an append-only record for an AUDIENCE. It can't be verified against code, never "drifts", and can
only be INCOMPLETE, so a missed entry is unrecoverable. Trigger is "does someone downstream need to
know" (feature, breaking change, deprecation, security fix), not "did code change": internal
refactors get no entry. Audit with `git log $(git describe --tags --abbrev=0)..HEAD --oneline` and
look for user-visible commits with no entry. Do not backfill from commit messages beyond what they
genuinely support, since that produces plausible fiction.

## Drift lesson (learned the hard way, same session)

After splitting docs knowledge across CLAUDE.md/skill/template, the coverage floor got restated in
BOTH the rule and the skill. One edit later they contradicted each other, and the "update the
project's own CLAUDE.md on convention change" clause was silently dropped from the rule while the
skill still asserted it. Fix: the skill now points at CLAUDE.md for the floor instead of restating
it. Rule of thumb: when the same fact lives in two files, it is already drifting; make one the owner
and have the other link.

## Enforcement

`claude/hooks/undocumented-env-vars.py` is a Stop hook that diffs the session's added lines for new
env var reads (JS/TS, .NET, Python) and blocks/reports any that appear in no doc. Modes via
`DOCS_ENV_HOOK_MODE`: `dry-run` (default, logs to `~/.claude/logs/env-doc-hook.log`), `enforce`,
`off`; documented in `docs/configuration.md`. A prose rule alone is a compliance problem, not a
discovery problem - same reasoning that produced `block-claude-attribution.py`. The hook captures
variable NAMES only, never the matched line, so secret VALUES in a diff can't leak into the log
(locked in by regression tests). Dry-running it against this repo caught a real false-positive class
(its own test fixtures), which is why test/fixture paths are excluded.

## Skill-writing lesson

`writing-project-docs` was written inline without the subagent pressure-testing
`superpowers:writing-skills` mandates, then tested and rewritten the same day (`6b7a0dc`): three
fresh agents applying it adversarially found six real defects, including the anti-pattern and the
coverage floor giving OPPOSITE answers on API/flags/exit codes, and an audit that runs commands to
verify itself clobbering HOME and the global git identity via `script/test`. An inline-written skill
reads fine to its author; only a fresh agent applying it surfaces the contradictions.
