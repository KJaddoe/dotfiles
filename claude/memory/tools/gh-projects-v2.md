# GitHub Projects v2 (org boards) — gh/GraphQL gotchas

## Issue numbers collide across repos on a shared board (2026-07-21)

An org-level Project board holds items from **multiple repos**, and issue numbers are
per-repo — so the same `#N` can appear twice (e.g. `#14` exists in two different repos on the
board). Selecting a project item by `content.number` alone grabs the
first match and can hit the **wrong repo's issue**.

**Rule:** when resolving a project item ID, always disambiguate by repository, e.g.
`select(.content.number==14 and .content.repository.name=="<repo>")`. After ANY board
mutation, verify by reading the field back (this is how the wrong-item write above was caught).

## Field-mutation patterns

- Number field (e.g. Size): `updateProjectV2ItemFieldValue(... value:{number:3})`
- Iteration field (e.g. Sprint): `... value:{iterationId:"<id>"}` — get iteration IDs from
  the field's `configuration.iterations`; the *active* one = the iteration whose date range
  contains today.
- Clear a value (revert): `clearProjectV2ItemFieldValue(input:{projectId,itemId,fieldId})`.
- Need projectId + fieldId + itemId; fetch fields via `projectV2.fields`, items via
  `projectV2.items` (paginate with `--paginate`).

## PR↔issue linking on the board

Closing keywords (`Closes #n`) only create the board's linked-PR relationship when the PR
targets the repo's **default branch**. Stacked PRs (base = another feature branch) must be
linked manually via the issue's **Development** sidebar (UI-only, no API). See the relevant
project's memory note for the verified detail.
