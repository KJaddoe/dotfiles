# GitHub Projects v2 (org boards) — gh/GraphQL gotchas

## Issue numbers collide across repos on a shared board (2026-07-21)

An org-level Project board holds items from **multiple repos**, and issue numbers are
per-repo — so the same `#N` can appear twice (e.g. `#14` exists in two different repos on the
board). Selecting a project item by `content.number` alone grabs the
first match and can hit the **wrong repo's issue**.

**Rule:** when resolving a project item ID, always disambiguate by repository, e.g.
`select(.content.number==14 and .content.repository.name=="<repo>")`. After ANY board
mutation, verify by reading the field back (this is how the wrong-item write above was caught).

## Status = Done AUTO-CLOSES the issue (verified 2026-08-17)

Setting a board item's Status to **Done** closes the underlying GitHub issue immediately — the
board write and the issue state are not independent. Never set Done to mean merely "the code
merged" unless the issue should genuinely close; an issue that must stay open for a follow-up
(a guard that hasn't landed, criteria not yet verified) will be closed out from under you.

Undoing it takes **two** steps, not one: `gh issue reopen <n>` **and** restoring the board Status.
Reopening alone leaves the board showing Done.

The reverse also happens: closing an issue moves its board item to Done by **automation**, so no
manual field write is needed after a `Closes #n` merge. Check the item before mutating it.

## An item stays invisible until its Sprint is set (learned 2026-08-17)

Status alone is not enough to make an item appear on a working board view — the view filters on
the **Sprint** iteration field. An item created with labels, milestone, epic link and Status but
no Sprint is on the board and findable by nobody. After `gh project item-add` + Status, also set
the Sprint iteration and propose a Size.

## Status option ids are shared across boards

The Status single-select option ids turn out to be **identical across different org boards**
(verified on three). So an option id read once can be reused on another board — but do NOT infer
the same for **project** or **field** ids, which are per-board. The literal ids live in each
project's own (untracked) memory, not here.

## Field-mutation patterns

- Number field (e.g. Size): `updateProjectV2ItemFieldValue(... value:{number:3})`
- Iteration field (e.g. Sprint): `... value:{iterationId:"<id>"}` — get iteration IDs from
  the field's `configuration.iterations`; the *active* one = the iteration whose date range
  contains today.
- Clear a value (revert): `clearProjectV2ItemFieldValue(input:{projectId,itemId,fieldId})`.
- Need projectId + fieldId + itemId; fetch fields via `projectV2.fields`, items via
  `projectV2.items` (paginate with `--paginate`).
- Assignee/label are **issue** fields, not board fields: set them with `gh issue edit`, which fails
  **silently** on an unresolvable value (exit 0, nothing assigned) — see `github-accounts.md`. The
  read-back rule above applies to these too, and they are easy to miss because the board mutation
  beside them fails loudly.

## PR↔issue linking on the board

Closing keywords (`Closes #n`) only create the board's linked-PR relationship when the PR
targets the repo's **default branch**. Stacked PRs (base = another feature branch) must be
linked manually via the issue's **Development** sidebar (UI-only, no API). See the relevant
project's memory note for the verified detail.
