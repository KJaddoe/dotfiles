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
  - `bin/*` is added to `$PATH`.
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
  their switches (ADR 0002 covers why hooks rather than prose alone). The repo-root `CLAUDE.md`
  (this trial) is separate: it is repo-level project instructions, not the global config.

## Python tooling (hooks)

Hooks are plain Python 3, no third-party runtime dependencies — they must work on a freshly
bootstrapped machine before anything is installed.

| Task   | Command                                                                        |
|--------|--------------------------------------------------------------------------------|
| Test   | `for s in claude/hooks/tests/test_*.py git/tests/test_*.py; do python3 "$s"; done` |
| Format | `black claude/hooks/ git/tests/`                                                |
| Lint   | `pylint claude/hooks/ git/tests/`                                               |

`script/test` runs the hook suites first, before its (destructive) bootstrap steps.

`git/tests/` covers the shipped git `pre-commit` hook (see below). It lives outside
`git/template/` on purpose: git copies that directory wholesale into every new repo, so a `tests/`
folder inside it would ship too. The suite neutralises `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM`
and works in throwaway repos, so unlike `script/test` it cannot touch your real git config.

`pyproject.toml` at the repo root holds the shared `black` / `pylint` settings (line length 100)
so formatting is reproducible across machines. Tests use stdlib `unittest` for the same reason —
no dependency to install. `black` and `pylint` are dev-only; neither is needed to run a hook.

## Git commit hook

`git/template/hooks/pre-commit` ships via `init.templateDir` (`~/.git-template`), so **every repo
created with `git init` from this machine** gets it — existing repos do not, copy it in manually.

It enforces the format+lint half of the definition of done on staged files: whitespace errors, then
prettier/eslint, black/pylint, shellcheck, stylua, and `dotnet format`. Each tool runs only when it
is **installed AND the project configures it**, so it stays silent in repos that haven't opted in.
It checks, never rewrites what you staged. Bypass with `SKIP_HOOKS=1 git commit …`.

Tests are deliberately excluded — a hook slow enough to be bypassed enforces nothing.

It also prints the matching audit command (`npm audit`, `pip-audit`, `dotnet list package
--vulnerable`) when a staged path is a dependency manifest. These are **notices, not gates**: they
never fail the commit, because a real audit needs the network and would be bypassed on the first slow
day. A `pyproject.toml` only counts when it actually declares dependencies, so config-only ones (like
this repo's) stay quiet.

## Other languages

Python is the only language here with a configured formatter, linter, and tests. The rest have
tooling present but no repo-level command or config, so linting them is currently manual:

| Language | Tooling present                                               | Configured?              |
|----------|---------------------------------------------------------------|--------------------------|
| Shell    | `shellcheck` + `shfmt` (each its own ansible role)            | Command below, not gated |
| Lua      | `stylua` (installed by its own topic), `selene` (neovim role) | No repo-level command    |
| Ansible  | 31 roles under `_system/`                                     | No `ansible-lint`        |

Lint shell with:

```sh
git ls-files | grep -E '\.(sh|bash)$|^script/' | xargs shellcheck
```

The zsh files are excluded on purpose — shellcheck cannot parse zsh. The shipped `pre-commit` hook is
clean, but 14 findings (1 error, 4 warnings, 9 notes) remain in older `install.sh` scripts, so this is
**not** wired into `script/test` yet; doing that means fixing those first.

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
