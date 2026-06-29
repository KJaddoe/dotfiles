# docs/

Durable "why" knowledge for {Project Name} — the things that can't be reconstructed by reading
the code. Keep entries scoped and link out rather than duplicating code.

| File | Contents | Read when |
|------|----------|-----------|
| `architecture.md` | Structure, components, data flow, cross-repo relations | Working in an unfamiliar area |
| `decisions/` | ADRs — one file per decision, newest wins | Changing or questioning a design choice |
| `erd.md` | (DB projects) entity-relationship map | Touching the schema — verify against migrations |

Precedence: code wins over docs. Treat anything here as possibly stale; verify before relying.
