# gh + GraphQL: incrementally building a pending PR review

How to walk through PR findings one at a time, attaching each as an inline comment to a single *pending* review, then submit once the user approves. The naive REST path doesn't work — record this workflow once so we don't rediscover it.

**Verified 2026-05-27** against a private repo PR.

## Why the obvious REST path fails

`POST /repos/{owner}/{repo}/pulls/{n}/comments` looks like the right endpoint to add a single inline comment, but it implicitly tries to create its own pending review. If a pending review already exists for the same user on the same PR, it fails with:

```
422 Validation Failed
"user_id can only have one pending review per pull request"
```

There is **no** `POST /repos/{owner}/{repo}/pulls/{n}/reviews/{review_id}/comments` REST endpoint either — confirmed against the docs.

## The working workflow

### 1. Create the pending review (REST)

```bash
gh api -X POST repos/{OWNER}/{REPO}/pulls/{N}/reviews --input review-init.json
```

`review-init.json`:
```json
{
  "commit_id": "<HEAD SHA of the PR>",
  "body": "<placeholder or initial summary>",
  "comments": [ /* optional first comment(s) */ ]
}
```

Omit `event` → the review stays in `PENDING` state. Capture the returned `id` (this is the REST `databaseId`).

### 2. Convert the REST review id → GraphQL node id

```bash
gh api graphql -f query='
{
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: N) {
      reviews(first: 10, states: [PENDING]) {
        nodes { id databaseId }
      }
    }
  }
}'
```

Match the `databaseId` to your review and grab the `id` (e.g. `PRR_kwDOO3FE2s8AAAABBKc1qQ`).

### 3. Append comments via `addPullRequestReviewThread` (GraphQL)

The deprecated `addPullRequestReviewComment` only takes `position` (diff-line index), so it can't do `line` / `startLine` / `side` / `startSide` and can't render multi-line suggestions cleanly. Use `addPullRequestReviewThread`:

```graphql
mutation AddThread($body: String!) {
  addPullRequestReviewThread(input: {
    pullRequestReviewId: "PRR_...",
    path: "path/to/file.sql",
    body: $body,
    line: 127,
    side: RIGHT,
    # for multi-line, also:
    startLine: 120,
    startSide: RIGHT,
    subjectType: LINE
  }) {
    thread { id comments(first: 1) { nodes { databaseId url } } }
  }
}
```

Invoke:
```bash
BODY=$(cat comment-body.txt) && \
  gh api graphql -F query=@add-thread.graphql -F body="$BODY"
```

Pass the body through `-F` from a shell variable (loaded from a file) so backticks and ```` ```suggestion ```` fences survive escaping. Inlining a long body string in `-f` arguments will eat your code fences.

### 4. (Optional) Update the summary body before submission

```bash
gh api -X PUT repos/{OWNER}/{REPO}/pulls/{N}/reviews/{REVIEW_ID} -f body="$NEW_BODY"
```

The summary stays PENDING — only the body text changes.

### 5. Submit

```bash
gh api -X POST repos/{OWNER}/{REPO}/pulls/{N}/reviews/{REVIEW_ID}/events \
  -f event=REQUEST_CHANGES   # or COMMENT, APPROVE
```

Returns the review with `state: CHANGES_REQUESTED` (or matching state) and `submitted_at`.

**Only do this after the user explicitly approves** — see `general.md` "Code Review Workflow".

## Common pitfalls

- Using REST `POST .../pulls/{n}/comments` after the pending review exists → `422 user_id can only have one pending review per pull request`. Use GraphQL instead.
- Passing the REST `databaseId` (integer) as `pullRequestReviewId` to GraphQL → error. You need the node ID (string, e.g. `PRR_...`).
- Inlining a multi-line body with backticks via `-f body="..."` → quoting hell, suggestion fences get mangled. Use a file + shell variable + `-F`.
- Forgetting `subjectType: LINE` when you want a line comment (the default for some shapes is `FILE`).
