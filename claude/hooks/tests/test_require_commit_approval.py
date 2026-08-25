#!/usr/bin/env python3
"""Tests for the require-commit-approval PreToolUse hook.

Run: python3 claude/hooks/tests/test_require_commit_approval.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

The property under test is that a commit can never reach git unapproved: prompting modes must
ask, and every non-prompting mode must deny. "allow" is not a legal outcome of this hook.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "require-commit-approval.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("require_commit_approval", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

NON_PROMPTING_MODES = ["auto", "acceptEdits", "dontAsk", "bypassPermissions"]


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


def decisions_for(command):
    """Collect the hook's decision for `command` across every permission mode.

    :param command: the shell command the model would run
    :return: list of permissionDecision strings
    """
    modes = ["default", "plan"] + NON_PROMPTING_MODES
    return [run_hook(command, mode=m)["permissionDecision"] for m in modes]


class TestPromptingModes(unittest.TestCase):
    """Where a prompt can render, the user is asked."""

    def test_plain_commit_asks(self):
        """A commit in default mode raises an approval prompt."""
        self.assertEqual(run_hook("git commit -m 'feat: x'")["permissionDecision"], "ask")

    def test_plan_mode_asks(self):
        """Plan mode also prompts."""
        out = run_hook("git commit -m 'feat: x'", mode="plan")
        self.assertEqual(out["permissionDecision"], "ask")

    def test_reason_names_the_rule(self):
        """The prompt points at the rule it enforces."""
        out = run_hook("git commit -m 'feat: x'")
        self.assertIn("CLAUDE.md", out["permissionDecisionReason"])


class TestNonPromptingModes(unittest.TestCase):
    """Where a prompt would be auto-approved, the commit is denied instead."""

    def test_every_non_prompting_mode_denies(self):
        """auto, acceptEdits, dontAsk and bypassPermissions all deny."""
        for mode in NON_PROMPTING_MODES:
            with self.subTest(mode=mode):
                out = run_hook("git commit -m 'feat: x'", mode=mode)
                self.assertEqual(out["permissionDecision"], "deny")

    def test_denial_explains_the_way_out(self):
        """The denial tells the model to get approval and switch mode."""
        reason = run_hook("git commit -m 'x'", mode="acceptEdits")["permissionDecisionReason"]
        self.assertIn("default", reason)

    def test_never_allows(self):
        """No mode produces an allow decision for a commit."""
        self.assertNotIn("allow", decisions_for("git commit -m 'x'"))


class TestCoverage(unittest.TestCase):
    """Every shape of commit invocation is caught."""

    def test_amend(self):
        """An amend rewrites a commit and is gated too."""
        self.assertEqual(run_hook("git commit --amend --no-edit")["permissionDecision"], "ask")

    def test_clustered_short_flags(self):
        """`-am` is a commit."""
        self.assertEqual(run_hook("git commit -am 'x'")["permissionDecision"], "ask")

    def test_global_flags_before_subcommand(self):
        """A commit reached through global flags is still a commit."""
        out = run_hook("git -C /tmp/repo commit -m 'x'")
        self.assertEqual(out["permissionDecision"], "ask")

    def test_compound_command(self):
        """A commit hidden behind && is caught."""
        self.assertEqual(run_hook("git add -A && git commit -m 'x'")["permissionDecision"], "ask")


class TestPassthrough(unittest.TestCase):
    """Anything that is not a commit must not be touched."""

    def test_non_bash_tool(self):
        """A non-Bash tool call is ignored."""
        self.assertIsNone(run_hook("git commit -m 'x'", tool="Edit"))

    def test_read_only_history(self):
        """Inspecting history is not committing."""
        self.assertIsNone(run_hook("git log --oneline | grep commit"))

    def test_prose_mentioning_commits(self):
        """The word 'commits' in prose is not a commit."""
        self.assertIsNone(run_hook("echo 'we are 3 commits ahead'"))

    def test_status(self):
        """git status is untouched."""
        self.assertIsNone(run_hook("git status -sb"))

    def test_heredoc_body_mentioning_a_commit(self):
        """A script written via heredoc is data, not a commit."""
        self.assertIsNone(run_hook("python3 - <<'PY'\n# git commit -m x\nPY"))

    def test_command_after_heredoc_still_gated(self):
        """A real commit following a heredoc is still caught."""
        cmd = "cat > x.txt <<'EOF'\nhello\nEOF\ngit commit -m 'x'"
        self.assertEqual(run_hook(cmd)["permissionDecision"], "ask")

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
    """The approval prompt must carry what is about to be committed."""

    def test_staged_file_appears_in_prompt(self):
        """A staged file's name reaches the reason the user reads."""
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
            subprocess.run(["git", "init", "-q", tmp], check=True, env=env, timeout=20)
            Path(tmp, "widget.txt").write_text("hello\n", encoding="utf-8")
            subprocess.run(["git", "-C", tmp, "add", "widget.txt"], check=True, env=env, timeout=20)
            reason = run_hook("git commit -m 'x'", cwd=tmp)["permissionDecisionReason"]
        self.assertIn("widget.txt", reason)

    def test_empty_tree_says_so(self):
        """Nothing staged is reported rather than shown as an empty prompt."""
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
            subprocess.run(["git", "init", "-q", tmp], check=True, env=env, timeout=20)
            reason = run_hook("git commit -m 'x'", cwd=tmp)["permissionDecisionReason"]
        self.assertIn("Nothing staged", reason)

    def test_sweeps_tracked_detects_all_flag(self):
        """`-a` includes unstaged tracked changes; `--amend` alone does not."""
        self.assertTrue(hook.sweeps_tracked("git commit -am 'x'"))
        self.assertTrue(hook.sweeps_tracked("git commit --all -m 'x'"))
        self.assertFalse(hook.sweeps_tracked("git commit --amend --no-edit"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
