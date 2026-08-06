#!/usr/bin/env python3
"""Tests for bin/git-gone.

The script force-deletes local branches, so a regression here destroys work that
is not on any remote. Each test builds a throwaway bare "remote" plus a clone,
with the global and system git config neutralised, so the developer's own config
can never influence a result and nothing touches a real repository.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "git-gone"


class GitGoneTestCase(unittest.TestCase):
    """Base case providing a bare remote and a clone tracking it."""

    def setUp(self):
        """Create a bare remote, clone it, and commit an initial file."""
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        }
        self.remote = self.tmp / "remote.git"
        self.repo = self.tmp / "clone"
        self.shell("git", "init", "--bare", "--template=", "-q", "-b", "main", str(self.remote))
        self.shell("git", "clone", "--template=", "-q", str(self.remote), str(self.repo))
        self.git("config", "user.name", "test")
        self.git("config", "user.email", "test@example.com")
        (self.repo / "file.txt").write_text("x\n", encoding="utf-8")
        self.git("add", "file.txt")
        self.git("commit", "-q", "-m", "initial")
        self.git("push", "-q", "-u", "origin", "main")

    def shell(self, *args, cwd=None):
        """Run a command and return its CompletedProcess."""
        return subprocess.run(
            list(args),
            cwd=cwd or self.tmp,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def git(self, *args):
        """Run a git command inside the clone."""
        return self.shell("git", *args, cwd=self.repo)

    def gone(self, *args):
        """Run bin/git-gone inside the clone and return its CompletedProcess."""
        return self.shell(str(SCRIPT), *args, cwd=self.repo)

    def push_branch(self, name):
        """Create a branch, push it, and set its upstream."""
        self.git("branch", name, "main")
        self.git("push", "-q", "-u", "origin", name)

    def drop_upstream(self, name):
        """Delete a branch on the remote, leaving the local upstream gone."""
        self.shell("git", "-C", str(self.remote), "branch", "-D", name)

    def branches(self):
        """Return the set of local branch names in the clone."""
        out = self.git("for-each-ref", "--format=%(refname:short)", "refs/heads")
        return set(out.stdout.split())


class DeletesGoneBranches(GitGoneTestCase):
    """A branch whose upstream was deleted on the remote is removed."""

    def test_deletes_branch_with_gone_upstream(self):
        """The gone branch disappears and the command succeeds."""
        self.push_branch("feature")
        self.drop_upstream("feature")
        result = self.gone()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("feature", self.branches())

    def test_reports_the_deleted_branch(self):
        """The deleted branch is named on stdout."""
        self.push_branch("feature")
        self.drop_upstream("feature")
        self.assertIn("feature", self.gone().stdout)

    def test_deletes_unmerged_branch(self):
        """A branch with unmerged commits still goes, mirroring a squash merge."""
        self.push_branch("feature")
        self.git("checkout", "-q", "feature")
        (self.repo / "extra.txt").write_text("y\n", encoding="utf-8")
        self.git("add", "extra.txt")
        self.git("commit", "-q", "-m", "unmerged work")
        self.git("checkout", "-q", "main")
        self.drop_upstream("feature")
        self.gone()
        self.assertNotIn("feature", self.branches())

    def test_resolves_as_a_git_subcommand(self):
        """git gone works when bin/ is on PATH, not just as a direct call."""
        env = {**self.env, "PATH": f"{SCRIPT.parent}{os.pathsep}{self.env['PATH']}"}
        self.push_branch("feature")
        self.drop_upstream("feature")
        result = subprocess.run(
            ["git", "gone"],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("feature", self.branches())


class LeavesLiveBranchesAlone(GitGoneTestCase):
    """Branches that are not gone must survive — the destructive regression."""

    def test_keeps_branch_with_live_upstream(self):
        """A branch still present on the remote is never deleted."""
        self.push_branch("keep")
        self.gone()
        self.assertIn("keep", self.branches())

    def test_keeps_branch_with_no_upstream(self):
        """A purely local branch has no upstream and must not be touched."""
        self.git("branch", "local-only", "main")
        self.gone()
        self.assertIn("local-only", self.branches())

    def test_keeps_the_current_branch(self):
        """The checked-out branch is skipped even when its upstream is gone."""
        self.push_branch("feature")
        self.git("checkout", "-q", "feature")
        self.drop_upstream("feature")
        result = self.gone()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("feature", self.branches())
        self.assertIn("skipped", result.stdout)

    def test_dry_run_deletes_nothing(self):
        """--dry-run reports the branch but leaves it in place."""
        self.push_branch("feature")
        self.drop_upstream("feature")
        result = self.gone("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("feature", result.stdout)
        self.assertIn("feature", self.branches())

    def test_no_fetch_skips_pruning(self):
        """--no-fetch leaves the upstream unpruned, so nothing looks gone yet."""
        self.push_branch("feature")
        self.drop_upstream("feature")
        result = self.gone("--no-fetch")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("feature", self.branches())


class RejectsBadInput(GitGoneTestCase):
    """Invalid invocations fail loudly instead of deleting something."""

    def test_unknown_option_exits_two(self):
        """An unrecognised flag is rejected before any branch is touched."""
        self.push_branch("feature")
        self.drop_upstream("feature")
        result = self.gone("--force-everything")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown option", result.stderr)
        self.assertIn("feature", self.branches())

    def test_outside_a_repository_exits_one(self):
        """Running outside a work tree is an error, not a no-op."""
        outside = self.tmp / "plain"
        outside.mkdir()
        result = self.shell(str(SCRIPT), cwd=outside)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a git repository", result.stderr)

    def test_help_exits_zero_without_deleting(self):
        """--help prints usage and touches nothing."""
        self.push_branch("feature")
        self.drop_upstream("feature")
        result = self.gone("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: git gone", result.stdout)
        self.assertIn("feature", self.branches())


class ReportsNothingToDo(GitGoneTestCase):
    """A clean repo says so rather than failing."""

    def test_no_gone_branches_exits_zero(self):
        """With nothing to delete the command succeeds with a clear message."""
        result = self.gone()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No branches with a gone upstream", result.stdout)


if __name__ == "__main__":
    unittest.main()
