# Memory Index

Read this file at session start. Load specific topic files only when relevant.

| File | Description | Last updated |
|------|-------------|--------------|
| `general.md` | Cross-project conventions and preferences (commit/PR/branch/review rules, code style) | 2026-06-01 |
| `tools/gh-pending-pr-reviews.md` | Pointer — promoted to the `pending-pr-review` skill (`claude/skills/`) | 2026-06-01 |
| `tools/docker-sql-server.md` | Local Docker SQL Server: backups live in `~/Projects/Docker/SQL_Server/backups/` (mounted `/var/opt/mssql/backup`); restore to original DB name; suggest DROP when done | 2026-06-07 |
| `domain/mise-migration.md` | In-progress: migrating node/python/ruby/java to mise (+uv for python tooling), then CLI-only RN Android. Done: mise/java/node/python. Remaining: ruby, cleanup, Android, RN device verify. Resume point + gotchas inside. | 2026-06-10 |

## Cross-Memory Sync Rule

At session start, after reading this file:
1. Note the Last updated dates in the table above
2. Check projects.md (if it exists) for active project MEMORY.md paths
3. If any project MEMORY.md has content worth promoting to a global tools/ or domain/ file, flag it
4. Update the Last updated date on this file after any changes

## Domain Knowledge Lifecycle

1. Staging — knowledge accumulates in domain/{name}/
2. Promotion — enough knowledge exists to package as a plugin/skill
3. Pointer — after promotion, the memory file becomes a pointer to the plugin
