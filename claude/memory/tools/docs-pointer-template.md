# docs-pointer template

2026-06-29 — Added `claude/templates/docs-pointer/`: a reusable repo-level `CLAUDE.md` that
points at a `docs/` folder for durable project knowledge (architecture, cross-repo relations,
ADRs, optional ERD), since `CLAUDE.md` auto-loads but `docs/` doesn't. Design: `CLAUDE.md` stays
an index, heavy content in `docs/`, precedence clause = code wins / docs can go stale / verify
first. Trialled in this repo: root `CLAUDE.md` + `docs/` (architecture.md, decisions/0001).

Chose option 3 (static template now, YAGNI) over a scaffolding skill — it overlaps
claude-md-management. **Promotion trigger:** if the template gets copied into ~3+ repos, promote
it to a scaffolding skill in `claude/skills/` and turn this file into a pointer (mirror the
`gh-pending-pr-reviews.md` → `pending-pr-review` skill pattern).
