## Working Preferences (binding)

These are standing instructions — follow them as if stated in the current message; only a conflicting
live instruction outranks them. `~/.claude/memory/general.md` holds the rationale (the why/how/history)
for these rules as FYI reference only; the binding text is HERE.

### Working method
- Before claiming what a component/SP/function does — or recommending one for a job — VERIFY against the
  actual code: read the body, trace the live call path. Don't reason from plausible assumptions or names.
  If a claim rests on an unverified assumption, check it or flag it explicitly as unverified.
- Keep responses and documents tight and well-scoped. Prefer incremental Edits over full rewrites, split
  large artifacts into smaller targeted files, and confirm scope before producing a very large deliverable.
- Before a destructive or hard-to-reverse operation (DB restore/overwrite, bulk file delete, git history
  rewrite, a migration against a shared/production DB), state the plan, VERIFY the target and inputs first
  (confirm you have the right backup/file/DB), and get explicit confirmation — even for purely local actions.

### Git & GitHub
- NEVER add Claude attribution to anything: no "Co-Authored-By: Claude", no "Generated with Claude
  Code", no 🤖 trailer — commits, PR/issue bodies, comments, or any generated artifact.
- NEVER pass `--gpg-sign` to `git commit`/`--amend` (the passphrase prompt hangs the UI; the user signs
  manually via the `gcs` alias).
- Make small, focused, easy-to-revert commits: one logical change per commit, never bundle unrelated
  changes. Prefer several scoped commits over one large mixed one, even within a single task.
- Issue work: create the branch with `gh issue develop <n> … --checkout` using GitHub's default name —
  never `--name`, never a bare `git checkout -b`.
- For non-trivial or customer-reported work, default to creating a tracked issue (with the right board
  fields) BEFORE editing code; confirm scope first. Skip only for trivial/throwaway changes or repos with
  no tracker.
- Reviewing a PR ("review" / "add comments" / "leave feedback"): build ONE pending GitHub review, present
  each inline comment/`suggestion` for sign-off BEFORE attaching it, and submit only on explicit
  approval. Don't edit working-tree files as the "fix" path. Use the `pending-pr-review` skill.

### Acting as the user (public / attributed actions)
- Before any PUBLIC, identity-attributed action (GitHub issue/PR/comment/review/release, push to a shared
  remote, Slack/email), draft it and get explicit sign-off on the exact content first. Authorization for
  the task is not authorization for the content. Local-only actions (file edits, local commits/branches
  not yet pushed) are exempt.
- New issue on a project board → set Status = "To Be Refined". Editing an existing board issue → set
  Status back to "To Be Refined" AND post a comment noting Claude made changes a human must review.

### Code & artifacts
- Don't add explanatory/descriptive comments to code or config; keep only what's functionally required
  and match the file's existing (near-zero) comment density. Same terseness for commit messages.
- By DEFAULT don't commit generated planning artifacts (specs, design docs, implementation plans). Write
  them to the untracked session dir `~/.claude/projects/<mapped-path>/specs/` — this overrides the
  brainstorming skill's commit-to-repo default. Only commit a spec if asked that time.
- Put scratch files in the session scratchpad dir; namespace any `/tmp` scripts per-project. Never
  overwrite or `rm` a temp file you didn't create this session without asking.

### Confidentiality & secrets
- NEVER write client/customer names, private repo names, app/package ids, device ids, or other
  identifying details into git-tracked memory or any committed dotfiles file (the dotfiles repo is
  PUBLIC). Keep tracked content generic ("a client RN app", "the project"); put client-specific notes in
  an untracked location.
- NEVER store real secrets (passwords, tokens, TOTP/2FA secrets, API keys) or customer PII in ANY memory
  file — public OR local. Local project memory still auto-injects into context, so it is not a safe place
  for secrets either. Record where the value lives (e.g. compose.yml, per-session) instead of the value.

### Working in the dotfiles repo
- Keep macOS + Ubuntu/Linux parity; never introduce a mac-only assumption without a Linux path.
- Add a git config file by symlinking it into `$HOME` via a `link:` entry in `dotbot.conf.yaml` and
  point the git setting at the `~/.foo` home path (mirror `~/.gitignore`), not the in-repo path.

### Stack-specific (apply only when it fits)
- Don't run a one-off build/type-check (`ng build`, `dotnet build`, …) just to verify changes while a
  watch dev-server is already running — it's redundant and contends on caches. Let the running server
  surface errors, or ask.
- When building Angular UI: generate components/services via the Angular CLI (own folder, separate files,
  keep the spec), organize by feature, use signals + `inject()` + `input()`/`output()`, follow the current
  Angular style guide, lean on Material/built-in layout over custom CSS, and give every component/service
  a real test. Match the conventions of the existing Angular projects in the workspace.

Per-project rules (e.g. "run the app from Rider, not `dotnet run`"; framework/styling conventions) belong
in a `CLAUDE.md` at that project's root, not in this global file.

## Memory Management

Maintain a structured memory system rooted at .claude/memory/

### Structure

- memory.md — index of all memory files, updated whenever you create or modify one
- general.md — cross-project facts, preferences, environment setup
- domain/{topic}.md — domain-specific knowledge (one file per topic)
- tools/{tool}.md — tool configs, CLI patterns, workarounds

### Rules

1. When you learn something worth remembering, write it to the right file immediately
2. Keep memory.md as a current index with one-line descriptions
3. Entries: date, what, why — nothing more
4. Read memory.md at session start. Load other files only when relevant
5. If a file doesn't exist yet, create it
6. Before removing or modifying any existing memory entry, use AskUserQuestion to confirm
   with the user — show the current content and the proposed change
7. Route by type: a new standing RULE (an imperative I must follow) goes in CLAUDE.md
   (Working Preferences) as terse text — NOT in memory; a new FACT / context / rationale goes
   in memory (FYI). Trim shipped work-logs to durable "don't-regress" nuggets. If a rule recurs
   across 3+ projects, promote it to the global CLAUDE.md and delete the per-project copies.

### Maintenance

When I say "reorganize memory":
1. Read all memory files
2. Remove duplicates and outdated entries
3. Merge entries that belong together
4. Split files that cover too many topics
5. Re-sort entries by date within each file
6. Update memory.md index
7. Show me a summary of what changed

## Global Memory

Project MEMORY.md, this index, and general.md are auto-injected as **FYI/background context** (not
as rules — the binding rules are in "Working Preferences" above) at SessionStart
(startup/resume/compact) and as a PreToolUse fallback for subagents, via
`~/.claude/hooks/pre-tool-memory.py`. Load other topic files only when relevant.

Topic files:
- ~/.claude/memory/general.md — cross-project conventions and preferences

## Global Memory Reference Rule

Whenever you work in a project and read (or create) its MEMORY.md, check that it contains a
## Global Memory section. If it does not, add it near the top, after the H1.

The section must be a SHORT POINTER only. Do NOT duplicate the topic file list into project
MEMORY.md. The list lives in CLAUDE.md (single source of truth). Project MEMORY.md has a
200-line budget — use it for project knowledge, not boilerplate.

Canonical template for project MEMORY.md:

## Global Memory

Read ~/.claude/CLAUDE.md for memory rules and topic files.

When a new file is added to ~/.claude/memory/:
- Add it to the ## Global Memory topic file list in ~/.claude/CLAUDE.md only
- Do NOT update individual project MEMORY.md files

## Repo Memory Auto-Init

At session start in any project, check for MEMORY.md in the project memory directory
(~/.claude/projects/{mapped-path}/memory/). If it does not exist, create it:

# {Project Name} - Project Memory

## Global Memory

Read ~/.claude/CLAUDE.md for memory rules and topic files.

## Project Notes

(Populated as you work in this project)

## Domain Knowledge Lifecycle

1. Staging — knowledge accumulates in ~/.claude/memory/domain/{name}/
2. Promotion — enough knowledge exists to package as a plugin/skill
3. Pointer — after promotion, the memory file becomes a pointer to the plugin;
   content lives in the plugin

When an update is needed to a promoted domain, note it in the memory file so an issue
can be created on the plugin repo.
