#!/usr/bin/env python3
"""PreToolUse(Bash) gate: a destructive or hard-to-reverse command needs explicit approval.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Working method):
before a DB restore/overwrite, a bulk file delete, a git history rewrite, or a migration against
a shared DB, state the plan, verify the target, and get explicit confirmation, "even for purely
local actions". Until this hook existed the permission prompt was doing that job silently, which
meant the rule held only in `default` mode and evaporated in `auto`.

Unlike `require-gh-approval`, this is a DENYLIST, and that is a deliberate concession rather than
an oversight: there is no enumerable set of "safe shell commands" to allowlist against. So this
gate is a safety net over the known-destructive set, not a boundary. It cannot be the only thing
standing between the model and the user's data, and it is not meant to be.

Because it cannot be complete, it errs toward gating: a false positive costs one approval, a false
negative costs work that git does not have.

Two kinds of text are data rather than commands, and both are removed before matching. Heredoc
bodies, matching the other guards, so writing a script or a .sql file that CONTAINS `DROP TABLE`
is not running one. And `echo`/`printf` arguments, because a progress line that NAMES a destructive
command is not one: the first live run of this hook blocked itself on its own `echo "... rm -rf
..."` banner. A printed string that is then piped into a shell is not covered by that carve-out,
but it is not covered by the denylist either, so nothing is lost by it.

Mode handling matches the commit, push and gh gates. See `approval_decision` in `_hookutil`:
prompt where a prompt renders, deny where it would be auto-approved, never allow.

Deliberately unconfigurable, with no env switch. An off-switch is the failure it exists to prevent.
"""

import re
import sys

from _hookutil import (
    GIT_FLAGS,
    SHELL_SEPARATORS,
    approval_decision,
    clip_summary,
    emit_decision,
    read_bash_payload,
    strip_heredocs,
)

# Confined to one command in a compound line, so a match cannot run past a `&&` or a pipe and
# pick up a flag that belongs to the next command.
SAME_COMMAND = r"[^&|;\n]*?"

DESTRUCTIVE = [
    (
        "delete files recursively or forcibly (rm)",
        re.compile(rf"\brm\b{SAME_COMMAND}\s-\S*[rRfF]"),
    ),
    (
        "delete files found by a search (find -delete / -exec rm)",
        re.compile(rf"\bfind\b{SAME_COMMAND}\s(-delete\b|-exec\s+rm\b)"),
    ),
    (
        "overwrite a file or device (dd)",
        re.compile(rf"\bdd\b{SAME_COMMAND}\sof="),
    ),
    (
        "irrecoverably overwrite a file (shred)",
        re.compile(r"\bshred\b"),
    ),
    (
        "format a filesystem (mkfs)",
        re.compile(r"\bmkfs(\.\w+)?\b"),
    ),
    (
        "discard every uncommitted change (git reset --hard)",
        re.compile(rf"\bgit\b{GIT_FLAGS}\s+reset\b{SAME_COMMAND}\s--hard\b"),
    ),
    (
        "delete untracked files (git clean -f)",
        re.compile(rf"\bgit\b{GIT_FLAGS}\s+clean\b{SAME_COMMAND}\s-\S*[fF]"),
    ),
    (
        "discard changes in the working tree (git checkout -- / git restore)",
        re.compile(
            rf"\bgit\b{GIT_FLAGS}\s+(checkout\s+(\S+\s+)?--\s"
            rf"|restore\b(?!{SAME_COMMAND}\s--staged\b))"
        ),
    ),
    (
        "rewrite history (git rebase)",
        re.compile(rf"\bgit\b{GIT_FLAGS}\s+rebase\b"),
    ),
    (
        "rewrite every commit (git filter-branch / filter-repo)",
        re.compile(rf"\bgit\b{GIT_FLAGS}\s+filter-(branch|repo)\b"),
    ),
    (
        "discard recovery data (git reflog expire / gc --prune)",
        re.compile(rf"\bgit\b{GIT_FLAGS}\s+(reflog\s+expire\b|gc\b{SAME_COMMAND}\s--prune)"),
    ),
    (
        "force-delete a branch (git branch -D)",
        re.compile(rf"\bgit\b{GIT_FLAGS}\s+branch\b{SAME_COMMAND}\s-\S*D"),
    ),
    (
        "delete a tag or a ref (git tag -d / update-ref -d)",
        re.compile(rf"\bgit\b{GIT_FLAGS}\s+(tag\b{SAME_COMMAND}\s-d\b|update-ref\s+-d\b)"),
    ),
    (
        "throw away stashed work (git stash drop / clear)",
        re.compile(rf"\bgit\b{GIT_FLAGS}\s+stash\s+(drop|clear)\b"),
    ),
    (
        "drop a table, database or schema (SQL DROP)",
        re.compile(r"\bdrop\s+(table|database|schema|index|view)\b", re.IGNORECASE),
    ),
    (
        "empty a table (SQL TRUNCATE)",
        re.compile(r"\btruncate\s+(table\b|\w+\s*;)", re.IGNORECASE),
    ),
    (
        "delete rows (SQL DELETE FROM)",
        re.compile(r"\bdelete\s+from\b", re.IGNORECASE),
    ),
    (
        "restore over an existing database",
        re.compile(r"\b(pg_restore|mongorestore|mysqldump\s+.*\|)\b"),
    ),
    (
        "flush a Redis database",
        re.compile(r"\bflush(all|db)\b", re.IGNORECASE),
    ),
    (
        "run a database migration",
        re.compile(
            r"\b(dotnet\s+ef\s+database\s+(update|drop)"
            r"|alembic\s+(upgrade|downgrade)"
            r"|prisma\s+migrate\s+(deploy|reset)"
            r"|flyway\s+(migrate|clean)"
            r"|rails\s+db:(migrate|drop|reset)"
            r"|artisan\s+migrate)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "change or tear down infrastructure (terraform)",
        re.compile(r"\bterraform\s+(apply|destroy)\b"),
    ),
    (
        "delete a Kubernetes resource (kubectl delete)",
        re.compile(rf"\bkubectl\b{SAME_COMMAND}\sdelete\b(?![^&|;\n]*--dry-run)"),
    ),
    (
        "remove a Helm release (helm uninstall / delete)",
        re.compile(r"\bhelm\s+(uninstall|delete)\b"),
    ),
    (
        "remove Docker volumes or prune (data loss)",
        re.compile(
            r"\bdocker\b[^&|;\n]*(\bvolume\s+rm\b|\bsystem\s+prune\b|\sdown\s[^&|;\n]*-\S*v)"
        ),
    ),
]


def strip_printed_text(cmd):
    """Return `cmd` with `echo` and `printf` segments removed.

    A banner naming a destructive command is data on its way to the terminal, the same way a
    heredoc body is data on its way to a program. Segments are split on the shell separators, so
    only the printing command is dropped and everything chained around it is still inspected.

    :param cmd: full shell command, heredoc bodies already stripped
    :return: the command with printing segments elided
    """
    kept = [
        segment
        for segment in SHELL_SEPARATORS.split(cmd)
        if not re.match(r"\s*(echo|printf)\b", segment)
    ]
    return "\n".join(kept)


def destructive_matches(cmd):
    """List what a shell command would destroy, by label.

    :param cmd: full shell command, heredoc bodies already stripped
    :return: list of labels for every destructive pattern present
    """
    return [label for label, pattern in DESTRUCTIVE if pattern.search(cmd)]


def destructive_summary(labels, cmd):
    """Summarise what the command would do, for the approval prompt.

    :param labels: the destructive actions detected
    :param cmd: full shell command, as the user would see it run
    :return: human-readable summary
    """
    actions = "\n".join(f"  - {label}" for label in labels)
    return clip_summary(
        f"This command would:\n{actions}\n\n"
        f"Full:   {cmd.strip()}\n\n"
        "Verify the target is the one you mean before approving. Much of this is not undoable, "
        "and what git can recover it can only recover from a commit that already exists."
    )


def main():
    """Turn a destructive invocation into an approval decision the user controls."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    code = strip_printed_text(strip_heredocs(cmd))
    labels = destructive_matches(code)
    if not labels:
        sys.exit(0)

    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "destructive command", destructive_summary(labels, cmd)))
    sys.exit(0)


if __name__ == "__main__":
    main()
