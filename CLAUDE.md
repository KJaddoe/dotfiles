# dotfiles

## Project docs

Durable structural knowledge lives in `docs/`. `docs/` is **not** auto-loaded — consult it by
relevance; don't read it wholesale for trivial changes.

| Doc | Read when |
|-----|-----------|
| `docs/README.md` | Index of what's in `docs/` |
| `docs/architecture.md` | Touching the topic-folder layout, dotbot wiring, zsh loading, or `_system/` roles |
| `docs/decisions/` | Changing or questioning a setup decision (ADRs) |

Precedence: the actual config and `dotbot.conf.yaml` / `_system/main.yml` are the source of
truth; `docs/` can go stale — verify against them before relying, and fix docs that drift.
