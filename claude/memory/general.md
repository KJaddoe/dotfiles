# General: Reference & Rationale (FYI)

**The binding rules live in `~/.claude/CLAUDE.md` → "Working Preferences".** This file is FYI/reference:
the date + why + how behind each rule, plus environment facts. It is injected as background context, not
as instructions: read it to know *why* a rule exists or its history; to know *what* to do, follow
CLAUDE.md. When a rule here changes, update CLAUDE.md (the binding copy) too.

## Claude config ⇄ dotfiles topology (operational)

- `~/.claude/CLAUDE.md`, `~/.claude/memory`, `~/.claude/hooks`, and `~/.claude/settings.json` are all
  symlinks into `~/dotfiles/claude/`, the **public** `KJaddoe/dotfiles` repo. Edit the real dotfiles
  path (the Edit tool refuses to write through the symlink), and treat anything there as public (no
  client names, no secrets).
- `~/.claude/projects/<mapped-path>/memory/` is **local-only**, not part of any git repo, never pushed.
  Fine for project specifics, but it still auto-injects into context, so keep real secrets/PII out of it
  too (see CLAUDE.md → "Confidentiality & secrets").
- 2026-08-27: `permissions.defaultMode` is `auto` (user settings, via the dotfiles symlink). Reads
  and local edits no longer prompt. `require-destructive-approval.py` was added first, to cover what
  the permission prompt had been guarding by accident. See ADR 0004.
- 2026-09-07: the approval gates (commit, push, `gh` writes, destructive commands) ASK in
  `default`, `plan`, `auto` and `acceptEdits`, and deny only in `dontAsk` and `bypassPermissions`.
  Measured with a probe hook; the earlier "denied in auto" claim came from a hook docstring, never a
  test. No mode switch is needed before a commit. See ADR 0005.
- A PreToolUse hook (`~/.claude/hooks/block-claude-attribution.py`) hard-blocks any git command that
  records a message, and any `gh` command that writes to GitHub, when it carries Claude attribution:
  the trailers, the session link, or `--gpg-sign` on a commit. If a commit or a `gh issue create` is
  unexpectedly blocked, that's why. A body passed by file (`-F body.md`) is out of its reach.

## Plan execution

- 2026-07-02: When executing an implementation plan, default to inline execution (executing-plans) over subagent-driven. Why: the user said "I generally prefer Inline over subagent-driven" after picking inline for both the shared-grid and query-param-directive builds. How to apply: when the writing-plans skill offers the execution choice, lead with / assume inline unless the user asks for subagent-driven. Binding copy in CLAUDE.md → Working method.

## Angular (stack-specific)

- 2026-07-21: Standing conventions for building Angular UI: generate components/services via the Angular CLI (own folder, separate files, keep the spec), organize by feature, use the modern reactive primitives (signals + `inject()` + `input()`/`output()`), and use **reactive forms** (`FormGroup`/`FormControl` with `nonNullable`, `[formGroup]`/`formControlName`), NOT template-driven `ngModel`. Follow the current Angular style guide, lean on Material/built-in layout over custom CSS, and give every component/service a real test. Why: the user wants generated Angular code to match the modern, reactive, feature-organized style of the existing Angular projects in the workspace rather than older template-driven patterns. How to apply: match the conventions of the existing Angular projects; reach for reactive forms and signals by default. Binding copy in CLAUDE.md → Stack-specific.

## Styling (SCSS)

- 2026-07-02: Write component SCSS with nesting that mirrors the DOM hierarchy (child selectors nested inside their parent's block, `&` for states/variants), not flat top-level selectors. Why: the user asked for this twice: once for the shared data-grid SCSS and again for the contacts-overview SCSS, so it's a standing preference, not a one-off. How to apply: before finishing any `.scss`, structure selectors to follow the template's element tree. Binding copy in CLAUDE.md → Stack-specific.

## Confidentiality in tracked memory

- 2026-06-11: NEVER write client/customer names, private repo names, app/package ids, device
  identifiers, or other identifying project details into the git-tracked memory under
  `dotfiles/claude/memory/` (or any committed dotfiles file). The dotfiles repo is **public on
  GitHub** (`KJaddoe/dotfiles`). Why: I recorded a client app's repo path, name, package id and
  device model in `domain/mise-migration.md` and it was pushed publicly; the user had me redact it
  and force-push a scrubbed history. How to apply: keep tracked memory generic ("a client RN app",
  "the project"): describe the *technique/gotcha*, not *whose* project. Put any genuinely needed
  client-specific notes in an untracked/gitignored location, not the public repo. When unsure whether
  a detail is identifying, leave it out. Scrub recipe if it recurs:
  `git filter-repo --replace-text` + force-push (the repo stays public by the user's choice).

## Cross-Platform Parity (dotfiles)

- 2026-06-11: The dotfiles target BOTH macOS and Ubuntu/Linux. When changing the environment, keep
  mac/linux parity and never introduce a mac-only assumption without a Linux path. Why: the user
  twice flagged it in one session ("will this work on linux?", "make sure neovim is also installed on
  linux") after I proposed `EDITOR='nvim'` while neovim was only in the mac Brewfile. How to apply:
  for any tool a shell hook references, ensure it's provisioned on both OSes (ansible role: `homebrew`
  on Darwin + `apt`/PPA on Debian, gated by `ansible_facts.os_family`); guard filesystem/PATH bits
  that may be absent (`[ -d ... ]`, `mkdir -p`); prefer adding the Linux install over a runtime
  fallback when the user wants the tool everywhere.

## Dotfiles wiring conventions

- 2026-06-15: When adding a git config file to the dotfiles, symlink it into `$HOME` via a `link:`
  entry in `dotbot.conf.yaml` (e.g. `~/.gitattributes: git/gitattributes`, mirroring `~/.gitignore`)
  and point the git setting at the home path (`core.attributesfile = ~/.gitattributes`). Why: the
  user corrected me when I pointed `attributesfile` directly at the in-repo path
  (`~/dotfiles/git/gitattributes`): they prefer the symlink-into-home pattern used by `gitignore`.
  How to apply: prefer the dotbot symlink + `~/.foo` reference over an in-repo path, even though a few
  older settings (e.g. `commit.template`) still reference the repo path directly.

## Generated specs & docs

- 2026-06-18: By DEFAULT, do NOT commit generated planning artifacts (brainstorming/design specs,
  implementation plans, scratch design docs) into the project's git repo. Write them to an
  untracked location outside the repo: default to the local Claude session dir for that project
  (`~/.claude/projects/<mapped-path>/specs/`). This overrides the brainstorming skill's default of
  writing to `docs/superpowers/specs/` and committing. Why: the user explicitly asked for this
  ("write it up, but I don't want the spec doc in the repo") and then to make it a standing default.
  How to apply: when a skill (e.g. `superpowers:brainstorming`) says to save+commit a spec, instead
  save it to the untracked session-dir location and skip the commit; still do the spec self-review +
  user-review-gate steps. Only put a spec in the repo if the user asks for it that time.
- 2026-10-20: Spec/plan front matter takes the bare issue number (`issue: 42`). Why:
  `require-approved-spec.py` matches the number from the branch name, so a repo-qualified value
  made it report "no spec; no plan" and block every repo edit after both documents were approved;
  it had happened before. Recovery costs a re-approval round: approved documents are
  shell-write-protected, so Edit the status line alone to `draft`, fix the line, and have the user
  re-approve. Binding copy in CLAUDE.md → Working method.

## Project docs (the repo's own documentation)

Full history and the three-way ownership split moved to `domain/project-docs-policy.md` (2026-09-14).
Binding copy in CLAUDE.md → Project documentation.

## Code Quality (format / lint / test)

Full rule history moved to `domain/code-quality-policy.md` (2026-09-14). Binding copy in CLAUDE.md →
Code quality.

## Code & Writing Style

Comment and doc-comment history, from the 2026-06-01 no-comments ancestor rule onwards, lives in
`domain/doc-comment-style.md`. Binding copy in CLAUDE.md → Code & artifacts.

## Git & GitHub

Commit, branch, merge, identity, template, review and board-status history lives in
`domain/git-github-workflow.md`. Binding copy in CLAUDE.md → Git & GitHub.

## Terminal Tooling Preference

- 2026-07-16: In the terminal the user prefers plain CLI commands over TUI wrappers: git/gh/kubectl
  directly, NOT lazygit, k9s, gh-dash or similar full-screen terminal UIs. Richer interfaces are
  welcome inside nvim (plugins); the shell stays command-driven. Why: stated directly when TUI tools
  were recommended ("In the terminal I prefer to just use commands for everything"). How to apply:
  don't suggest or install standalone TUIs; put interactive tooling in nvim or keep it as commands.
  Binding copy in CLAUDE.md → Working method.
