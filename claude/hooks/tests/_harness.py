#!/usr/bin/env python3
"""Shared machinery for the hook test suites: how a hook is loaded, invoked and fixtured.

Every suite used to carry its own copy of all three. That is where pylint's duplicate-code
warnings came from, and it is also what made the suite slow: each copy spawned a fresh
interpreter per case, and the two fixture-heavy suites rebuilt a git repository per case on top
of that. Measured, those two accounted for half the suite's wall clock from a twelfth of its
tests.

A hook is therefore invoked in THIS process by default, and `run_standalone` is kept only for
the cases that are about being run as a program.

The git fixture is likewise built ONCE per baseline and copied per test rather than rebuilt.
`git init` plus a config plus a commit is five subprocesses; a copy of the finished tree is one
filesystem walk, and it leaves each test with the same untouched repository it had before.

Not a test module itself, and named to match `_hookutil.py`: the leading underscore says it is
imported, never run.
"""

import atexit
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]

# Loading a hook by file path does not put the hooks directory on sys.path, so its own
# `from _hookutil import ...` would fail without this.
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

GIT_TIMEOUT_SECONDS = 30

# Literal copies of _hookutil's, on purpose: a test that read the constant it is checking would
# pass whatever the hook was later changed to say.
# Measured: a hook's "ask" renders a dialog in all four prompting modes. See ADR 0005.
PROMPTING_MODES = ["default", "plan", "auto", "acceptEdits"]
NON_PROMPTING_MODES = ["dontAsk", "bypassPermissions"]
ALL_MODES = PROMPTING_MODES + NON_PROMPTING_MODES

# Field names match subprocess.CompletedProcess, so a suite moving off run_standalone keeps its
# existing assertions.
HookRun = namedtuple("HookRun", "returncode stdout stderr")

_TEMPLATES = {}


def load_hook(filename):
    """Import a hook module by its kebab-case filename.

    :param filename: the hook's filename, such as "require-push-approval.py"
    :return: the imported module
    """
    path = HOOKS_DIR / filename
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke(module, payload):
    """Run a loaded hook's `main` in this process, feeding it `payload` as stdin.

    Spawning an interpreter per case cost roughly 45ms, more than every hook body put together.
    Reusing one module across a suite is safe only because each hook's module-level state is
    read-only lookup tables; a hook that started caching would need a fresh load per case.

    :param module: a module returned by `load_hook`
    :param payload: the hook payload to feed it
    :return: a HookRun carrying the exit code and both captured streams
    """
    out, err = io.StringIO(), io.StringIO()
    real_stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps(payload))
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                module.main()
                code = 0
            except SystemExit as exit_call:
                code = exit_call.code or 0
    finally:
        sys.stdin = real_stdin
    return HookRun(code, out.getvalue(), err.getvalue())


def bash_decision(module, command, mode="default", tool="Bash", cwd=None):
    """Ask a Bash approval gate what it would decide about `command`.

    :param module: a module returned by `load_hook`
    :param command: the shell command the model would run
    :param mode: permission mode to report as the session's
    :param tool: tool name to report, for the cases checking a gate ignores other tools
    :param cwd: working directory to report, or None for this process's own
    :return: the hookSpecificOutput dict, or None when the gate stayed silent
    """
    stdout = invoke(
        module,
        {
            "tool_name": tool,
            "tool_input": {"command": command},
            "permission_mode": mode,
            "cwd": cwd or str(Path.cwd()),
        },
    ).stdout
    if not stdout.strip():
        return None
    return json.loads(stdout)["hookSpecificOutput"]


def run_standalone(filename, *args, stdin="", env=None):
    """Run a hook the way the harness does, as its own process.

    Kept for the tests that are ABOUT standalone invocation: a `--path` run, or the import that
    only fails when the file is executed from outside its own directory.

    :param filename: the hook's filename
    :param args: command-line arguments to pass
    :param stdin: text to feed the process
    :param env: environment to run under, or None for this process's own
    :return: the CompletedProcess
    """
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / filename), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )


def git(repo, *args):
    """Run a git command in `repo`, raising on failure.

    :param repo: repository path
    :param args: git arguments
    """
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )


def template_repo(baseline):
    """Build, once, a pristine repository holding one committed baseline file.

    :param baseline: (filename, contents) pair to commit
    :return: path to the template, which callers copy rather than modify
    """
    if baseline not in _TEMPLATES:
        path = Path(tempfile.mkdtemp())
        atexit.register(shutil.rmtree, path, ignore_errors=True)
        git(path, "init", "-q")
        git(path, "config", "user.email", "test@example.com")
        git(path, "config", "user.name", "test")
        (path / baseline[0]).write_text(baseline[1])
        git(path, "add", "-A")
        git(path, "commit", "-qm", "init")
        _TEMPLATES[baseline] = path
    return _TEMPLATES[baseline]


class RepoFixture(unittest.TestCase):
    """A throwaway git repo with one committed baseline file, copied from a prebuilt template.

    Override `baseline` to change what that file is; each distinct value is built once.
    """

    baseline = ("baseline.md", "baseline\n")

    def setUp(self):
        """Copy the template into a directory of this test's own."""
        self.repo = Path(tempfile.mkdtemp()) / "repo"
        self.addCleanup(shutil.rmtree, self.repo.parent, ignore_errors=True)
        shutil.copytree(template_repo(self.baseline), self.repo)

    def write(self, name, content):
        """Write a file inside the repo, creating parent directories.

        :param name: repo-relative path
        :param content: file body
        :return: absolute Path written
        """
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def commit(self, message="change"):
        """Stage and commit everything currently in the working tree.

        :param message: commit message
        """
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", message)
