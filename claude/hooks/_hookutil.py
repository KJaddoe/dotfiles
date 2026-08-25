#!/usr/bin/env python3
"""Git helpers and command patterns shared by the hooks in this directory.

The hooks keep needing the same handful of things: run a git command without letting a failure
escape, resolve the repository root for the session's cwd, and recognise a commit invocation —
and its short flags — inside a shell command. Each was duplicated across hooks before this
module existed.

Importing this works because Python puts a script's OWN directory at the front of `sys.path`,
and the hooks are invoked as `python3 ~/.claude/hooks/<name>.py` — so `~/.claude/hooks` leads
the path regardless of the cwd git happens to be run from. Loading a hook by file path instead
(`importlib.util.spec_from_file_location`, as the tests do) does NOT do that, so a caller taking
that route has to put this directory on `sys.path` itself.

The leading underscore marks it as internal to the hooks directory: it is not a hook, and
`settings.json` never invokes it.
"""

import re
import subprocess
from pathlib import Path

GIT_TIMEOUT_SECONDS = 8

GIT_FLAGS = r"(?:\s+-{1,2}[\w-]+(?:[= ]\S+)?)*"

COMMIT_SUBCOMMAND = re.compile(rf"\bgit\b{GIT_FLAGS}\s+commit\b", re.IGNORECASE)


def short_flag(cmd, letter):
    """Report whether `letter` is present as a short flag in `cmd`.

    Matches the bare flag and clustered forms (`-a`, `-am`, `-vam`) while ignoring long flags
    that merely contain the letter, so `--amend` does not read as `-a`. Matching is
    case-sensitive, keeping opposites like signing and sign-off distinct.

    :param cmd: full shell command
    :param letter: single flag letter to look for
    :return: True when the letter is present as a short flag
    """
    return bool(re.search(rf"(?<![\w-])-[A-Za-z]*{re.escape(letter)}[A-Za-z]*(?![\w-])", cmd))


def run_git(repo, *args):
    """Run a git command in `repo`, returning stdout or "" if git fails.

    :param repo: repository root path
    :param args: git arguments following the subcommand
    :return: decoded stdout, empty on any failure
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def repo_root(cwd):
    """Resolve the git repository root containing `cwd`.

    :param cwd: directory to resolve from
    :return: Path to the repo root, or None when not inside a git repo
    """
    top = run_git(cwd, "rev-parse", "--show-toplevel").strip()
    return Path(top) if top else None
