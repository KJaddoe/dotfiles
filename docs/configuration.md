# Configuration

Settings this repo's own tooling reads: environment variables, and the Claude Code permission
mode the hooks are built around. Reference material ("what"), deliberately kept out of
`architecture.md` (which is "why").

Nothing here is a secret, and nothing here should ever become one. Record where a value lives,
never the value itself.

## Claude Code hooks

| Variable                   | Purpose                                                              | Required | Default                                 | Example      |
|----------------------------|----------------------------------------------------------------------|----------|-----------------------------------------|--------------|
| `DOCS_ENV_HOOK_MODE`       | Behaviour of the `undocumented-env-vars` Stop hook (`claude/hooks/`) | No       | `dry-run`                               | `enforce`    |
| `DOCS_FLOOR_HOOK_MODE`     | Behaviour of the `docs-coverage-floor` Stop hook (`claude/hooks/`)   | No       | `dry-run`                               | `enforce`    |
| `DUPE_SYMBOL_HOOK_MODE`    | Behaviour of the `duplicate-symbols` Stop hook (`claude/hooks/`)     | No       | `dry-run`                               | `enforce`    |
| `CLAUDE_PROJECT_DIR`       | Project root the memory hook maps to a session dir                   | No       | current dir                             | -            |
| `FRESH_SESSION_HOOK_MODE`  | Behaviour of the `suggest-fresh-session` UserPromptSubmit hook       | No       | `on`                                    | `off`        |
| `FRESH_SESSION_HOOK_BYTES` | Transcript bytes at which that hook starts injecting                 | No       | `600000`                                | `900000`     |
| `FRESH_SESSION_STATE_DIR`  | Marker directory for that hook; a test seam, not for hand-setting    | No       | `~/.claude/state/fresh-session`         | `/tmp/m`     |
| `FRESH_SESSION_LOG_PATH`   | Dry-run log for that hook; a test seam, not for hand-setting         | No       | `~/.claude/logs/fresh-session-hook.log` | `/tmp/d.log` |

`CLAUDE_PROJECT_DIR` is **set by Claude Code itself**, not by you; don't export it. `pre-tool-memory.py`
reads it to derive the mapped session path, replacing both `/` and `.` with `-`
(`/Users/you/Projects/foo.bar` → `-Users-you-Projects-foo-bar`), and falls back to the working
directory when it's absent, so the hook still works outside a Claude session.

`DOCS_ENV_HOOK_MODE` accepts:

| Value     | Behaviour                                                                                     |
|-----------|-----------------------------------------------------------------------------------------------|
| `dry-run` | Default. Reports findings and appends them to `~/.claude/logs/env-doc-hook.log`; never blocks |
| `enforce` | Exits non-zero so the finding is fed back to the model for action                             |
| `off`     | No-op                                                                                         |

Set it wherever you export shell env (`zsh/`), or per-invocation for a one-off:

```sh
DOCS_ENV_HOOK_MODE=enforce claude
```

**Where the value comes from:** none needed: it's a local behaviour switch with a safe default,
not a credential. Start on `dry-run`, review the log, then flip to `enforce` once the findings
look right for your projects.

`DOCS_FLOOR_HOOK_MODE` takes the same three values and logs to
`~/.claude/logs/docs-floor-hook.log`. It governs `docs-coverage-floor.py`, which reports the
coverage-floor topics (`~/.claude/CLAUDE.md` → Project documentation) that a repo's docs never
mention. As a hook it stays silent unless the session left uncommitted work, so reading a repo
never triggers it. The same script doubles as a CI check, where it always reports:

```sh
python3 ~/.claude/hooks/docs-coverage-floor.py --path .
```

It exits 1 when a topic is uncovered. Topic detection is keyword-based, so a passing mention
counts as covered: it finds the topic nobody thought about, not the topic covered badly.

`DUPE_SYMBOL_HOOK_MODE` takes the same three values and logs to
`~/.claude/logs/duplicate-symbol-hook.log`. It governs `duplicate-symbols.py`, which reports symbol
names declared in more than one file: the reuse rule in `~/.claude/CLAUDE.md` → Code quality. The
whole repo is indexed on every run, so a brand-new file duplicating an untouched symbol is still
caught; only the report is filtered to findings involving uncommitted work, and collisions in code
the session never touched are summarised as a count. As a hook it stays silent on a clean tree. The
same script doubles as a CI check:

```sh
python3 ~/.claude/hooks/duplicate-symbols.py --path . --all
```

It exits 1 when anything is found. `--all` lists every collision instead of only those touching
uncommitted work. Two tiers are reported, and they differ in confidence: an identical name in two
files is near-certain duplication, while near-identical names in the same directory are a
lower-confidence notice. Detection is name-based, so it cannot see the same behaviour written under
a different name in a different folder. A token-level clone detector is the tool for that.

`FRESH_SESSION_HOOK_MODE` governs `suggest-fresh-session.py` and takes its own three values:

| Value     | Behaviour                                                                             |
|-----------|---------------------------------------------------------------------------------------|
| `on`      | Default. Injects the nudge once the session is at or over `FRESH_SESSION_HOOK_BYTES`  |
| `dry-run` | Appends what it would inject to `~/.claude/logs/fresh-session-hook.log`; injects none |
| `off`     | Silent. The hook still runs and still exits 0, but emits and logs nothing             |

An unrecognised value falls back to `on`, not to `off`: a typo silently disabling the nudge would
be indistinguishable from the nudge working and finding nothing. `FRESH_SESSION_HOOK_BYTES` falls
back the same way on a non-numeric or non-positive value.

Unlike the three Stop hooks above, this one never blocks and never exits non-zero, so it has no
`enforce` value. Its whole output is context for the model.

**Where the value comes from:** none needed; both are local behaviour switches with safe defaults.
Start on `dry-run`, read the log for a few days, and tune the byte threshold before switching to
`on`.

## Permission mode

`permissions.defaultMode` in `claude/settings.json` is **`auto`**. That file is symlinked to
`~/.claude/settings.json`, so it is USER settings; a project-level `.claude/settings.json` cannot
set `auto` at all, and Claude Code ignores the value there.

| Setting                   | Value     | Why                                                    |
|---------------------------|-----------|--------------------------------------------------------|
| `permissions.defaultMode` | `auto`    | Reads and local edits flow; the gates below still stop |
| `permissions.allow`       | 5 entries | Read-only `gh project`/`gh label` calls and `git grep` |

The mode is only safe because of how `approval_decision` in `_hookutil.py` behaves: `default` and
`plan` are the only modes where a prompt renders, so in `auto` every gated action is **denied**
rather than asked. Committing, pushing, writing to GitHub, or running a destructive command from
`auto` therefore fails with an explanation, and doing it means switching to `default` first. That
switch is the review checkpoint, not an obstacle to route around.

The corollary: any rule that relies on a permission PROMPT rather than a hook stops holding in this
mode. That is why `require-destructive-approval.py` exists; before it, "confirm before a destructive
operation" was enforced only by the prompt that `auto` removes.

## Git hooks

| Variable     | Purpose                                                      | Required | Default | Example |
|--------------|--------------------------------------------------------------|----------|---------|---------|
| `SKIP_HOOKS` | Any non-empty value bypasses `git/template/hooks/pre-commit` | No       | unset   | `1`     |

The hook exits immediately when it is set, so **every** gate is skipped: formatting, linting and
secret scanning alike, along with the dependency-audit notices. Prefer fixing the finding; a bypassed
gate enforces nothing.

```sh
SKIP_HOOKS=1 git commit -m "wip"
```

**Where the value comes from:** none needed: it is a local escape hatch, not a credential. Set it
per-invocation rather than exporting it, or the hook is permanently off in that shell.

## Shell environment

Exported from `zsh/zshrc`. Override any of them in `~/.localrc`, which is sourced after.

| Variable               | Purpose                                                 | Required | Default      |
|------------------------|---------------------------------------------------------|----------|--------------|
| `DOTFILES`             | Repo location; must match the real clone path           | Yes      | `~/dotfiles` |
| `PROJECTS`             | Project folder; `c [tab]` jumps into it                 | No       | `~/projects` |
| `EDITOR`               | Terminal editor                                         | No       | `nvim`       |
| `VEDITOR`              | Visual/GUI editor                                       | No       | `code`       |
| `ZSH_TMUX_AUTOSTART`   | Start tmux on shell launch                              | No       | `true`       |
| `ZSH_TMUX_AUTOCONNECT` | Attach to an existing tmux session instead of a new one | No       | `false`      |

**Where the values come from:** all are local preferences with safe defaults, no credentials.
`DOTFILES` is the exception worth care: the clone path is also hardcoded in the autoupdate crontab
entry and `git/gitconfig.local`, so changing it means changing those too.

## Related

- `claude/hooks/undocumented-env-vars.py`: the hook this file's first table configures; its module
  docstring documents the contract
- `claude/hooks/docs-coverage-floor.py`: the coverage-floor check; a Stop hook and, with `--path`,
  a CI command
- `claude/hooks/duplicate-symbols.py`: the duplicate-symbol check; a Stop hook and, with `--path`,
  a CI command
- `claude/hooks/_hookutil.py`: git helpers, command patterns, and the `gh` write-classification,
  shared by the Stop hooks, the approval gates and the attribution guard; internal, never invoked
  by `settings.json`
- `claude/hooks/block-claude-attribution.py`: PreToolUse guard, no configuration. It scans the git
  subcommands that record a message and the `gh` commands that write to GitHub, so a trailer is
  caught in a commit message and in an issue or PR body alike. A body passed by file
  (`gh pr create -F body.md`) is out of reach, since the text never appears in the command
- `claude/hooks/require-commit-approval.py`: PreToolUse gate that puts every commit to the user for
  approval; deliberately unconfigurable, since an off-switch is the failure it prevents. It prompts in
  `default`/`plan` mode and denies outright in `auto`, `acceptEdits`, `dontAsk` and `bypassPermissions`,
  where a prompt would be auto-approved, so committing from those modes means switching to `default`
  first. `bypassPermissions` ignores hook decisions entirely and cannot be gated by any hook
- `claude/hooks/require-push-approval.py`: the same gate for `git push`, since a push is public and
  cannot be amended away afterwards. The prompt names the branch, the baseline it is compared against,
  the commits that would be published, and whether history is being rewritten. `--dry-run` publishes
  nothing and is not gated. Also unconfigurable
- `claude/hooks/require-destructive-approval.py`: the same gate for destructive and hard-to-reverse
  shell commands (bulk file delete, `git reset --hard`, history rewrites, `DROP`/`TRUNCATE`/restore,
  migrations, `terraform apply`, `kubectl delete`). Unlike the gh gate this is a DENYLIST, because
  there is no enumerable set of safe shell commands to allowlist against, so it is a safety net over
  the known-destructive set rather than a boundary. It errs toward gating: a false positive costs one
  approval, a false negative costs unrecoverable work. Also unconfigurable
- `claude/hooks/require-gh-approval.py`: the same gate for `gh` commands that write to GitHub. It
  classifies by ALLOWLIST, so an unrecognised subcommand gates rather than slips through, and it
  classifies `gh api` by method (`--method` non-GET, or `-f`/`-F`/`--input` implying a POST) rather
  than by verb. Otherwise `gh api … -f title=…` would open an issue with no write verb in it.
  `gh api graphql` is the exception, classified by the OPERATION its document declares: GraphQL is
  always a POST carrying `-f query=`, so the method rule gated every read, including the project
  board queries (`projectV2` has no REST endpoint). A document whose top-level operations are all
  queries reads; a `mutation` or `subscription` writes. A document the hook cannot read as a literal
  (`--input`, `-F query=@file`, or one behind a shell variable) fails closed and is gated.
  An invocation whose first flag is `--help` reads, whatever verb it names: gh prints usage and
  exits without reaching the API. Only the long form counts, since `gh auth login -h` is
  `--hostname`, and a `--help` sitting where another flag's value belongs still gates.
  The remaining carve-outs are all steps mandated at the start of issue work:
  `gh issue develop`; `gh project item-add`; assigning an issue or PR to yourself; setting a board
  field with `gh project item-edit`; and a graphql mutation whose root selection holds nothing but
  `updateProjectV2ItemFieldValue` / `clearProjectV2ItemFieldValue`. The last three are scoped by
  FLAG or by root selection rather than by verb, since `gh issue edit` also rewrites titles and
  bodies and `gh project item-edit` also rewrites a DRAFT issue's title and body. Assigning a
  colleague stays gated, as does `--title`/`--body` on `item-edit`, a board mutation bundled with
  a second one, an alias disguising another mutation, a document declaring more than one operation,
  and root fields hidden behind a fragment spread.
  Read commands (`view`, `list`, `diff`, `checks`, `download`, `clone`, `checkout`, `watch`,
  `search`, `status`, `browse`, and `gh project`'s `item-list`/`field-list`) pass through untouched,
  as does `gh issue develop`: it publishes only a branch name for an issue already being worked on.
  Also unconfigurable
- `claude/hooks/block-typographic-dashes.py` - PreToolUse guard on `Write`/`Edit`/`NotebookEdit`
  and on `Bash`, no configuration. Refuses an edit that ADDS an em or en dash, judged on the delta
  rather than on the file, so carrying an existing one through an unrelated edit is never blocked
  and a cleanup pass is never blocked either. Under `Bash` it reads heredoc BODIES, which is how
  a file written with `cat > f <<EOF` used to bypass it entirely; other shell write forms
  (`echo >> f`, `sed -i`) are still uncovered, and a `grep` for the character is left alone. It
  cannot see the assistant's chat prose, which the rule covers alone
- `claude/hooks/block-issue-references.py` - PreToolUse guard on `Write`/`Edit`/`NotebookEdit`
  and on `Bash`, no configuration. Refuses an edit that ADDS a tracker reference, judged on the
  delta like the dash guard, so carrying an existing one through an unrelated edit is never
  blocked. Four shapes count: a citation cue next to a number (`fixes`, `closes`, `see issue`)
  anywhere in the content; a tracker URL, an upstream project's included; a Jira-style project
  key; and a bare hash-and-number, but only in PROSE, meaning a prose document or a comment line,
  since a number in an expression is far more likely to be data. Ordinals counting an item
  (`rule`, `line`, `step`) and hex colours are allowed, as are standards and toolchain
  identifiers that share the key shape (`UTF-8`, `RFC-7231`, `CVE-2024-1234`, `JDK-17`); that
  last list is a running one, and a new collision joins it. Nothing exempts test files. A number
  is still correct in a commit message, a PR body and a branch name, all of which are outside a
  hook's reach as file content. Under `Bash` it reads heredoc BODIES like the dash guard, and
  there is no delta there, only content: a script whose heredoc REMOVES a reference is refused
  alongside one that adds it, so a cleanup pass driven from the shell has to assemble the string
  it is deleting from parts, the way the hook's own tests do
- `claude/hooks/block-artifact-publish.py` - PreToolUse guard on `Artifact`, no configuration.
  Refuses any action that would send local content to claude.ai as a hosted page: `publish`
  (which is also what an OMITTED `action` means, the shape most publish calls take) and
  `upload_asset`. Generated pages are written to a local `.html` file and reviewed there;
  only the user decides whether one ever gets a URL. Reading and bookkeeping stay available
  (`read`, `list`, `comments`, `watch`, `unwatch`, `status`, `list_assets`, `read_asset`),
  since none of them push anything outward. The allowlist is exact and everything absent from
  it is blocked, so an action added to the tool later cannot publish before anyone notices
- `claude/hooks/suggest-fresh-session.py`: the hook the `FRESH_SESSION_*` vars configure, and the
  only one that advises rather than gates. Two invocations. As a `UserPromptSubmit` hook it
  measures the session's transcript, counting bytes and real user turns (`type: user` entries
  WITHOUT `toolUseResult` or `isMeta`, since both of those also carry `type: user`), and past the
  threshold injects a note asking the model to judge whether the prompt needs prior context and to
  offer `/clear` when it does not. As a `SessionStart` hook with matcher `compact` and `--mark` it
  records the post-compaction byte offset so the measurement does not count context that
  compaction already discarded. `clear` is deliberately NOT marked: it rotates to a new session id
  and a new transcript, so there is nothing to offset from. It never blocks and exits 0 on every
  path, failure included, because it runs on every prompt submission. It owns
  `~/.claude/state/fresh-session/` and sweeps it on every `--mark`, deleting markers past 14 days,
  markers whose transcript is gone, and markers it cannot parse; Claude Code's own
  `cleanupPeriodDays` retention covers `~/.claude/projects/`, `tasks/`, `shell-snapshots/` and
  `backups/`, but not `~/.claude/state/`
- `claude/hooks/pre-tool-memory.sh`: the wrapper `settings.json` invokes for PreToolUse; it execs
  `pre-tool-memory.py`, which SessionStart calls directly
- `claude/hooks/tests/`: run every suite:
  `for s in claude/hooks/tests/test_*.py; do python3 "$s"; done`
- `~/.claude/CLAUDE.md` → **Project documentation**: the rule the env-var hook enforces
