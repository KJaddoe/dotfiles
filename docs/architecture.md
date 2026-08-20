# Architecture

> Why, not what. The config files are authoritative; this captures how they relate.

## Overview

Two independent halves, run in sequence by `script/bootstrap`:

1. **dotfiles (symlink) side** — topic folders at the repo root, linked into `$HOME` by
   [Dotbot](https://github.com/anishathalye/dotbot) per `dotbot.conf.yaml`.
2. **`_system/` (Ansible) side** — `_system/main.yml` provisions the actual tools/packages
   (languages, CLIs, databases) via one role per tool. This is the machine setup; the symlink
   side is the config those tools read.

Split rationale: provisioning (install software, idempotent, needs root on Linux) is a different
concern from config (symlink dotfiles, no root). Keeping them separate lets either run alone.

## Components

- **Topic folders** (`git/`, `node/`, `claude/`, …) — one per area. Files are picked up by
  convention, not by an explicit manifest:
  - `*/*.zsh` are sourced by `zsh/zshrc` (glob `$DOTFILES/*/*.zsh`).
  - `*/path.zsh` loads **first** (set up `$PATH`), `*/completion.zsh` loads **last**.
  - `bin/*` is added to `$PATH`. A script named `git-<name>` there becomes the `git <name>`
    subcommand for free — that's the home for git helpers with real logic (`bin/git-gone`),
    since a `gitconfig.local` alias is a config string and so invisible to shellcheck and tests.
  - `*/install.sh` (executable) runs at bootstrap and `dot_update`.
- **`dotbot.conf.yaml`** — the symlink manifest and **sole owner of plain config symlinks**:
  maps in-repo paths to `~/.foo` targets. Add a new linked config here, and point the tool's
  setting at the `~/.foo` home path (not the in-repo path), mirroring `~/.gitignore`.
- **`_system/`** — Ansible: `main.yml` (role list), `roles/<tool>/`, `requirements.yml`,
  `hosts.ini`. `should_be_root` is true except under Homebrew (macOS). Roles provision software;
  they do **not** symlink plain configs (that's dotbot's job — see ADR 0001). The exception is
  `ssh`, whose link carries dir-mode + backup logic dotbot can't express.
- **`claude/`** — global Claude Code config, symlinked into `~/.claude/` (`settings.json`,
  `CLAUDE.md`, `hooks/`, `memory/`, `skills/`, `keybindings.json`, `templates/`). `templates/`
  holds starter scaffolding, currently `docs-pointer/` — a `CLAUDE.md.template`, a `docs/`
  skeleton, and its own `README.md` carrying the apply steps (copy, then replace the `{...}`
  placeholders); don't copy the directory wholesale. `hooks/` enforce CLAUDE.md rules the harness
  can check mechanically rather than trusting the model to remember — see `docs/configuration.md` for
  their switches (ADR 0002 covers why hooks rather than prose alone). `docs-coverage-floor.py` is
  the one that also runs standalone (`--path`), because the documentation coverage floor is a
  repo property rather than a session event, so CI can gate it too. The repo-root `CLAUDE.md`
  (this trial) is separate: it is repo-level project instructions, not the global config.

## Python tooling (hooks)

Hooks are plain Python 3, no third-party runtime dependencies — they must work on a freshly
bootstrapped machine before anything is installed.

| Task      | Command                                                                            |
|-----------|------------------------------------------------------------------------------------|
| Test      | `for s in claude/hooks/tests/test_*.py git/tests/test_*.py; do python3 "$s"; done` |
| Test nvim | `python3 nvim/tests/test_lint.py`                                                  |
| Format    | `black claude/hooks/ git/tests/ nvim/tests/`                                       |
| Lint      | `pylint claude/hooks/ git/tests/ nvim/tests/`                                      |

`script/test` runs the hook suites first, before its (destructive) bootstrap steps.

`nvim/tests/` is the exception it does **not** run. Those tests drive a real headless nvim against
`nvim/config`, so they need nvim, an installed plugin set and pylint on PATH, while the hook suites
deliberately need nothing but python3 and git — which is what makes them safe to run before the
bootstrap. They skip cleanly when any of that is missing. They point `XDG_CONFIG_HOME` at the in-repo
config rather than `~/.config/nvim`, so they cover this repo whether or not dotbot has run.

`git/tests/` covers the shipped git `pre-commit` hook (see below) and `bin/git-gone`. It lives outside
`git/template/` on purpose: git copies that directory wholesale into every new repo, so a `tests/`
folder inside it would ship too. The suite neutralises `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM`
and works in throwaway repos, so unlike `script/test` it cannot touch your real git config.

`pyproject.toml` at the repo root holds the shared `black` / `pylint` settings (line length 100)
so formatting is reproducible across machines. Tests use stdlib `unittest` for the same reason —
no dependency to install. `black` and `pylint` are dev-only; neither is needed to run a hook.

## Git commit hook

`git/template/hooks/pre-commit` ships via `init.templateDir` (`~/.git-template`), so **every repo
created with `git init` from this machine** gets it — existing repos do not, copy it in manually.

This repo is always one of those, on every machine. `init.templateDir` is set by
`git/gitconfig.local`, which dotbot links only once the clone already exists, so the dotfiles clone
is made before the setting exists and never picks the hook up. Part of bootstrapping a fresh
machine is therefore:

```sh
cp ~/.git-template/hooks/pre-commit .git/hooks/pre-commit
```

It enforces the format+lint half of the definition of done on staged files: whitespace errors, then
betterleaks, prettier/eslint, black/pylint, shellcheck, `zsh -n`, stylua/selene, csharpier, hadolint,
markdownlint and yamllint. Each tool runs only when it is **installed AND the project configures it**,
so it stays silent in repos that haven't opted in. It checks, never rewrites what you staged. Bypass
with `SKIP_HOOKS=1 git commit …`.

**Secret scanning is the one gate with no opt-in.** Every other tool waits for project config, because
formatting is a matter of taste that a shared repo gets to decide. A committed credential is not —
it is the single mistake no later gate can undo, since rewriting published history does not unpublish
the secret. So it runs wherever it is installed. It reads the staged diff
(`betterleaks git --staged`), takes well under a second, and needs no network.

The tool is `betterleaks`, not the better-known `gitleaks`, because gitleaks' own README declares it
feature complete — security patches only — and points at betterleaks, written by the same authors
including the original one. The CLI is a drop-in: same `git --staged` invocation, same exit codes, and
it still reads `GITLEAKS_CONFIG`. Picking the frozen tool would have meant adopting a dependency with
a known end date.

Two detection rules are load-bearing. ESLint is detected by flat config only (`eslint.config.*`) —
`.eslintrc*` was removed in ESLint 9 and matching it would gate on a file ESLint no longer reads. C#
is checked with `csharpier`, the same tool that formats it on save; `dotnet format` is a different
formatter, and gating with one while formatting with the other fails the hook on correct code.

Most tools select files by extension, but shell scripts are commonly extensionless (`bin/git-gone`),
so shellcheck additionally picks up any staged file with no extension whose shebang names a shell it
can parse — `sh`, `bash`, `dash`, `ksh`, directly or via `env`. `zsh` is excluded because shellcheck
cannot parse it — and neither can `shfmt`, so zsh has no linter or formatter at all. `zsh -n`, a
syntax check, is the only gate available for it; that is worth having because a parse error in a
sourced file breaks *every new shell*, not just the script. It matches `*.zsh`, `zshrc` and `zshenv`
by name only — extensionless zsh scripts are not covered, unlike the shellcheck shebang scan.

Tests are deliberately excluded — a hook slow enough to be bypassed enforces nothing.

It also prints the matching audit command (`npm audit`, `pip-audit`, `dotnet list package
--vulnerable`) when a staged path is a dependency manifest. These are **notices, not gates**: they
never fail the commit, because a real audit needs the network and would be bypassed on the first slow
day. A `pyproject.toml` only counts when it actually declares dependencies, so config-only ones (like
this repo's) stay quiet.

## Editor formatting and linting

`conform.nvim` formats on save (`nvim/config/lua/user/plugins/init.lua`), falling back to the LSP for
any filetype it has no formatter for. Indent width is **not** set there — `shfmt` and `csharpier` both
read `.editorconfig`, so `~/.editorconfig` (from `editorconfig/editorconfig`) is what decides it.
That file is `root = true` in `$HOME`, so it applies to every project below it that has none of its
own. This repo adds a non-root `.editorconfig` so its own extensionless scripts in `bin/`, `script/`
and `git/template/hooks/` get the same 4-space indent as its `*.sh` files.

Linting is LSP-first. `nvim-lint` is wired only to the filetypes no enabled language server already
covers, because running both would double every diagnostic:

| Language   | Linted by                         | Runner    |
|------------|-----------------------------------|-----------|
| JS/TS      | `eslint`                          | LSP       |
| Shell      | `shellcheck`, via `bashls`        | LSP       |
| C#         | Roslyn analyzers, via `roslyn_ls` | LSP       |
| Lua        | `lua_ls` diagnostics              | LSP       |
| Ansible    | `ansible-lint`, via `ansiblels`   | LSP       |
| Python     | `pylint`                          | nvim-lint |
| Dockerfile | `hadolint`                        | nvim-lint |
| Markdown   | `markdownlint-cli2`               | nvim-lint |
| YAML       | `yamllint`                        | nvim-lint |

Python needs `nvim-lint` because `jedi_language_server` publishes at most one diagnostic per file (a
syntax error) and does no rule linting. `yaml.ansible` buffers keep their exact filetype, so
`yamllint` does not fire on files `ansiblels` already lints.

XML is deliberately unformatted: the only locally available tool, `xmllint --format`, injects an
`<?xml …?>` declaration into files that lack one, which would rewrite every `.csproj` on first save.

## Other languages

Python is the only language here with a repo-level formatter, linter, and test command. The rest have
tooling present but no repo-level command, so running them over this repo is manual:

| Language | Tooling present                                    | Configured?                   |
|----------|----------------------------------------------------|-------------------------------|
| Shell    | `shellcheck` + `shfmt` (each its own ansible role) | Linter gated, shfmt manual    |
| Lua      | `stylua` (own topic), `selene` (own topic)         | Command below, gated          |
| zsh      | none exists — `zsh -n` only                        | Syntax gated, never formatted |
| Ansible  | 32 roles under `_system/`                          | Linted in-editor, not gated   |
| Markdown | `markdownlint-cli2` (`.markdownlint-cli2.jsonc`)   | Gated repo-wide               |

109 `ansible-lint` findings remain across `_system/`, so that is reported in the editor but not yet
gated. zsh is the second-largest filetype here (26 files) and the only one with no formatter and no
linter in existence — `shfmt` and `shellcheck` both refuse to parse it, so a syntax check is the
ceiling, not a placeholder for something better.

Markdown is gated because `.markdownlint-cli2.jsonc` at the repo root is what switches the hook's
markdown check on — it only runs where a project ships a config. The config governs this repo's own
sources, so like `pyproject.toml` and `.editorconfig` it stays at the root and is not linked into
`$HOME`.

`ignores` excludes only what this repo carries but does not author: vendored `dotbot/`.
`claude/memory/` and `claude/CLAUDE.md` are symlinked into `~/.claude/` as payload, but they are
authored here, so they are linted like everything else — the files that state the conventions are
held to them. The cost is that a memory rewrite now has to pass the gate to be committed.

Three rules are off because they contradict conventions here rather than
catching defects — `MD013` (line length: the skills mix prose wrapped at ~100 with deliberately
unwrapped lines), `MD025` (the README's `PHILOSOPHY` / `Installation` / `Personalization` headings
are top-level by design), and `MD041` (`git/PULL_REQUEST_TEMPLATE.md` correctly opens with a form
field, not a heading). Everything else is on, including `MD060`, which enforces the aligned-table
convention mechanically.

Lint markdown with:

```sh
markdownlint-cli2 "**/*.md"
```

Lint shell with:

```sh
git ls-files | grep -E '\.(sh|bash)$|^script/|^bin/' | xargs shellcheck
```

Lint Lua with:

```sh
selene --config selene/selene.toml nvim/config/lua/
```

`--config` is not optional: selene reads `selene.toml` from the working directory only and does **not**
search parent directories, so it cannot find a config held in a topic folder on its own. That is why
`selene/` is a topic folder but *not* a dotbot symlink — a `~/selene.toml` would only ever apply when
the shell sits in `$HOME`, unlike `~/.editorconfig` and `~/.prettierrc.json`, whose tools do search
upward. The `pre-commit` hook passes `--config` for the same reason, accepting either a root
`selene.toml` (selene's own convention, preferred) or `selene/selene.toml` (this repo's layout).
`vim.toml`, the standard library `selene.toml` names, is resolved relative to the config file, so the
two must stay side by side.

The zsh files are excluded on purpose — shellcheck cannot parse zsh. `bin/` is listed explicitly
because its scripts are extensionless and the glob alone would miss them; the `pre-commit` hook
covers the same files by reading shebangs instead, which works in any repo rather than only this
one. The shipped hook and `bin/` are clean, but 14 findings (1 error, 4 warnings, 9 notes) remain in
older `install.sh` scripts, so this is **not** wired into `script/test` yet; doing that means fixing
those first.

Closing the remaining gaps means adding the config and a command here, not just installing the tool.

## Cross-repo / external relations

- **Antidote** manages zsh plugins from `antidote/zsh_plugins.txt`; **Powerlevel10k** is the
  prompt (`powerlevel10k/p10k.zsh`).
- **Dotbot** is a git submodule (`dotbot/`).
- Per-machine secrets/overrides stay out of the repo: `~/.localrc` (shell), `~/.gitconfig`
  (includes the managed one), `~/.ssh/config.local`.

## Conventions worth knowing

- **mac/Linux parity** — every change must work on both; never add a mac-only assumption without
  a Linux path. Ansible keys off `ansible_pkg_mgr` (`brew` vs not) / `ansible_facts.os_family`.
- **tmux status bar** — native tmux config in `tmux/tmux.conf`, with no status-bar plugin (see
  ADR 0003). It sits **after** the `run '~/.tmux/plugins/tpm/tpm'` line, because TPM loads plugins
  at that point and styling set before it can be overridden. Parts that need a shell are standalone
  scripts in `bin/` (`tmux-battery`, `tmux-git-branch`), invoked by name from `#()` and so resolved
  through `$PATH` — they render empty rather than erroring if the tmux server's environment lacks
  `bin/`. `tmux-git-branch` shortens a name over 32 characters to its first and last twelve around
  an ellipsis, mirroring powerlevel10k's truncation of the same branch so the prompt and the bar
  agree, and so one long branch cannot consume the whole `status-right-length` budget. Colours are
  tokyonight-night hexes, matching nvim's colorscheme and Ghostty's built-in `TokyoNight Night`
  theme.

## Adding a tool

Most tools take two edits: a topic folder (config, linked via `dotbot.conf.yaml`) and a
`_system/roles/<tool>/` role added to `_system/main.yml` (install). A role is structured
mac/Linux-parallel, branching on `ansible_facts.os_family`:

- **macOS** — `homebrew:` / `homebrew_cask:` / `homebrew_tap:`.
- **Debian/Ubuntu** — `apt:`. For a package in the base repos that's the whole story; for a
  vendor apt repo, follow the keyring + deb822 recipe below.

Config files a tool reads stay in dotbot, not the role (see ADR 0001) — `ssh` is the only role
that symlinks, because its link carries dir-mode + backup logic dotbot can't express.

### Vendor apt repository recipe

`apt_key` and `apt_repository` are **deprecated** (removed in ansible-core 2.25) — don't use
them. Per role, on Debian:

1. Install prerequisites including **`python3-debian`** (required by `deb822_repository`).
2. Ensure the keyring dir: `file: path=/etc/apt/keyrings state=directory mode=0755`.
3. Fetch the signing key with `get_url` into a keyring file (never the global trusted keyring).
   New roles use `/etc/apt/keyrings/<tool>.asc`; some older roles use `/usr/share/keyrings/` —
   either works, prefer `/etc/apt/keyrings` for new ones.
4. Add the repo with `deb822_repository:` — `name`, `types: deb`, `uris`, `suites`, `components`,
   `architectures`, and `signed_by:` set to the keyring path (it also accepts a key URL, but we
   keep the explicit `get_url` step for consistency and so the key is testable on disk).

Models to copy: `gh` / `mise` (keyring + deb822), `docker` (dearmored `.gpg` key), `powershell`
& `sqlcmd` (shared Microsoft repo). For an Ubuntu **PPA**, `deb822_repository` can't take the
`ppa:` shorthand — use `command: add-apt-repository -y ppa:<owner>/<name>` (see `neovim`), which
needs `software-properties-common` and handles the key itself.
