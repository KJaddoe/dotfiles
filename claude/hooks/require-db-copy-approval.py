#!/usr/bin/env python3
"""PreToolUse(Bash) gate: backing up, restoring or copying a database needs the user's approval.

Local databases are tested in place: no backup first, no per-PR copy. See docs/configuration.md.
"""

import re
import sys

from _hookutil import approval_decision, clip_summary, emit_decision, read_bash_payload

RULE = "local databases are tested in place, never backed up or copied first"

# Heredoc bodies and printed text are scanned too: `sqlcmd <<SQL` and `echo ... | sqlcmd` run them.
STATEMENTS = re.compile(r"\b(?:BACKUP|RESTORE)\s+(?:DATABASE|LOG)\b", re.IGNORECASE)


def copy_statements(cmd):
    """List the backup and restore statements a command contains, in order, without repeats.

    :param cmd: full shell command
    :return: the statements, normalised to upper case with single spaces
    """
    found = [" ".join(match.group(0).upper().split()) for match in STATEMENTS.finditer(cmd)]
    return list(dict.fromkeys(found))


def copy_summary(statements, cmd):
    """Summarise what the command would do, for the approval prompt.

    :param statements: the statements detected
    :param cmd: full shell command, as the user would see it run
    :return: human-readable summary
    """
    return clip_summary(
        f"This command runs {', '.join(statements)}.\n\n"
        f"Full:   {cmd.strip()}\n\n"
        "Test on the database a copy would be made from. If it breaks, it breaks."
    )


def main():
    """Turn a backup or restore invocation into an approval decision the user controls."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    statements = copy_statements(cmd)
    if not statements:
        sys.exit(0)

    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "database copy", copy_summary(statements, cmd), RULE))
    sys.exit(0)


if __name__ == "__main__":
    main()
