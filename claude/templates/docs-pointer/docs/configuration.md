# Configuration

> Reference material ("what"), deliberately kept out of `architecture.md` (which is "why").

Record where a value lives — **never the value itself**. No real secrets here.

## Environment variables

| Variable | Purpose            | Required | Default         | Example            |
|----------|--------------------|----------|-----------------|--------------------|
| `{NAME}` | {what it controls} | {Yes/No} | {default, or —} | {safe placeholder} |

For each, state **where the real value comes from**: which vault/1Password item, cloud secret
store, who to ask, or `generate with {command}`. Two exceptions worth naming explicitly:

- **Set by the platform/harness, not you** — say so; "where it comes from" doesn't apply.
- **Local behaviour switches with safe defaults** — no provenance needed, say it in one clause.

## {Other config}

{Config files, feature flags, per-environment settings. Delete if none.}
