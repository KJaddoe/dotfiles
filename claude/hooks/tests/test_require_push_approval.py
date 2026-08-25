#!/usr/bin/env python3
"""Tests for the require-push-approval PreToolUse hook.

Run: python3 claude/hooks/tests/test_require_push_approval.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

The property under test is that nothing reaches a remote unapproved: prompting modes must ask,
every other mode must deny, and "allow" is not a legal outcome for a real push.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "require-push-approval.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("require_push_approval", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

NON_PROMPTING_MODES = ["auto", "acceptEdits", "dontAsk", "bypassPermissions"]

GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}


def run_hook(command, mode="default", tool="Bash", cwd=None):
    """Invoke the hook with a payload and return its parsed decision.

    :param command: the shell command the model would run
    :param mode: permission mode reported by the session
    :param tool: tool name to report
    :param cwd: working directory to report
    :return: the hookSpecificOutput dict, or None when the hook stayed silent
    """
    payload = json.dumps(
        {
            "tool_name": tool,
            "tool_input": {"command": command},
            "permission_mode": mode,
            "cwd": cwd or str(Path.cwd()),
        }
    )
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]


def git(repo, *args):
    """Run a git command in a fixture repo, isolated from the developer's own config.

    :param repo: repository path
    :param args: git arguments
    """
    subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, env=GIT_ENV, timeout=20
    )


class TestPromptingModes(unittest.TestCase):
    """Where a prompt can render, the user is asked."""

    def test_plain_push_asks(self):
        """A bare push raises an approval prompt."""
        self.assertEqual(run_hook("git push")["permissionDecision"], "ask")

    def test_explicit_remote_and_branch(self):
        """Naming the remote does not exempt it."""
        self.assertEqual(run_hook("git push origin HEAD")["permissionDecision"], "ask")

    def test_plan_mode_asks(self):
        """Plan mode also prompts."""
        self.assertEqual(run_hook("git push", mode="plan")["permissionDecision"], "ask")


class TestNonPromptingModes(unittest.TestCase):
    """Where a prompt would be auto-approved, the push is denied instead."""

    def test_every_non_prompting_mode_denies(self):
        """auto, acceptEdits, dontAsk and bypassPermissions all deny."""
        for mode in NON_PROMPTING_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(run_hook("git push", mode=mode)["permissionDecision"], "deny")

    def test_never_allows(self):
        """No mode produces an allow decision for a real push."""
        modes = ["default", "plan"] + NON_PROMPTING_MODES
        decisions = [run_hook("git push", mode=m)["permissionDecision"] for m in modes]
        self.assertNotIn("allow", decisions)


class TestCoverage(unittest.TestCase):
    """Every shape of push is caught."""

    def test_force_push_is_flagged(self):
        """A force push says so in the prompt."""
        reason = run_hook("git push --force origin main")["permissionDecisionReason"]
        self.assertIn("FORCE PUSH", reason)

    def test_force_with_lease_is_flagged(self):
        """The `please` alias's flag is a force push too."""
        reason = run_hook("git push --force-with-lease")["permissionDecisionReason"]
        self.assertIn("FORCE PUSH", reason)

    def test_short_force_flag_is_flagged(self):
        """`-f` is a force push."""
        self.assertIn("FORCE PUSH", run_hook("git push -f")["permissionDecisionReason"])

    def test_global_flags_before_subcommand(self):
        """`git -C dir push` is still a push."""
        self.assertEqual(run_hook("git -C /tmp/repo push")["permissionDecision"], "ask")

    def test_compound_command(self):
        """A push hidden behind && is caught."""
        out = run_hook("git commit -m x && git push")
        self.assertEqual(out["permissionDecision"], "ask")

    def test_tags_push(self):
        """Pushing tags publishes too."""
        self.assertEqual(run_hook("git push --tags")["permissionDecision"], "ask")


class TestPassthrough(unittest.TestCase):
    """Anything that does not publish must not be touched."""

    def test_dry_run_is_not_gated(self):
        """A dry run publishes nothing."""
        self.assertIsNone(run_hook("git push --dry-run"))

    def test_non_bash_tool(self):
        """A non-Bash tool call is ignored."""
        self.assertIsNone(run_hook("git push", tool="Edit"))

    def test_pull_is_not_a_push(self):
        """Fetching is not publishing."""
        self.assertIsNone(run_hook("git pull --rebase"))

    def test_prose_mentioning_pushing(self):
        """The word in prose is not a push."""
        self.assertIsNone(run_hook("echo 'remember to push later'"))

    def test_heredoc_body_mentioning_a_push(self):
        """A script written via heredoc is data, not a push."""
        self.assertIsNone(run_hook("cat > x.sh <<'EOF'\ngit push origin main\nEOF"))

    def test_malformed_payload(self):
        """Garbage on stdin exits quietly rather than crashing the tool call."""
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="not json",
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0)


class TestSummary(unittest.TestCase):
    """The prompt must say what would actually be published."""

    def setUp(self):
        """Create a repo with one commit beyond a stand-in default branch."""
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        empty_template = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty_template, ignore_errors=True)
        git(self.repo, "init", "-q", "-b", "main", f"--template={empty_template}")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "test")
        (self.repo / "a.txt").write_text("a\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "init")

    def test_branch_name_appears(self):
        """The user sees which branch is being published."""
        git(self.repo, "checkout", "-qb", "feature/widget")
        reason = run_hook("git push", cwd=str(self.repo))["permissionDecisionReason"]
        self.assertIn("feature/widget", reason)

    def test_unpushed_commit_appears(self):
        """A commit that is not on the base branch is listed."""
        git(self.repo, "checkout", "-qb", "feature/widget")
        (self.repo / "b.txt").write_text("b\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "feat: add the widget")
        reason = run_hook("git push", cwd=str(self.repo))["permissionDecisionReason"]
        self.assertIn("feat: add the widget", reason)

    def test_branch_with_no_upstream_is_named_as_such(self):
        """A never-pushed branch says it is not on any remote."""
        git(self.repo, "checkout", "-qb", "feature/widget")
        reason = run_hook("git push", cwd=str(self.repo))["permissionDecisionReason"]
        self.assertIn("not yet on any remote", reason)

    def test_no_baseline_is_reported_not_guessed(self):
        """With nothing to compare against, say so rather than list all history."""
        with tempfile.TemporaryDirectory() as tmp:
            empty_template = Path(tempfile.mkdtemp())
            self.addCleanup(shutil.rmtree, empty_template, ignore_errors=True)
            git(tmp, "init", "-q", "-b", "solo", f"--template={empty_template}")
            git(tmp, "config", "user.email", "test@example.com")
            git(tmp, "config", "user.name", "test")
            Path(tmp, "a.txt").write_text("a\n", encoding="utf-8")
            git(tmp, "add", "-A")
            git(tmp, "commit", "-qm", "init")
            reason = run_hook("git push", cwd=tmp)["permissionDecisionReason"]
        self.assertIn("no upstream and no default branch", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
