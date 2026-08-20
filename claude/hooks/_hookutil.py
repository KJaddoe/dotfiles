#!/usr/bin/env python3
"""Git helpers shared by the Stop hooks in this directory.

Every hook needs the same two things: run a git command without letting a failure escape, and
resolve the repository root for the session's cwd. They were duplicated byte-for-byte across
three hooks before this module existed.

Importing this works because Python puts a script's OWN directory at the front of `sys.path`,
and the hooks are invoked as `python3 ~/.claude/hooks/<name>.py` — so `~/.claude/hooks` leads
the path regardless of the cwd git happens to be run from. Loading a hook by file path instead
(`importlib.util.spec_from_file_location`, as the tests do) does NOT do that, so a caller taking
that route has to put this directory on `sys.path` itself.

The leading underscore marks it as internal to the hooks directory: it is not a hook, and
`settings.json` never invokes it.
"""

import subprocess
from pathlib import Path

GIT_TIMEOUT_SECONDS = 8


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
