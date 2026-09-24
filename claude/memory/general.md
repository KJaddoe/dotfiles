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
  and local edits no longer prompt; commits, pushes, `gh` writes and destructive commands are DENIED
  rather than asked, because `approval_decision` treats only `default`/`plan` as prompting modes.
  Switching to `default` is the review checkpoint. `require-destructive-approval.py` was added
  first, to cover what the permission prompt had been guarding by accident. See ADR 0004.
- A PreToolUse hook (`~/.claude/hooks/block-claude-attribution.py`) hard-blocks any git command that
  records a message, and any `gh` command that writes to GitHub, when it carries Claude attribution:
  the trailers, the session link, or `--gpg-sign` on a commit. If a commit or a `gh issue create` is
  unexpectedly blocked, that's why. A body passed by file (`-F body.md`) is out of its reach.

## Commits & PRs

- 2026-05-21: Don't pass `--gpg-sign` to `git commit` / `git commit --amend` when committing on the user's behalf. Why: the GPG passphrase prompt hangs the Claude Code UI. The user signs their own commits manually via the `gcs` alias when they need to.
- 2026-05-21: Drop "Generated with Claude Code" / "🤖 Generated with [Claude Code]" / "Co-Authored-By: Claude …" trailers from every commit, PR body, issue, and generated artifact. Why: the user explicitly asked me to stop after seeing the trailer on a PR.

## Branches

- 2026-05-21 (reaffirmed 2026-06-17): When starting work on a GitHub issue, always create a linked issue-branch via `gh issue develop <number> --repo <owner>/<repo> --base <base> --checkout` and let GitHub auto-generate the branch name. NEVER pass `--name` or use a custom branch name for issue-linked branches: the user explicitly never wants custom names, always the default GitHub naming. Why: keeps the branch ↔ issue link clean and matches the user's standing workflow; reaffirmed after a project-level note had drifted to recommending `--name <slug>`. Never use a bare `git checkout -b <name>` for issue work either.

## History integration (merge, never rebase)

- 2026-08-27: The user always integrates with merge and never rebases. Why: they want the whole history of everything that actually happened, and a rebase replays commits into a history that never occurred. How to apply: default to `git merge` / `git merge --no-ff` and `gh pr merge --merge`; never propose rebase, squash-merge, or a `--force-with-lease` history cleanup unless the user asks for it that time. Root cause of the complaint was config, not choice: `git/gitconfig.local` had `[pull] rebase = true`, so every plain `git pull` on a diverged branch rebased silently without either of us naming it. Set to `rebase = false` on 2026-08-27, and the repo-local `.git/config` override in the dotfiles repo was unset. An explicit `git rebase` was already gated by `claude/hooks/require-destructive-approval.py`, and `gh pr merge` by `require-gh-approval.py`, so no new CLAUDE.md rule was added: config plus the existing hooks cover it.

## Acting under the user's identity

- 2026-05-26: Before taking any action that will be publicly visible to others AND attributed to the user (their GitHub account, email, or any other identity), draft it and get explicit confirmation first. No exceptions. Covers: creating/editing/closing GitHub issues, PRs, PR/issue comments, reviews, releases, gists; pushing branches to remotes others can see; posting to Slack/email/external services; anything else that lands in someone else's inbox or notification feed under the user's name. Why: the user noticed I filed an issue on a private repo without showing a draft first; these actions are hard to fully undo (notifications already fired, watchers already pinged) and the user's name is on them. How to apply: even if the surrounding task was authorized ("create an issue for X"), pause after drafting the content and show title + body + labels (or message text, etc.) for review before the create/post call. Authorization for the *task* is not authorization for the *exact content*. Local-only actions (file edits, local commits, local branches that have not been pushed) are not covered by this rule.

## Template content

- 2026-09-22: Keep GitHub issue bodies short: only the information actually needed to act on the issue, no padding or restated context. Why: the user said "for a lot of issues you write a lot of text that doesn't really say anything. I prefer issues to be short with only the information you actually need." How to apply: before posting an issue body, cut any sentence that doesn't add information the reader needs; prefer a short bulleted list over prose paragraphs.
- 2026-09-23: Per-kind issue body templates (bug, feature, question, tech-debt, chore) live at `git/templates/issues/` in the dotfiles repo, read only by Claude. Why: the user asked for the brevity rule above to be backed by concrete structure, as a dotfiles-wide convention rather than a Claude-specific artifact. This went through two rounds of naming: first `claude/templates/issues/` (rejected, wanted it dotfiles-wide not Claude-specific), then a standalone `git/issue-templates/` (rejected as confusing next to the pre-existing `git/template/` singular git-hooks dir), landing on consolidating both into one `git/templates/` with `hooks/` (the renamed former `git/template/hooks/pre-commit`) and `issues/` subfolders. The user then also asked why the `~/.git-template` symlink name stayed singular once it pointed at the plural `templates/` dir, so that got renamed to `~/.git-templates` too (`dotbot.conf.yaml`, `git/gitconfig.local`'s `core.hooksPath`). Functionally safe to co-locate hooks and issue content because `core.hooksPath` reads `hooks/pre-commit` as one specific file, not a directory copy (`init.templateDir` is deliberately unset), so `issues/` never ships into new repos. How to apply: the CLAUDE.md rule references the templates by the absolute `~/dotfiles/git/templates/issues/` path (mirroring `README.md`'s "repo must live at `~/dotfiles`" convention) so it resolves regardless of which project's directory a session is working in. Next time a new content-skeleton type is needed under `git/templates/`, follow the same subfolder pattern rather than inventing a sibling top-level directory.
- 2026-09-23: `git/templates/pull-request.md` (moved from the former top-level `git/PULL_REQUEST_TEMPLATE.md`, content unchanged) joined the same `git/templates/` consolidation, following the pattern above. Why: the user asked for a PR-body template right after the issue-templates consolidation, and it made sense to fold in rather than leave a lone file back at `git/` root. `bin/new-project` still copies it into a scaffolded project's `.github/PULL_REQUEST_TEMPLATE.md` (updated source path), which is the one place this template is GitHub-native rather than Claude-read-only. How to apply: `CLAUDE.md`'s PR-body-drafting rule points at `~/dotfiles/git/templates/pull-request.md`.

## Code Review Workflow

- 2026-05-27: When asked to review a PR ("review", "add comments", "leave feedback"), build a *pending* GitHub review with inline comments + `suggestion` blocks and walk through findings one at a time. Present each draft comment for sign-off *before* attaching it to the pending review (do not bulk-attach), and only call `…/events` to submit once the user explicitly approves. Don't edit working-tree files as the "fix" path: the deliverable is review comments, not local commits, unless the user later asks to push fixes. Why: user said in one session both "Don't publish anything publically untill we've gone through everything" and "we'll do the review step by step before adding all your suggestions", after I edited a file directly and after I bulk-created a pending review with all findings at once. How to apply: use the `pending-pr-review` skill (invocable as `/pending-pr-review`) for the GraphQL-based technical workflow that lets you append comments incrementally to one pending review.

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

## Project docs (the repo's own documentation)

Full history and the three-way ownership split moved to `domain/project-docs-policy.md` (2026-09-14).
Binding copy in CLAUDE.md → Project documentation.

## GitHub issue status (project boards)

- 2026-06-23: Whenever I create a GitHub issue that goes onto a project board, set its **Status = "To Be Refined"** by default (do not leave Status unset). When I **update/edit an existing issue**, also set its Status back to **"To Be Refined"** AND add an issue comment stating that the status was set to "To Be Refined" because of changes made by Claude that a human needs to review. Why: the user wants every Claude-touched issue to land in the refinement column so a human verifies it before it moves forward. How to apply: after the create/edit call, set the project item's Status single-select to the "To Be Refined" option; on edits, post the explanatory comment too. Combine with the "Acting under the user's identity" rule: still draft issue/comment content for approval before the public create/post.

## Code Quality (format / lint / test)

Full rule history moved to `domain/code-quality-policy.md` (2026-09-14). Binding copy in CLAUDE.md →
Code quality.

## Code & Writing Style

Doc-comment evolution (seven revisions, 2026-07-13 to 2026-09-24; the last two make each
language's official standard the baseline and allow tag-free one-line blocks) lives in `domain/doc-comment-style.md`. Binding copy in CLAUDE.md → Code & artifacts. What stays
here: 2026-06-01, don't add explanatory/descriptive comments to code or config files; keep only
what's functionally required (e.g. shebangs) and match the surrounding file's existing near-zero
comment density. Why: the user explicitly rejected added comments in a zsh dotfile and expects this
as a standing preference; the same terse style applies to commit messages (see Commits & PRs).

## Terminal Tooling Preference

- 2026-07-16: In the terminal the user prefers plain CLI commands over TUI wrappers: git/gh/kubectl
  directly, NOT lazygit, k9s, gh-dash or similar full-screen terminal UIs. Richer interfaces are
  welcome inside nvim (plugins); the shell stays command-driven. Why: stated directly when TUI tools
  were recommended ("In the terminal I prefer to just use commands for everything"). How to apply:
  don't suggest or install standalone TUIs; put interactive tooling in nvim or keep it as commands.
  Binding copy in CLAUDE.md → Working method.
