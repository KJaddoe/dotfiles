# Memory Index

Read this file at session start. Load specific topic files only when relevant.

| File | Description | Last updated |
|------|-------------|--------------|
| `general.md` | Cross-project conventions and preferences (commit/PR/branch/review rules, code style, mac/linux parity, generated-specs-stay-out-of-repo, GitHub issue status→To Be Refined) | 2026-06-23 |
| `tools/gh-pending-pr-reviews.md` | Pointer — promoted to the `pending-pr-review` skill (`claude/skills/`) | 2026-06-01 |
| `tools/zsh-startup.md` | zsh startup perf: single-compinit architecture in `zsh/zshrc` (fpath→compinit→aliases→completion order), ng-completion caching. Cut ~2.1s→~0.35s. | 2026-06-11 |
| `tools/docker-sql-server.md` | Local Docker SQL Server: backups live in `~/Projects/Docker/SQL_Server/backups/` (mounted `/var/opt/mssql/backup`); restore to original DB name; suggest DROP when done | 2026-06-07 |
| `tools/macos-doc-conversion.md` | docx/md/pdf conversion: `textutil` drops images → use headless Chrome `--print-to-pdf` (abs `file://` paths) or `brew install pandoc`; md→pdf via python-markdown; extract docx images with `unzip word/media/*` | 2026-06-17 |
| `tools/docs-pointer-template.md` | `claude/templates/docs-pointer/` — repo `CLAUDE.md`→`docs/` pointer template (index + precedence). Trialled in this repo. Promote to a skill if copied to ~3+ repos. | 2026-06-29 |
| `domain/mise-migration.md` | COMPLETE: migrated node/python/ruby/java to mise (+uv), Brewfile cleanup, Android SDK/watchman roles, neovim role, RN Android verified CLI-only on a physical phone. Gotchas/resume notes retained. | 2026-06-11 |

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
