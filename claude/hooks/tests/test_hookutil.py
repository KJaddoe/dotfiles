#!/usr/bin/env python3
"""Tests for the shared hook git helpers, and for the import they depend on.

Run: python3 claude/hooks/tests/test_hookutil.py
Uses stdlib unittest only — no third-party dependencies, identical on macOS and Linux.

The standalone-invocation tests are the point of this file. Extracting `_hookutil.py` made every
Stop hook depend on Python placing a script's own directory at the front of `sys.path`. That is
documented behaviour, but it is now load-bearing for hooks the user never invokes by hand, so it
is asserted rather than assumed.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS_DIR))

spec = importlib.util.spec_from_file_location("_hookutil", HOOKS_DIR / "_hookutil.py")
hookutil = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hookutil)

SETTINGS = json.loads((HOOKS_DIR.parent / "settings.json").read_text())


def stop_hook_scripts():
    """List the script filenames settings.json registers as Stop hooks.

    Derived rather than hardcoded, so registering a hook cannot leave this list behind.

    :return: script basenames, in registration order
    """
    return [
        entry["command"].rsplit("/", 1)[-1]
        for matcher in SETTINGS["hooks"]["Stop"]
        for entry in matcher["hooks"]
    ]


class GitHelpers(unittest.TestCase):
    """run_git and repo_root against real repositories and real failures."""

    def setUp(self):
        """Create a temp git repo and a plain directory outside any repo."""
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True, capture_output=True)

    def test_run_git_returns_stdout(self):
        """Happy path: a successful command yields its output."""
        out = hookutil.run_git(self.repo, "rev-parse", "--is-inside-work-tree")
        self.assertEqual(out.strip(), "true")

    def test_run_git_swallows_failure(self):
        """A failing git command yields "" rather than raising or leaking stderr."""
        self.assertEqual(hookutil.run_git(self.repo, "cat-file", "-p", "deadbeef"), "")

    def test_run_git_survives_missing_directory(self):
        """A path that does not exist must not raise."""
        self.assertEqual(hookutil.run_git(self.repo / "gone", "status"), "")

    def test_repo_root_resolves(self):
        """The root of a repo is found from a nested directory."""
        nested = self.repo / "a" / "b"
        nested.mkdir(parents=True)
        found = hookutil.repo_root(nested)
        self.assertEqual(found.resolve(), self.repo.resolve())

    def test_repo_root_outside_a_repo_is_none(self):
        """Outside any repository the result is None, not an exception."""
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        self.assertIsNone(hookutil.repo_root(outside))


class StandaloneInvocation(unittest.TestCase):
    """Every hook must stay runnable as `python3 ~/.claude/hooks/<name>.py` from any cwd."""

    def setUp(self):
        """Create a directory unrelated to the hooks directory to run from."""
        self.elsewhere = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.elsewhere, ignore_errors=True)

    def test_hooks_import_shared_helpers_from_any_cwd(self):
        """Regression: the shared import must resolve without the cwd being the hooks dir.

        Run by absolute path from an unrelated directory, exactly as settings.json invokes them.
        An ImportError here would break every session, silently.
        """
        for name in stop_hook_scripts():
            with self.subTest(hook=name):
                result = subprocess.run(
                    [sys.executable, str(HOOKS_DIR / name)],
                    input=json.dumps({"cwd": str(self.elsewhere)}),
                    capture_output=True,
                    text=True,
                    cwd=self.elsewhere,
                )
                self.assertNotIn("ImportError", result.stderr)
                self.assertNotIn("ModuleNotFoundError", result.stderr)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_shared_module_is_not_itself_a_hook(self):
        """`_hookutil.py` is internal: settings.json must never invoke it."""
        commands = [
            entry["command"]
            for group in SETTINGS.get("hooks", {}).values()
            for matcher in group
            for entry in matcher.get("hooks", [])
        ]
        self.assertTrue(commands)
        self.assertFalse([c for c in commands if "_hookutil" in c])

    def test_registered_stop_hooks_all_exist(self):
        """Every Stop hook settings.json names must be a file on disk."""
        for name in stop_hook_scripts():
            with self.subTest(hook=name):
                self.assertTrue((HOOKS_DIR / name).is_file(), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
