# Two GitHub identities — which tool picks which

Two accounts are configured: a **personal** one and an **org** one (the org account is the member of
the company org). Different tools resolve the identity differently, which is why the same repo can
be pushable and unreadable at the same time.

Promoted to global memory 2026-08-17 — these facts had been independently rediscovered in three
separate project memories.

## The split that causes the confusion

| Tool        | Picks identity via                     | Failure when it picks wrong                                     |
|-------------|----------------------------------------|-----------------------------------------------------------------|
| `gh` CLI    | the currently-active auth user         | `Could not resolve to a Repository` / 404 on a repo that exists |
| `git` (SSH) | the SSH key selected by the host alias | `Repository not found` on push/clone                            |

Because they are independent, **a push can succeed while `gh pr create` 404s on the same repo** —
git used the right key, `gh` used the wrong token. Don't read that as a permissions bug on the repo.

## gh

Switch before working in a repo owned by the other identity:

```bash
gh auth switch --user <account>
```

Only the org account can create issues in the org (the personal one can read but not write), and it
is the one carrying the `project` scope needed for Projects v2 board mutations. Switch back
afterwards if the next repo belongs to the other account.

## git over SSH

Org repos must use the **host alias**, not plain `github.com`:

```text
git@<host-alias>:<org>/<repo>.git   # correct — uses the org key
git@github.com:<org>/<repo>.git     # wrong — uses the personal key → "Repository not found"
```

The alias and the identity file it points at are defined in the untracked `~/.ssh/config.local` —
read the real alias name there. When cloning or adding a remote for an org repo, set the alias form
deliberately; `gh repo clone` will not do it.

## Symptom → cause

- 404 from `gh` on a repo you can see in the browser → wrong active `gh` account.
- "Repository not found" on `git push` → remote uses plain `github.com:` instead of the alias.
- Can push but `gh` 404s → both of the above at once; they are separate fixes.
