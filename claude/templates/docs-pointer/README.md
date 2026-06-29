# docs-pointer template

A repo-level `CLAUDE.md` that points Claude at a `docs/` folder for durable project knowledge,
plus a `docs/` skeleton. `CLAUDE.md` auto-loads; `docs/` does not — the pointer bridges them.

## Apply

1. Copy `CLAUDE.md.template` to the target repo root as `CLAUDE.md` (merge if one exists).
2. Copy `docs/` to the target repo root.
3. Replace `{Project Name}` and the `{...}` placeholders with real content; delete sections
   that don't apply (e.g. `erd.md` for non-DB projects).

Keep `CLAUDE.md` an index (what exists, when to consult it); put heavy content in `docs/`.
Favor "why" docs — rationale, cross-repo relations, ADRs — over what's reconstructable from code.
