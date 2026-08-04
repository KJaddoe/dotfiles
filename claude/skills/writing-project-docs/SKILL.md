---
name: writing-project-docs
description: Use when a change touches behaviour, setup, commands, env vars or config keys, API contracts, the data model, architecture, or deploy/release steps; when a user-visible change needs a CHANGELOG entry or a release is being cut; when a project's docs are missing, thin, or absent entirely; or when checking a repo for stale, wrong, or drifted documentation.
---

# Writing Project Docs

## Overview

Docs earn trust only if they match the code. A doc that is wrong is worse than one that is
missing, because people act on it. Every claim you write or keep must be **verified against the
code**, and anything you cannot verify gets marked, not guessed.

The binding obligation (update docs in the same commit; removals delete docs; the coverage floor)
lives in `~/.claude/CLAUDE.md` → **Project documentation**. This skill is the *how*.

## Three Modes

| Mode | Trigger | Output |
|------|---------|--------|
| **Inline** | You're making a change that hits a doc trigger | Doc edits in the same commit as the code |
| **Audit** | "Are our docs stale?" / unfamiliar repo / pre-release | A findings table. **No writes.** |
| **Remediate** | Acting on an audit | Scoped commits, worst findings first |

Audit and remediate are separate on purpose — present findings before editing, so scope stays the
user's call.

## Coverage Floor

**Canonical list lives in `~/.claude/CLAUDE.md` → Project documentation** (universal core plus
per-archetype extras). Read it there — do not restate it here, or the two drift apart.

Layout: use what the project already has. Starting from nothing, copy
`~/.claude/templates/docs-pointer/`. That template is scoped **"why, not what"** — reference
material (setup, run, test, env, deploy) belongs in the README or its own `docs/` page, never
crammed into `architecture.md`.

## Audit Procedure

1. **Inventory** — `README*`, `docs/`, ADRs, per-package READMEs, `.env.example`, `CHANGELOG*`,
   `CLAUDE.md`, doc-site sources.
2. **Verify every claim against code.** This is the step that gets skipped; it's the whole value:

   | Claim | Check against |
   |-------|--------------|
   | Env vars | grep the code for env access (`process.env`, `IConfiguration`, `os.environ`, …), diff vs `.env.example` + docs — **both directions** |
   | Commands | `package.json` scripts, `Makefile`, `*.csproj`, CI workflow |
   | Tooling versions | `.nvmrc`, `.tool-versions`, `mise.toml`, `global.json`, `Dockerfile`, CI matrix |
   | API contracts | routes/controllers vs documented endpoints and shapes |
   | Structure | documented tree vs actual directories |
   | Deploy steps | CI/CD workflows, deploy scripts, infra manifests |
   | CHANGELOG | see below — audited for OMISSIONS, not correctness |

3. **Gap-check** against the coverage floor.
4. **Classify** — `WRONG` (contradicts code) → `STALE` (describes something removed) → `MISSING`
   (floor gap) → `THIN`. Report in that order; it's also the fix order.
5. **Report** file, line, finding, evidence. Then stop.

## Remediation

- Fix `WRONG` first — it's actively misleading. Then `STALE`, then `MISSING`.
- One commit per doc area; don't bundle a README rewrite with an ADR.
- Touch only what's wrong or missing. No mass rewrites of prose that is merely *unfashionable*.
- **Never invent unverifiable facts.** Deploy targets, credential locations, and who-to-ask are
  usually not derivable from the repo. Write `TODO(owner): …`, surface it in your report, and ask.

## Auditing a CHANGELOG

A changelog is the one doc you cannot check against current code — it records history for an
audience, so it never "drifts", it can only be **incomplete**. Audit for omissions instead:

```sh
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```

Every user-visible commit in that range should have an entry. Flag the ones that don't. Internal
refactors, test-only changes, and chores correctly have none — absence is a finding only when the
change was visible to a consumer.

Writing an entry: describe the change from the **consumer's** side (what they can now do, what
broke, what to migrate to), not the implementation. Breaking changes say what to change, not just
that something changed. Follow the project's existing format and headings.

Remediation caveat: reconstructing old entries from commit messages produces plausible fiction.
Backfill only what the commits genuinely support, and flag the rest for a human.

## Documenting Env Vars & Config

Every entry needs: name · purpose · required vs optional · default · safe example placeholder ·
**where the real value comes from** (vault item, cloud config, who to ask, or `generate with X`).

Record the **location, never the value**. No real secrets in docs, examples, or commit history.

## Anti-Patterns

| ❌ | ✅ |
|----|----|
| Documenting intended behaviour | Document what the code does *today* |
| Restating what code already says | Capture the *why* and what code can't show |
| Inventing deploy steps to fill a gap | `TODO(owner)` + ask |
| Real secret as the "example" value | Placeholder + where the real one lives |
| Backfilling every gap unasked | Fill what your change touches; report the rest |
| Deleting a feature, leaving its docs | Same commit removes both |

## Red Flags — Stop

- "I'll document it in a follow-up" → it won't happen; same commit.
- "This is probably how it deploys" → you're inventing. Verify or `TODO`.
- "The docs say X, close enough" → verify against code or delete the claim.
- "Just a small env var" → undocumented env vars are the #1 onboarding blocker.
