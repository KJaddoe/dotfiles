# docs/

Durable "why" knowledge for this dotfiles repo — how the pieces fit and why, beyond what a
single config file shows. Keep entries scoped; link to the real files rather than copying them.

| File | Contents | Read when |
|------|----------|-----------|
| `architecture.md` | The two halves (dotbot symlinks + `_system` Ansible), topic-folder conventions, zsh load order, and the recipe for adding a tool / vendor apt repo | Working in an unfamiliar area, or adding a tool/role |
| `configuration.md` | Env vars this repo's own tooling reads, and what they switch | Changing hook behaviour, or adding a tool that reads config |
| `decisions/` | ADRs — one file per setup decision, newest wins | Changing or questioning a design choice |

Precedence: config wins over docs. Treat anything here as possibly stale; verify before relying.
