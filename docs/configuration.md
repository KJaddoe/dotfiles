# Configuration

Environment variables this repo's own tooling reads. Reference material ("what"), deliberately
kept out of `architecture.md` (which is "why").

Nothing here is a secret, and nothing here should ever become one — record where a value lives,
never the value itself.

## Claude Code hooks

| Variable              | Purpose                                                              | Required | Default          | Example   |
|-----------------------|----------------------------------------------------------------------|----------|------------------|-----------|
| `DOCS_ENV_HOOK_MODE`  | Behaviour of the `undocumented-env-vars` Stop hook (`claude/hooks/`)  | No       | `dry-run`        | `enforce` |
| `CLAUDE_PROJECT_DIR`  | Project root the memory hook maps to a session dir                   | No       | current dir      | —         |

`CLAUDE_PROJECT_DIR` is **set by Claude Code itself**, not by you — don't export it. `pre-tool-memory.py`
reads it to derive the mapped session path (`/Users/you/Projects/foo` → `-Users-you-Projects-foo`) and
falls back to the working directory when it's absent, so the hook still works outside a Claude session.

`DOCS_ENV_HOOK_MODE` accepts:

| Value     | Behaviour                                                                              |
|-----------|----------------------------------------------------------------------------------------|
| `dry-run` | Default. Reports findings and appends them to `~/.claude/logs/env-doc-hook.log`; never blocks |
| `enforce` | Exits non-zero so the finding is fed back to the model for action                        |
| `off`     | No-op                                                                                    |

Set it wherever you export shell env (`zsh/`), or per-invocation for a one-off:

```sh
DOCS_ENV_HOOK_MODE=enforce claude
```

**Where the value comes from:** none needed — it's a local behaviour switch with a safe default,
not a credential. Start on `dry-run`, review the log, then flip to `enforce` once the findings
look right for your projects.

## Related

- `claude/hooks/undocumented-env-vars.py` — the hook itself; module docstring documents its contract
- `claude/hooks/tests/` — `python3 claude/hooks/tests/test_undocumented_env_vars.py`
- `~/.claude/CLAUDE.md` → **Project documentation** — the rule this hook enforces
