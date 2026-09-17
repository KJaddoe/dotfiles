---
name: claude-code-skills
description: Skills fire on model judgment against their description, not on a guaranteed schedule; only CLAUDE.md and hooks are guaranteed to run every turn
metadata:
  type: reference
---

A Skill only loads when the model decides its description matches the current task; there is no
supported flag or config to force a custom skill to fire on every turn the way `~/.claude/CLAUDE.md`
is always injected as instructions.

The project's own `pre-tool-memory.py` (`claude/hooks/`) shows the actual guaranteed-injection
pattern: it runs as a SessionStart hook (plus a PreToolUse fallback for subagents, which don't get
SessionStart) and injects file contents as `additionalContext` directly, bypassing the Skill tool
entirely. That hook is deliberately scoped to FYI/facts only; the binding rules stay in CLAUDE.md.

**Why:** confirmed 2026-09-17 while deciding whether to move the whole `## Memory Management`
section (Structure + Rules + Maintenance) out of CLAUDE.md into a `reorganizing-memory` skill. The
always-on behaviors (write immediately, load the index at session start, route by type) had to stay
in CLAUDE.md; only the "reorganize memory" procedure, a discrete command-triggered task, moved to
the skill.

**How to apply:** when deciding whether a procedure belongs in CLAUDE.md/a hook versus a skill, the
test is whether it must fire on every relevant turn regardless of whether the model recognizes a
trigger (CLAUDE.md/hook), or is a discrete task invoked by an explicit ask or clear task shape
(skill). The `## Memory Management` → Maintenance split in `~/.claude/CLAUDE.md` is the worked
example: Structure/Rules stayed, the `reorganize memory` procedure moved to the `reorganizing-memory`
skill.
