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
  `CLAUDE.md`, `hooks/`, `memory/`, `skills/`, `keybindings.json`). The repo-root `CLAUDE.md`
  (this trial) is separate: it is repo-level project instructions, not the global config.

## Cross-repo / external relations

- **Antidote** manages zsh plugins from `antidote/zsh_plugins.txt`; **Powerlevel10k** is the
  prompt (`powerlevel10k/p10k.zsh`).
- **Dotbot** is a git submodule (`dotbot/`).
- Per-machine secrets/overrides stay out of the repo: `~/.localrc` (shell), `~/.gitconfig`
  (includes the managed one), `~/.ssh/config.local`.

## Conventions worth knowing

- **mac/Linux parity** — every change must work on both; never add a mac-only assumption without
  a Linux path. Ansible keys off `ansible_pkg_mgr` (`brew` vs not).
- Adding a tool is usually two edits: a topic folder (config, linked via `dotbot.conf.yaml`) and
  an `_system/roles/<tool>/` role added to `_system/main.yml` (install).
