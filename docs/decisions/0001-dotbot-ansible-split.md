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

## Consequences

- Re-symlinking config (the common case) doesn't require running the heavier Ansible provision.
- Adding a tool is typically two edits: a topic folder linked via `dotbot.conf.yaml`, and a role
  in `_system/main.yml`.
- Two systems to learn instead of one; the split must be kept in sync by convention.
