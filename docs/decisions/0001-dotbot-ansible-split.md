# ADR 0001: Split provisioning (Ansible) from config (Dotbot)

- Status: accepted
- Date: 2026-06-29

## Context

Setting up a machine has two distinct jobs: installing software (languages, CLIs, databases —
idempotent, needs root on Linux) and placing config files (symlink dotfiles into `$HOME` — no
root). Bundling both into one mechanism couples concerns that change at different rates and have
different privilege needs.

## Decision

Keep them separate. `_system/` (Ansible, `main.yml` + one role per tool) provisions software;
the topic folders + `dotbot.conf.yaml` (Dotbot) handle symlinks. `script/bootstrap` runs both,
but either can run alone.

Ownership boundary (tightened after roles had grown their own symlink tasks — `psqlrc` was
double-managed by both dotbot and the postgres role): **Dotbot is the sole owner of plain config
symlinks.** A role keeps a symlink only when it is inseparable from provisioning logic Dotbot
can't express — directory modes, conditional backup of a pre-existing file. The `ssh` role is
the lone such case (creates `~/.ssh` at `0700`, touches `config.local` at `0600`, backs up any
real `~/.ssh/config` before linking).

## Consequences

- Re-symlinking config (the common case) doesn't require running the heavier Ansible provision.
- Adding a tool is typically two edits: a topic folder linked via `dotbot.conf.yaml`, and a role
  in `_system/main.yml`.
- A plain config file is linked in exactly one place (`dotbot.conf.yaml`) — no drift between the
  two systems. Anything a role links must justify why it isn't a plain dotbot link.
- Two systems to learn instead of one; the boundary must be kept by convention.
