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

## The GitHub login is not the git author name (2026-08-18)

`git config user.name` — and the "Git user:" line in a session's environment context — is a
**display name for commit authorship**, not a GitHub login. With two accounts the org one's login
typically carries a suffix the commit name does not.

The trap is worse than a name that simply does not exist. Corrected 2026-08-18: the commit author
name matched the **personal** account's real login exactly. So the guessed name resolved to a
genuine GitHub user — it was just not a collaborator on the org repo, and **assignability is
per-repository**. A wrong-but-real login is indistinguishable from a right one until you check it
against the repo.

Either way the failure is **silent**:

> `gh issue edit --add-assignee <login>` exits **0**, prints the issue URL, and assigns nobody.

GitHub's REST API drops assignees it cannot resolve *on that repo* instead of erroring;
`--add-label` does the same for a label that does not exist. An `&&` chain therefore carries
straight on as though it worked, and the board looks set while the field is empty.

```bash
gh api user -q .login                         # the login of the ACTIVE gh account
gh api repos/<org>/<repo>/assignees/<login>   # 404 = not assignable HERE, so it will be dropped
gh issue view <n> --json assignees            # read back — the only proof it landed
```

Note the middle check is repo-scoped on purpose: a login that is valid globally still 404s here if
that account is not a collaborator.

**How to apply:** never infer a GitHub login from git config, a commit author, or session context —
resolve it with `gh api user -q .login`. After any `gh issue edit` write, read the field back. Exit
code 0 is not evidence here.

## Symptom → cause

- 404 from `gh` on a repo you can see in the browser → wrong active `gh` account. **The active
  account can change mid-session**: calls that worked earlier in the same shell later failed with
  `Could not resolve to a Repository` (2026-08-18). Re-check `gh auth status` on a sudden 404
  rather than assuming permissions changed.
- "Repository not found" on `git push` → remote uses plain `github.com:` instead of the alias.
- Can push but `gh` 404s → both of the above at once; they are separate fixes.
- `gh issue edit` reported success but the assignee/label is empty → the value was unresolvable and
  was silently dropped; check the login with `gh api user -q .login`.
