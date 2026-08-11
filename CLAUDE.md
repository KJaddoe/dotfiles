# dotfiles

## Project docs

Durable structural knowledge lives in `docs/`. `docs/` is **not** auto-loaded — consult it by
relevance; don't read it wholesale for trivial changes.

| Doc | Read when |
|-----|-----------|
| `docs/README.md` | Index of what's in `docs/` |
| `docs/architecture.md` | Touching the topic-folder layout, dotbot wiring, zsh loading, or `_system/` roles |
| `docs/configuration.md` | Env vars this repo's own tooling reads (hook switches) |
| `docs/decisions/` | Changing or questioning a setup decision (ADRs) |

Precedence: the actual config and `dotbot.conf.yaml` / `_system/main.yml` are the source of
truth; `docs/` can go stale — verify against them before relying, and fix docs that drift.

## Conventions

- Keep macOS + Ubuntu/Linux parity; never introduce a mac-only assumption without a Linux path.
- Add a git config file by symlinking it into `$HOME` via a `link:` entry in `dotbot.conf.yaml` and
  point the git setting at the `~/.foo` home path (mirror `~/.gitignore`), not the in-repo path.
- A topic folder is not automatically a symlink. Link a config into `$HOME` only when the tool
  actually discovers it from there by searching upward (editorconfig, prettier). A tool that reads
  its config from the working directory only — `selene` — keeps it in its topic folder and gets
  `--config` passed explicitly; linking it to `~` would be dead config. Config that governs *this
  repo's own* sources rather than every project stays at the repo root (`pyproject.toml`,
  `.editorconfig`) and is not linked at all.
- Scripts and automation (ansible roles, dotbot, env/version pinning) must be idempotent and safe to
  re-run: guard on actual state rather than assumptions, and expect a re-run to be a no-op
  (`changed=0`).
