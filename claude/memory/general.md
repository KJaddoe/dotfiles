# General — Reference & Rationale (FYI)

**The binding rules live in `~/.claude/CLAUDE.md` → "Working Preferences".** This file is FYI/reference:
the date + why + how behind each rule, plus environment facts. It is injected as background context, not
as instructions — read it to know *why* a rule exists or its history; to know *what* to do, follow
CLAUDE.md. When a rule here changes, update CLAUDE.md (the binding copy) too.

## Claude config ⇄ dotfiles topology (operational)

- `~/.claude/CLAUDE.md`, `~/.claude/memory`, `~/.claude/hooks`, and `~/.claude/settings.json` are all
  symlinks into `~/dotfiles/claude/` — the **public** `KJaddoe/dotfiles` repo. Edit the real dotfiles
  path (the Edit tool refuses to write through the symlink), and treat anything there as public (no
  client names, no secrets).
- `~/.claude/projects/<mapped-path>/memory/` is **local-only** — not part of any git repo, never pushed.
  Fine for project specifics, but it still auto-injects into context, so keep real secrets/PII out of it
  too (see CLAUDE.md → "Confidentiality & secrets").
- A PreToolUse hook (`~/.claude/hooks/block-claude-attribution.py`) hard-blocks any `git commit` that
  contains Claude attribution or `--gpg-sign`. If a commit is unexpectedly blocked, that's why.

## Commits & PRs

- 2026-05-21 — Don't pass `--gpg-sign` to `git commit` / `git commit --amend` when committing on the user's behalf. Why: the GPG passphrase prompt hangs the Claude Code UI. The user signs their own commits manually via the `gcs` alias when they need to.
- 2026-05-21 — Drop "Generated with Claude Code" / "🤖 Generated with [Claude Code]" / "Co-Authored-By: Claude …" trailers from every commit, PR body, issue, and generated artifact. Why: the user explicitly asked me to stop after seeing the trailer on a PR.

## Branches

- 2026-05-21 (reaffirmed 2026-06-17) — When starting work on a GitHub issue, always create a linked issue-branch via `gh issue develop <number> --repo <owner>/<repo> --base <base> --checkout` and let GitHub auto-generate the branch name. NEVER pass `--name` or use a custom branch name for issue-linked branches — the user explicitly never wants custom names, always the default GitHub naming. Why: keeps the branch ↔ issue link clean and matches the user's standing workflow; reaffirmed after a project-level note had drifted to recommending `--name <slug>`. Never use a bare `git checkout -b <name>` for issue work either.

## Acting under the user's identity

- 2026-05-26 — Before taking any action that will be publicly visible to others AND attributed to the user (their GitHub account, email, or any other identity), draft it and get explicit confirmation first. No exceptions. Covers: creating/editing/closing GitHub issues, PRs, PR/issue comments, reviews, releases, gists; pushing branches to remotes others can see; posting to Slack/email/external services; anything else that lands in someone else's inbox or notification feed under the user's name. Why: the user noticed I filed an issue on a private repo without showing a draft first; these actions are hard to fully undo (notifications already fired, watchers already pinged) and the user's name is on them. How to apply: even if the surrounding task was authorized ("create an issue for X"), pause after drafting the content and show title + body + labels (or message text, etc.) for review before the create/post call. Authorization for the *task* is not authorization for the *exact content*. Local-only actions (file edits, local commits, local branches that have not been pushed) are not covered by this rule.

## Code Review Workflow

- 2026-05-27 — When asked to review a PR ("review", "add comments", "leave feedback"), build a *pending* GitHub review with inline comments + `suggestion` blocks and walk through findings one at a time. Present each draft comment for sign-off *before* attaching it to the pending review (do not bulk-attach), and only call `…/events` to submit once the user explicitly approves. Don't edit working-tree files as the "fix" path — the deliverable is review comments, not local commits, unless the user later asks to push fixes. Why: user said in one session both "Don't publish anything publically untill we've gone through everything" and "we'll do the review step by step before adding all your suggestions" — after I edited a file directly and after I bulk-created a pending review with all findings at once. How to apply: use the `pending-pr-review` skill (invocable as `/pending-pr-review`) for the GraphQL-based technical workflow that lets you append comments incrementally to one pending review.

## Plan execution

- 2026-07-02 — When executing an implementation plan, default to inline execution (executing-plans) over subagent-driven. Why: the user said "I generally prefer Inline over subagent-driven" after picking inline for both the shared-grid and query-param-directive builds. How to apply: when the writing-plans skill offers the execution choice, lead with / assume inline unless the user asks for subagent-driven. Binding copy in CLAUDE.md → Working method.

## Angular (stack-specific)

- 2026-07-21 — Standing conventions for building Angular UI: generate components/services via the Angular CLI (own folder, separate files, keep the spec), organize by feature, use the modern reactive primitives (signals + `inject()` + `input()`/`output()`), and use **reactive forms** (`FormGroup`/`FormControl` with `nonNullable`, `[formGroup]`/`formControlName`) — NOT template-driven `ngModel`. Follow the current Angular style guide, lean on Material/built-in layout over custom CSS, and give every component/service a real test. Why: the user wants generated Angular code to match the modern, reactive, feature-organized style of the existing Angular projects in the workspace rather than older template-driven patterns. How to apply: match the conventions of the existing Angular projects; reach for reactive forms and signals by default. Binding copy in CLAUDE.md → Stack-specific.

## Styling (SCSS)

- 2026-07-02 — Write component SCSS with nesting that mirrors the DOM hierarchy (child selectors nested inside their parent's block, `&` for states/variants), not flat top-level selectors. Why: the user asked for this twice — once for the shared data-grid SCSS and again for the contacts-overview SCSS — so it's a standing preference, not a one-off. How to apply: before finishing any `.scss`, structure selectors to follow the template's element tree. Binding copy in CLAUDE.md → Stack-specific.

## Confidentiality in tracked memory

- 2026-06-11 — NEVER write client/customer names, private repo names, app/package ids, device
  identifiers, or other identifying project details into the git-tracked memory under
  `dotfiles/claude/memory/` (or any committed dotfiles file). The dotfiles repo is **public on
  GitHub** (`KJaddoe/dotfiles`). Why: I recorded a client app's repo path, name, package id and
  device model in `domain/mise-migration.md` and it was pushed publicly; the user had me redact it
  and force-push a scrubbed history. How to apply: keep tracked memory generic ("a client RN app",
  "the project") — describe the *technique/gotcha*, not *whose* project. Put any genuinely needed
  client-specific notes in an untracked/gitignored location, not the public repo. When unsure whether
  a detail is identifying, leave it out. Scrub recipe if it recurs: `git filter-repo --replace-text`
  + force-push (the repo stays public by the user's choice).

## Cross-Platform Parity (dotfiles)

- 2026-06-11 — The dotfiles target BOTH macOS and Ubuntu/Linux. When changing the environment, keep
  mac/linux parity and never introduce a mac-only assumption without a Linux path. Why: the user
  twice flagged it in one session ("will this work on linux?", "make sure neovim is also installed on
  linux") after I proposed `EDITOR='nvim'` while neovim was only in the mac Brewfile. How to apply:
  for any tool a shell hook references, ensure it's provisioned on both OSes (ansible role: `homebrew`
  on Darwin + `apt`/PPA on Debian, gated by `ansible_facts.os_family`); guard filesystem/PATH bits
  that may be absent (`[ -d ... ]`, `mkdir -p`); prefer adding the Linux install over a runtime
  fallback when the user wants the tool everywhere.

## Dotfiles wiring conventions

- 2026-06-15 — When adding a git config file to the dotfiles, symlink it into `$HOME` via a `link:`
  entry in `dotbot.conf.yaml` (e.g. `~/.gitattributes: git/gitattributes`, mirroring `~/.gitignore`)
  and point the git setting at the home path (`core.attributesfile = ~/.gitattributes`). Why: the
  user corrected me when I pointed `attributesfile` directly at the in-repo path
  (`~/dotfiles/git/gitattributes`) — they prefer the symlink-into-home pattern used by `gitignore`.
  How to apply: prefer the dotbot symlink + `~/.foo` reference over an in-repo path, even though a few
  older settings (e.g. `commit.template`) still reference the repo path directly.

## Generated specs & docs

- 2026-06-18 — By DEFAULT, do NOT commit generated planning artifacts (brainstorming/design specs,
  implementation plans, scratch design docs) into the project's git repo. Write them to an
  untracked location outside the repo — default to the local Claude session dir for that project
  (`~/.claude/projects/<mapped-path>/specs/`). This overrides the brainstorming skill's default of
  writing to `docs/superpowers/specs/` and committing. Why: the user explicitly asked for this
  ("write it up, but I don't want the spec doc in the repo") and then to make it a standing default.
  How to apply: when a skill (e.g. `superpowers:brainstorming`) says to save+commit a spec, instead
  save it to the untracked session-dir location and skip the commit; still do the spec self-review +
  user-review-gate steps. Only put a spec in the repo if the user asks for it that time.

## Project docs (the repo's own documentation)

- 2026-08-04 — Standing rule the user added after noticing docs were being left stale. Docs update in
  the SAME commit/PR as the change, never a later pass. The concrete misses that motivated it: a new
  env var added without recording what the value should be or where to get it; project
  structure/architecture undocumented; no deploy instructions. Why the first draft wasn't enough — it
  was purely reactive (fires only when something *changes*), so anything never documented in the first
  place never triggered, and deployment wasn't listed at all. Hence the **coverage floor**: what it is,
  setup/install + tooling versions, run, test, structure/architecture, config & env vars,
  deploy/release, CHANGELOG for versioned projects, project `CLAUDE.md` on convention changes. Filled
  in when work touches that area (report what's still missing) — NOT backfilled wholesale unasked.
  Also added: removals must delete the docs for the removed thing; docs must state what the code
  ACTUALLY does (verified, not aspirational); env vars need name/purpose/required/default/placeholder
  + where the real value lives — the LOCATION, never the value (ties to Confidentiality & secrets).
  How to apply: treat the docs edit as the same unit of work as the code edit. Do NOT confuse with
  "Generated specs & docs" above — project docs ARE a repo deliverable and get committed.
  Binding copy in CLAUDE.md → Project documentation.
- 2026-08-04 — Docs knowledge is split across THREE places by design; keep ownership strict or they
  drift. (1) `CLAUDE.md` → Project documentation = the always-on OBLIGATION (triggers, removals delete
  docs, coverage floor, verified-not-aspirational) — must stay in context or it never fires; a skill
  alone can't fix a *forgetting* problem. (2) The `writing-project-docs` SKILL = the procedure
  (inline/audit/remediate modes, the claim→where-to-verify table, env-var doc fields, anti-patterns).
  (3) `claude/templates/docs-pointer/` = the STRUCTURE (root `CLAUDE.md` pointer + `docs/README.md`,
  `architecture.md`, `decisions/` ADRs, `erd.md` for DB projects). Same shape as `pending-pr-review`
  (`5db1a9e`): terse rule in CLAUDE.md pointing at a skill that holds the detail.
- 2026-08-04 — The `docs-pointer` template is scoped "why, not what — rationale and relations the code
  doesn't make obvious", so it deliberately does NOT cover env vars, deploy, setup/run/test or API
  contracts. Those are "what" and belong in the README or a dedicated `docs/` page — do NOT cram them
  into `architecture.md`. NOTE: `claude/templates` was committed in `d7e874a` but never linked into
  `~/.claude/` by dotbot until 2026-08-04; the link entry was added so
  `~/.claude/templates/docs-pointer/` actually resolves from other projects.
- 2026-08-04 — A CHANGELOG is a doc of a DIFFERENT KIND and needs its own handling. Every other doc
  describes CURRENT STATE (verifiable against code, fixable any time); a changelog is an append-only
  record for an AUDIENCE — it can't be verified against code, never "drifts", and can only be
  INCOMPLETE. A missed entry is unrecoverable (you can't reconstruct what mattered to a consumer six
  months on), so it must land in the same commit. Trigger is "does someone downstream need to know"
  (feature, breaking change, deprecation, security fix), NOT "did code change" — internal refactors
  get no entry. Audit technique: `git log $(git describe --tags --abbrev=0)..HEAD --oneline` and look
  for user-visible commits with no entry. Backfilling from commit messages produces plausible fiction
  — only reconstruct what the commits genuinely support.
- 2026-08-04 — DRIFT LESSON (learned the hard way, same session): after splitting docs knowledge
  across CLAUDE.md / skill / template, the coverage floor got restated in BOTH the rule and the
  skill. One edit later they contradicted each other, and the "update the project's own CLAUDE.md on
  convention change" clause was silently dropped from the rule while the skill still asserted it.
  Fix applied: the skill now POINTS at CLAUDE.md for the floor instead of restating it. Rule of
  thumb — when the same fact lives in two files, it is already drifting; make one the owner and have
  the other link.
- 2026-08-04 — Docs rules are ENFORCED, not just written: `claude/hooks/undocumented-env-vars.py`
  is a Stop hook that diffs the session's added lines for new env var reads (JS/TS, .NET, Python)
  and blocks/reports any that appear in no doc. Modes via `DOCS_ENV_HOOK_MODE`: `dry-run`
  (default, logs to `~/.claude/logs/env-doc-hook.log`), `enforce`, `off` — documented in
  `docs/configuration.md`. Why: the user's complaint ("sometimes lacking") was a COMPLIANCE
  problem, and prose rule #41 in a file of 40 rules doesn't fix forgetting — same reasoning that
  produced `block-claude-attribution.py`. Rule of thumb: a "whenever X" behaviour needs a hook;
  CLAUDE.md alone cannot deliver it. Security constraint: the hook captures variable NAMES only,
  never the matched line, so secret VALUES in a diff can't leak into the log — locked in by
  regression tests. Dry-running it against this repo immediately caught a real false-positive
  class (its own test fixtures), which is why test/fixture paths are excluded.
- 2026-08-04 — `writing-project-docs` was written inline without the subagent pressure-testing
  `superpowers:writing-skills` mandates, then tested and rewritten the same day (`6b7a0dc`): three
  fresh agents applying it adversarially found six real defects — the anti-pattern and the coverage
  floor gave OPPOSITE answers on API/flags/exit codes, the audit taxonomy had no class for "list
  grew, doc didn't", and an audit that RUNS commands to verify them clobbers HOME and the global git
  identity via `script/test`. Lesson: an inline-written skill reads fine to its author; only a fresh
  agent applying it surfaces the contradictions.

## GitHub issue status (project boards)

- 2026-06-23 — Whenever I create a GitHub issue that goes onto a project board, set its **Status = "To Be Refined"** by default (do not leave Status unset). When I **update/edit an existing issue**, also set its Status back to **"To Be Refined"** AND add an issue comment stating that the status was set to "To Be Refined" because of changes made by Claude that a human needs to review. Why: the user wants every Claude-touched issue to land in the refinement column so a human verifies it before it moves forward. How to apply: after the create/edit call, set the project item's Status single-select to the "To Be Refined" option; on edits, post the explanatory comment too. Combine with the "Acting under the user's identity" rule — still draft issue/comment content for approval before the public create/post.

## Code Quality (format / lint / test)

- 2026-07-13 — Standing code-quality gate the user asked to add. (1) Format touched code with the project's formatter, else a locally available one; never mass-reformat untouched lines/files. (2) Lint every change with the project's linter, else a local one; if the project has NO linting, notify the user + propose options rather than skip. (3) Drive lint messages toward zero — fix root causes, don't blanket-suppress (`eslint-disable`, `#pragma warning disable`, `any`); justify any unavoidable suppression. (4) Write tests when possible; if no test setup, notify + propose options. (5) Definition of done = format + lint + tests all green, reported honestly (say so if anything fails/was skipped); on a large/slow suite run the changed-scope/affected tests each time (stating the scope run) and the full suite only when cheap or before merge/release. (6) Commit any formatter/linter/test config introduced, keeping mac/linux parity. Why: the user wants a consistently higher baseline and to be told (with options) when a project lacks linting/testing instead of having it silently skipped. How to apply: run these gates when finishing any code change; overlaps the verification-before-completion skill. Binding copy in CLAUDE.md → Code quality.
- 2026-07-13 — Global coding best practices the user chose to adopt (all four offered): (1) follow the codebase's existing conventions — read surrounding code first, mirror its patterns/naming/libraries, reuse existing helpers, no new dependency or parallel approach without sign-off; (2) never hardcode secrets in source (env/config/secret store); (3) leave the tree clean — delete dead/commented-out code and debug artifacts introduced (stray logging, `debugger`, throwaway TODOs); (4) input & injection safety — validate external input, parameterized queries not string-built SQL, escape output. Why: the user asked which global best practices would raise baseline quality and picked all four; #1 is the highest-value lever (fit the codebase, don't reinvent). Binding copy in CLAUDE.md → Code quality.
- 2026-07-13 — Two more global rules added after reviewing the stacks worked on often (Angular, .NET/C#+SQL Server, dotfiles ansible/dotbot, RN): (1) don't swallow errors — no empty catch/silent fallback, surface or handle meaningfully, log with context, fail loud/early; (2) scripts & automation (ansible, dotbot, migrations, version pinning) must be idempotent and safe to re-run (guard on state, expect changed=0). Why: both are language-agnostic and recurred in practice — the idempotency one is grounded in the mise-migration ansible work. NOTE: the biggest remaining gap is .NET/C# backend conventions, but those are stack-specific and belong in that project's own CLAUDE.md, not the global file (user declined a starter template for now). Binding copy in CLAUDE.md → Code quality.
- 2026-07-21 — Made the test-coverage bar explicit: every suite must cover THREE kinds of case, each at the layer where it's real — (1) the happy path; (2) edge/boundary cases; (3) what must NOT work and must stay broken (authorization/access denials, invalid or malformed input rejection, abuse/injection). Split by layer: server-side = SQL injection + authz bypass; client-side = output-escaping/XSS, authz-gated UI, input rejection. When a bug or bad input is found, lock it out with a regression test asserting it stays rejected. Why: "write tests when possible" (2026-07-13) was too loose — the negative/must-stay-broken cases are the ones most often skipped, and a found bug should never be able to silently return. How to apply: when writing or reviewing a test suite, check all three buckets are present, not just the happy path. Binding copy in CLAUDE.md → Code quality.

## Code & Writing Style

- 2026-06-01 — Don't add explanatory/descriptive comments to code or config files. Keep only what's functionally required (e.g. shebangs) and match the surrounding file's existing comment density, which is near-zero. Why: the user explicitly rejected added comments in a zsh dotfile and expects this as a standing preference. How to apply: write code without narration comments unless the user asks for them — the same terse style applies to commit messages (see Commits & PRs).
- 2026-07-13 — REFINED (function commenting): the user now wants a structured doc-comment (purpose + params + returns) on EVERY function, class, and method — JSDoc/TSDoc, C# XML `///`, or Python docstrings, matching the project's existing doc style. The 2026-06-01 rule still governs INLINE narration comments (explaining what a single line does) and config files — those stay comment-free. Net policy: API-level doc-comments YES, line-level narration NO. Why: the user asked to make function/class documentation a standing coding rule while keeping code self-explanatory line-by-line. Binding copy in CLAUDE.md → Code & artifacts.

## Terminal Tooling Preference

- 2026-07-16 — In the terminal the user prefers plain CLI commands over TUI wrappers: git/gh/kubectl
  directly, NOT lazygit, k9s, gh-dash or similar full-screen terminal UIs. Richer interfaces are
  welcome inside nvim (plugins) — the shell stays command-driven. Why: stated directly when TUI tools
  were recommended ("In the terminal I prefer to just use commands for everything"). How to apply:
  don't suggest or install standalone TUIs; put interactive tooling in nvim or keep it as commands.
  Binding copy in CLAUDE.md → Working method.
