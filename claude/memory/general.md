# General - Cross-Project Conventions

## Commits & PRs

- 2026-05-21 — Don't pass `--gpg-sign` to `git commit` / `git commit --amend` when committing on the user's behalf. Why: the GPG passphrase prompt hangs the Claude Code UI. The user signs their own commits manually via the `gcs` alias when they need to.
- 2026-05-21 — Drop "Generated with Claude Code" / "🤖 Generated with [Claude Code]" / "Co-Authored-By: Claude …" trailers from every commit, PR body, issue, and generated artifact. Why: the user explicitly asked me to stop after seeing the trailer on a PR.

## Branches

- 2026-05-21 — When starting work on a GitHub issue, always create a linked issue-branch via `gh issue develop <number> --repo <owner>/<repo> --base <base> --checkout` and let GitHub auto-generate the branch name (do not pass `--name`). Why: keeps the branch ↔ issue link visible in the GitHub UI and matches the user's standing workflow. Never use a bare `git checkout -b <name>` for issue work.

## Acting under the user's identity

- 2026-05-26 — Before taking any action that will be publicly visible to others AND attributed to the user (their GitHub account, email, or any other identity), draft it and get explicit confirmation first. No exceptions. Covers: creating/editing/closing GitHub issues, PRs, PR/issue comments, reviews, releases, gists; pushing branches to remotes others can see; posting to Slack/email/external services; anything else that lands in someone else's inbox or notification feed under the user's name. Why: the user noticed I filed an issue on a private repo without showing a draft first; these actions are hard to fully undo (notifications already fired, watchers already pinged) and the user's name is on them. How to apply: even if the surrounding task was authorized ("create an issue for X"), pause after drafting the content and show title + body + labels (or message text, etc.) for review before the create/post call. Authorization for the *task* is not authorization for the *exact content*. Local-only actions (file edits, local commits, local branches that have not been pushed) are not covered by this rule.

## Code Review Workflow

- 2026-05-27 — When asked to review a PR ("review", "add comments", "leave feedback"), build a *pending* GitHub review with inline comments + `suggestion` blocks and walk through findings one at a time. Present each draft comment for sign-off *before* attaching it to the pending review (do not bulk-attach), and only call `…/events` to submit once the user explicitly approves. Don't edit working-tree files as the "fix" path — the deliverable is review comments, not local commits, unless the user later asks to push fixes. Why: user said in one session both "Don't publish anything publically untill we've gone through everything" and "we'll do the review step by step before adding all your suggestions" — after I edited a file directly and after I bulk-created a pending review with all findings at once. How to apply: use the `pending-pr-review` skill (invocable as `/pending-pr-review`) for the GraphQL-based technical workflow that lets you append comments incrementally to one pending review.

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

## Code & Writing Style

- 2026-06-01 — Don't add explanatory/descriptive comments to code or config files. Keep only what's functionally required (e.g. shebangs) and match the surrounding file's existing comment density, which is near-zero. Why: the user explicitly rejected added comments in a zsh dotfile and expects this as a standing preference. How to apply: write code without narration comments unless the user asks for them — the same terse style applies to commit messages (see Commits & PRs).
