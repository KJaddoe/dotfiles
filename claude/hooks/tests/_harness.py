#!/usr/bin/env python3
"""Shared machinery for the hook test suites: how a hook is loaded, invoked and fixtured.

Every suite used to carry its own copy of all three. That is where pylint's duplicate-code
warnings came from, and it is also what made the suite slow: each copy spawned a fresh
interpreter per case, and the two fixture-heavy suites rebuilt a git repository per case on top
of that. Measured, those two accounted for half the suite's wall clock from a twelfth of its
tests.

The git fixture is therefore built ONCE per baseline and copied per test rather than rebuilt.
`git init` plus a config plus a commit is five subprocesses; a copy of the finished tree is one
filesystem walk, and it leaves each test with the same untouched repository it had before.

Not a test module itself, and named to match `_hookutil.py`: the leading underscore says it is
imported, never run.
"""

import atexit
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]

# Loading a hook by file path does not put the hooks directory on sys.path, so its own
# `from _hookutil import ...` would fail without this.
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

GIT_TIMEOUT_SECONDS = 30

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
