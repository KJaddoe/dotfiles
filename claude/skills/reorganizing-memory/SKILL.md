---
name: reorganizing-memory
description: Use when asked to reorganize, clean up, dedupe, or audit the ~/.claude/memory/ system, or when the user says "reorganize memory".
---

# Reorganizing Memory

Runs the periodic cleanup pass over the structured memory system at `~/.claude/memory/` (file
layout: see the Structure section in `~/.claude/CLAUDE.md`).

## Steps

1. Read all memory files (`memory.md`, `general.md`, `domain/*.md`, `tools/*.md`).
2. Remove duplicates and outdated entries.
3. Merge entries that belong together.
4. Split files that cover too many topics.
5. Re-sort entries by date within each file.
6. Update the `memory.md` index.
7. Show a summary of what changed.

## Rules while reorganizing

- Before removing or modifying any existing entry, confirm with AskUserQuestion: show the current
  content and the proposed change.
- Run the Auto-Memory Staging promotion pass too (see `~/.claude/CLAUDE.md`): a per-project
  auto-memory entry that duplicates a global `~/.claude/memory/` file shrinks to a pointer or is
  removed.
- Apply the Domain Knowledge Lifecycle (see `~/.claude/CLAUDE.md`): a domain file with enough
  accumulated content to package as a plugin/skill gets promoted, and becomes a pointer once
  promoted.
