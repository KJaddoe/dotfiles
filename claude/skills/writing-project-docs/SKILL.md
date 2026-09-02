---
name: writing-project-docs
description: Use when a change touches behaviour, setup, commands, env vars or config keys, API contracts, the data model, architecture, or deploy/release steps; when a user-visible change needs a CHANGELOG entry or a release is being cut; when a project's docs are missing, thin, or absent entirely; or when checking a repo for stale, wrong, or drifted documentation.
---

# Writing Project Docs

A doc that is wrong is worse than one that is missing, because people act on it. Every claim you
write or keep must be verified against the code; anything you cannot verify gets marked, not guessed.

The binding obligation and the coverage floor live in `~/.claude/CLAUDE.md` → **Project
documentation**. If that section is not in your context, read it off disk before classifying
anything: `MISSING` is undefined without it.

## Interface vs implementation

The one question this skill exists to answer. Document the **interface**; never restate the
**implementation**.

| Document it                                                        | Don't                                               |
|--------------------------------------------------------------------|-----------------------------------------------------|
| Public API, request/response shapes, CLI flags, exit codes         | Internal control flow, algorithms, how a loop works |
| Env vars, config keys, defaults                                    | Line-by-line narration of a function                |
| Why a design was chosen, what it rules out, cross-component wiring | Anything a reader gets faster by opening the file   |

"Don't restate the code" means don't narrate internals. Contracts are the code's promise to a
consumer: they are required even though they are "what". Keep the two apart physically: reference
material in the README or its own `docs/` page, rationale in `architecture.md` / ADRs.

## Never cite an issue or ticket number

Not in a doc comment, a README, an ADR, a changelog entry, or any other artifact that lives in the
repository. The tracker and the repository have different lifetimes: issues get closed, renumbered,
migrated between trackers, and deleted outright. What is left behind is a pointer to nothing, which
leaves the reader worse off than if you had written no reference at all. Anyone who wants the
history has `git log` and `git blame`, which cannot rot.

Write the substance instead. It is almost always already there:

| Instead of                                              | Write                                                  |
|---------------------------------------------------------|--------------------------------------------------------|
| `Guards #NNN: adding to the cart used to decide ...`    | `Adding to the cart used to decide ...`                |
| `the exact shape that blocked checkout in #NNN`         | `the exact shape that blocked checkout`                |
| `Extracted for #NNN, where the same block was repeated` | `It was extracted because the same block was repeated` |
| `no version is pinned yet, see issue #NNN`              | `no version is pinned in the repository yet`           |

Removing the number costs nothing, because the sentence already carried the reason. If it does feel
load-bearing, the sentence was too thin to begin with: say what the behaviour is, what broke, and
why it must not come back. A regression test's doc comment earns its place by describing the
failure, not by naming the ticket that reported it.

The same goes for `Fixes #NNN` in a source comment. A number belongs only where the medium's own
lifetime matches it: a commit message, a pull request body, a branch name.

## Three modes

| Mode          | Trigger                                          | Output                                         |
|---------------|--------------------------------------------------|------------------------------------------------|
| **Inline**    | A change hits a doc trigger                      | Doc edits in the same commit as the code       |
| **Audit**     | "Are our docs stale?", pre-release, unknown repo | A findings table. **No writes**; step 3 only   |
| **Remediate** | Acting on an audit                               | One commit per doc area, worst class first     |

If a task is both (changing code in an unfamiliar repo), do Inline. Audit is a task in its own
right, not a prerequisite for unrelated work.

**Drift you notice mid-change:** fix it in the same commit when it is in the area you touched.
Outside that blast radius, report it: "never bundle unrelated changes" wins.

## Layout

Use what the project already has. Starting from nothing, follow the Apply steps in
`~/.claude/templates/docs-pointer/README.md`: do not copy the directory wholesale, or you ship
`CLAUDE.md.template`, the template's own README, and unreplaced `{Project Name}` placeholders.

A repo can be more than one archetype (a published CLI that is also a library). Union the rows.

## Audit procedure

1. **Inventory**: `README*`, `docs/`, ADRs, per-package READMEs, `.env.example`, `CHANGELOG*`,
   `CLAUDE.md` (its own section below), doc-site sources, CI configs that tell a human or machine
   how to build/run/test, and any doc template this repo ships to other repos (a defect there
   propagates).

2. **Verify claims against code.** The step that gets skipped; it is the whole value.

   | Claim            | Check against                                                                                |
   |------------------|----------------------------------------------------------------------------------------------|
   | Env vars         | env reads in source, both directions vs `.env.example` + docs - see exclusions below         |
   | Commands         | `package.json` scripts, `Makefile`, `*.csproj`, CI workflows - **read them, never run them** |
   | Tooling versions | `.nvmrc`, `.tool-versions`, `mise.toml`, `global.json`, `Dockerfile`, CI matrix              |
   | API contracts    | routes/controllers vs documented endpoints and shapes                                        |
   | Structure        | documented tree vs actual directories                                                        |
   | Deploy steps     | CI/CD workflows, deploy scripts, infra manifests                                             |

   **Never execute a documented command to test it.** Setup and test scripts overwrite home
   directories, rewrite global git config, and change login shells. Verify by reading the definition.

   Env var exclusions, or every audit drowns: skip platform vars (`PATH`, `HOME`, `NODE_ENV`, `CI`,
   …) and test/fixture paths, which legitimately contain invented names.

3. **Floor first, then scope.** The floor lives in `~/.claude/CLAUDE.md` while the classes live
   here, and a floor item in another file gets skipped: "how to roll back" was absent from three
   audited deployed services and went unreported in all three. So walk it mechanically before
   anything else:

   ```sh
   python3 ~/.claude/hooks/docs-coverage-floor.py --path .
   ```

   It prints the repo's detected kind(s) and every floor topic no doc mentions. **Each line it
   prints is a `MISSING` row** unless you can name the doc that covers it. Detection is coarse: a
   passing mention counts as covered, so it under-reports and is a floor, never a quality bar; a
   topic it passes can still be `THIN`. If it cannot run, walk the floor by hand instead.

   This is the one command an audit runs. It ships with the skill, only reads, and executes
   nothing belonging to the repo; step 2's ban is on running the **project's** commands.

   Then verify every claim in the coverage-floor docs. Sample elsewhere and **say what you
   sampled**: an unbounded "verify everything" over a large repo silently becomes partial anyway.

4. **Classify.**

   | Class      | Means                                                                     |
   |------------|---------------------------------------------------------------------------|
   | `WRONG`    | Doc contradicts the code today                                            |
   | `CONFLICT` | Doc and code disagree and a human must choose which one changes           |
   | `STALE`    | Doc was right; the code moved and it didn't (incl. lists that grew)       |
   | `MISSING`  | Coverage-floor gap (step 3), or undocumented behaviour that surprises     |
   | `THIN`     | Present but not enough to act on without reading the source               |

   `CONFLICT` is usually the most valuable finding: never silently "fix" the doc to match the code
   when the code may be what is wrong.

5. **Report**, one row each, then stop:

   | # | Class | Location (file:line) | Finding | Verified against |
   |---|-------|----------------------|---------|------------------|

   Also list what you checked and found correct: a bare complaint list doesn't show coverage.

## Remediation

Fix `WRONG` and `CONFLICT` first (raise `CONFLICT`, don't decide it), then `STALE`, then `MISSING`,
then `THIN`, but a severe item outranks a trivial one in a higher class. Deleting a doc for a
subsystem that no longer exists is a valid fix, not a cop-out.

**Never invent.** Deploy targets, credential locations and who-to-ask are rarely derivable from a
repo. Leave `TODO:` with what you need and who could answer if you know, surface it in your report,
and ask. Don't guess a plausible answer.

**Generated docs** (OpenAPI, typedoc, docfx): fix the source or regenerate. Hand-editing an
artifact the next build overwrites is worse than leaving it stale.

**Docs outside the repo** (Confluence, Notion, a separate docs site): "same commit" is impossible.
Make the change, and report what needs updating externally: never assume someone else will.

## Env vars & config

Field list is in `~/.claude/CLAUDE.md`. Two cases it doesn't cover:

- **Harness/platform-set vars** (set by the tooling, not the user): say so explicitly and skip
  "where the value comes from"; the answer is "you don't set this".
- **Local behaviour switches** with safe defaults, no provenance needed. Say that in one clause,
  not an apologetic paragraph.

Record the **location** of a real value, never the value.

## CLAUDE.md

A project `CLAUDE.md` is a rule **budget**, not a backlog. Audit it to shrink it: the healthy
outcome is rules deleted or sharpened, and an audit that only adds has failed.

**Identify the target first.** Only a `CLAUDE.md` that governs *this repo* is in scope. A repo can
also carry one it does not own:

| File                                 | Is                                  | Audit?                        |
|--------------------------------------|-------------------------------------|-------------------------------|
| Repo root / package root             | This project's rules                | Yes                           |
| Symlinked out to a tool's config dir | Someone's **global** rules; payload | No                            |
| `*.template` shipped to other repos  | A template                          | No - a defect there is step 1 |

Check the repo's linking manifest (`dotbot.conf.yaml` `link:` entries, a stow/chezmoi layout, an
install script) and whether the path is already a symlink. Editing a linked-out global file under a
project audit applies project-scoped tests to global rules.

**Never propose a new rule.** Origination is reserved to the user (`~/.claude/CLAUDE.md` → Working
method). An audit reports; it does not write rules. `MISSING` here means a convention the repo
demonstrably follows is undocumented: report it and stop.

Per rule, stopping at the first hit:

| Class         | Means                                                               |
|---------------|---------------------------------------------------------------------|
| `ENFORCEABLE` | A hook, linter/formatter config, test or CI check could enforce it  |
| `DUPLICATE`   | Another rule - here or global - already covers it; sharpen that one |
| `MISPLACED`   | A fact, rationale or history, not an imperative → memory            |

The five general classes still apply: a rule naming a command, tool or path that no longer exists is
`WRONG`; one whose convention moved is `STALE`; one too vague to act on is `THIN`. Report in the
step 5 table.

`ENFORCEABLE` is the most valuable finding and the one to hunt hardest: a rule is the weakest
enforcement available. It is not fixed by editing `CLAUDE.md`: it is a proposal to build the check,
raised one at a time, and the rule goes only once the check lands.

## CHANGELOG

A changelog records history for an audience, so it never drifts: it can only be incomplete, and a
missed entry is unrecoverable. One entry per **user-visible change**, not per commit; a feature
delivered in fourteen commits is one entry. Internal refactors get none.

In-flight entries accumulate under `Unreleased`, promoted and dated when a release is cut.

Auditing: **skip entirely if the project is changelog-exempt** (personal/infra, no consumers) or has
no releases. Otherwise compare entries against the range since the last release:
`git describe --tags --abbrev=0` gives the last tag, but **it errors when there are no tags**; fall
back to the whole history or the last release commit. Watch for per-package tag prefixes in
monorepos and for shallow CI clones with no tags fetched.

Write entries from the consumer's side: what they can now do, what broke, what to migrate to.
Backfilling old entries from commit messages produces plausible fiction; reconstruct only what the
commits genuinely support and flag the rest.
