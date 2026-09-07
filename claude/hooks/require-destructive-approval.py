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
..."` banner. A command that pipes into a shell keeps its printed text, because there the string
is what executes.

The overwrite check below runs on the text with heredocs stripped but printing INTACT, because
dropping an `echo` segment drops its redirect with it, and `echo "" > live.conf` empties a file
whatever is on the left of the `>`. Reading redirects from the lexer is what makes that safe: a
`>` inside a quoted argument stays inside its token and is never seen as an operator.

Overwriting in place is the one class this gate cannot answer from the command text alone. A `>`
redirect and a `cp` destroy nothing when the destination is new and destroy everything when it is
not, and the same two characters do both. Matching them by text would either gate every redirect
in the session or none of them, so these two are decided by STATTING the destination: an existing
file gates, a new path does not. Scratch trees (`/tmp`, `$TMPDIR`, macOS `/var/folders`) are
carved out, since nothing there is worth an approval prompt. A destination the text cannot
resolve, behind a variable or a glob, fails closed. Redirect targets are read from the lexer
rather than by regex, so a `>` inside a quoted argument is not mistaken for one.

Mode handling matches the commit, push and gh gates. See `approval_decision` in `_hookutil`:
prompt where a prompt renders, deny where it cannot, never allow.

Deliberately unconfigurable, with no env switch. An off-switch is the failure it exists to prevent.
"""

import os
import re
import sys
from pathlib import Path

from _hookutil import (
    GIT_FLAGS,
    approval_decision,
    clip_summary,
    command_directory,
    command_segments,
    emit_decision,
    read_bash_payload,
    strip_heredocs,
    strip_printed_text,
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
    (
        "rewrite a file in place (sed -i / perl -i)",
        re.compile(
            rf"\b(sed|perl)\b{SAME_COMMAND}"
            rf"\s(-[A-Za-z]*i(\.\S*)?|--in-place(=\S*)?)(?=[\s'\"]|$)"
        ),
    ),
    (
        "shrink or empty a file (truncate)",
        re.compile(rf"\btruncate\b{SAME_COMMAND}\s(-s|--size)[=\s]*(?!\+)\d"),
    ),
    (
        "change permissions or ownership recursively (chmod -R / chown -R)",
        re.compile(rf"\bch(mod|own|grp)\b{SAME_COMMAND}\s(-\S*R\b|--recursive\b)"),
    ),
]

# `>>` appends and `&>>` appends both streams, so neither empties what is already there.
TRUNCATING_REDIRECTS = {">", ">|", "&>"}

REDIRECTS = TRUNCATING_REDIRECTS | {">>", "&>>", "<", "<<", "<<<"}

# Writing to a stream device destroys nothing.
DEVICE_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty", "/dev/fd/1", "/dev/fd/2"}

SCRATCH_ROOTS = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")

# A destination the command text cannot resolve: a variable, a substitution, or a glob.
UNRESOLVABLE_PATH = re.compile(r"[$`*?]")


def in_scratch(path):
    """Report whether a path lives in a tree kept for throwaway files.

    :param path: resolved destination path
    :return: True when the path sits under a temporary directory
    """
    roots = [*SCRATCH_ROOTS, os.environ.get("TMPDIR", "")]
    return any(root and str(path).startswith(root.rstrip("/") + "/") for root in roots)


def already_there(path):
    """Report whether a destination path already holds something.

    An unreadable path answers True: a destination that cannot be checked is treated as occupied,
    the same way an unresolvable one is.

    :param path: resolved destination path
    :return: True when something exists at the path
    """
    try:
        return path.exists()
    except OSError:
        return True


def occupied_destination(target, base):
    """Resolve a write destination and report it when writing there would land on something.

    :param target: the path as written in the command
    :param base: the directory the command acts in
    :return: the resolved path as text, or "" when nothing would be overwritten
    """
    if UNRESOLVABLE_PATH.search(target):
        return target

    path = Path(target).expanduser()
    path = path if path.is_absolute() else base / path
    if in_scratch(path) or not already_there(path):
        return ""
    return str(path)


def truncated_files(segments, base):
    """List existing files a truncating redirect would empty.

    :param segments: the command's token lists
    :param base: the directory the command acts in
    :return: list of destinations that already exist
    """
    hits = []
    for tokens in segments:
        for index, token in enumerate(tokens[:-1]):
            if token not in TRUNCATING_REDIRECTS or tokens[index + 1] in DEVICE_TARGETS:
                continue
            hit = occupied_destination(tokens[index + 1], base)
            if hit:
                hits.append(hit)
    return hits


def copied_over_files(segments, base):
    """List existing files a `cp` would overwrite.

    A destination DIRECTORY is not itself overwritten, so what matters there is what each source
    would land on inside it.

    :param segments: the command's token lists
    :param base: the directory the command acts in
    :return: list of destinations that already exist
    """
    hits = []
    for tokens in segments:
        if tokens[0] != "cp":
            continue

        stop = next((at for at, token in enumerate(tokens) if token in REDIRECTS), len(tokens))
        paths = [token for token in tokens[1:stop] if not token.startswith("-")]
        if len(paths) < 2:
            continue

        sources, destination = paths[:-1], paths[-1]
        if UNRESOLVABLE_PATH.search(destination):
            hits.append(destination)
            continue

        target = Path(destination).expanduser()
        target = target if target.is_absolute() else base / target
        if in_scratch(target):
            continue

        if not target.is_dir():
            hits.extend([str(target)] if already_there(target) else [])
        elif any(UNRESOLVABLE_PATH.search(source) for source in sources):
            hits.append(str(target))
        else:
            landings = [target / Path(source).name for source in sources]
            hits.extend(str(landing) for landing in landings if already_there(landing))
    return hits


def overwrite_matches(cmd, base):
    """List what a command would overwrite in place, by label.

    :param cmd: full shell command, heredoc bodies and printed text already stripped
    :param base: the directory the command acts in
    :return: list of labels, each naming the file that already exists
    """
    segments = command_segments(cmd)
    return [
        f"{action}: {path}"
        for action, paths in (
            ("empty an existing file (> redirect)", truncated_files(segments, base)),
            ("overwrite an existing file (cp)", copied_over_files(segments, base)),
        )
        for path in paths
    ]


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

    written = strip_heredocs(cmd)
    code = strip_printed_text(written)
    base = command_directory(code, data.get("cwd") or ".")
    labels = destructive_matches(code) + overwrite_matches(written, base)
    if not labels:
        sys.exit(0)

    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "destructive command", destructive_summary(labels, cmd)))
    sys.exit(0)


if __name__ == "__main__":
    main()
