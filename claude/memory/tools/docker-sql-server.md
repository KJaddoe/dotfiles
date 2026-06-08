# Tool: Docker SQL Server (local restores)

Local SQL Server runs in Docker: dir `~/Projects/Docker/SQL_Server` (compose.yml), container `mssql-db`, `sa` / `!StrongPassword123`, port 1433. Query:
`docker exec mssql-db /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P '!StrongPassword123' -C -N -d <db> -W -s "~" -Q "..."`

## Backups always live in the mounted backups folder
- 2026-06-07 — **All `.bak` files must live in `~/Projects/Docker/SQL_Server/backups/`**, which is bind-mounted into the container at `/var/opt/mssql/backup` (line in compose.yml: `- ./backups:/var/opt/mssql/backup`). Why: a `.bak` outside a mounted path is invisible to the container and cannot be restored without first copying it in. Keeping them here also survives container recreates (the bind mount persists).
- **If a backup to restore is anywhere else (Desktop, Downloads, a server copy, etc.), recommend moving it into `~/Projects/Docker/SQL_Server/backups/` first** rather than copying it ad-hoc into `data/`. Move, don't duplicate, so there's a single source of truth.

## Restore conventions
- 2026-06-07 — **Restore each backup to the same database name it had on the server it came from** (its original DB name), not an ad-hoc local name.
- 2026-06-07 — **Always suggest `DROP DATABASE <name>` once we're done** with a restored DB, to reclaim space.
