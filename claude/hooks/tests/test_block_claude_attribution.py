#!/usr/bin/env python3
"""Tests for the block-claude-attribution PreToolUse hook.

Run: python3 claude/hooks/tests/test_block_claude_attribution.py
Uses stdlib unittest only — no third-party dependencies, identical on macOS and Linux.

Trigger strings are assembled from fragments so this file never contains the literal text
the hook blocks on — otherwise editing it would trip the hook on its own test data.
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "block-claude-attribution.py"

spec = importlib.util.spec_from_file_location("block_claude_attribution", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

TRAILER = "Co-Authored" + "-By: " + "Claude"
GENERATED = "Generated with " + "Claude Code"
ROBOT = "\U0001f916"
NOREPLY = "noreply@" + "anthropic.com"


def run_hook(command, tool="Bash"):
    """Invoke the hook with a Bash command payload and return its exit code.

    :param command: the shell command the model would run
    :param tool: tool name to report
    :return: hook exit code (2 blocks, 0 allows)
    """
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": command}})
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    return result.returncode


class TestBlocks(unittest.TestCase):
    """Commits carrying attribution or gpg-sign must be blocked."""

    def test_coauthored_trailer(self):
        """A co-authored trailer is blocked."""
        self.assertEqual(run_hook(f"git commit -m 'feat: x\n\n{TRAILER} <{NOREPLY}>'"), 2)

    def test_generated_with_text(self):
        """A generated-with line is blocked."""
        self.assertEqual(run_hook(f"git commit -m '{GENERATED}'"), 2)

    def test_robot_emoji(self):
        """A robot emoji trailer is blocked."""
        self.assertEqual(run_hook(f"git commit -m 'chore: x {ROBOT}'"), 2)

    def test_gpg_long_flag(self):
        """--gpg-sign is blocked."""
        self.assertEqual(run_hook("git commit --gpg-sign -m ok"), 2)

    def test_gpg_short_flag(self):
        """-S is blocked."""
        self.assertEqual(run_hook("git commit -S -m ok"), 2)

    def test_gpg_in_flag_cluster(self):
        """-S inside a short-flag cluster is blocked."""
        self.assertEqual(run_hook("git commit -amS 'x'"), 2)

    def test_amend_with_attribution(self):
        """Amend carrying attribution is blocked."""
        self.assertEqual(run_hook(f"git commit --amend -m '{TRAILER}'"), 2)

    def test_compound_command(self):
        """A commit hidden behind && is still inspected."""
        self.assertEqual(run_hook(f"cd /tmp && git commit -m '{TRAILER}'"), 2)

    def test_git_with_c_flag(self):
        """`git -C dir commit` is still inspected."""
        self.assertEqual(run_hook(f"git -C /tmp commit -m '{TRAILER}'"), 2)


class TestAllows(unittest.TestCase):
    """Legitimate commands must pass through untouched."""

    def test_clean_commit(self):
        """An ordinary commit is allowed."""
        self.assertEqual(run_hook("git commit -m 'feat: normal message'"), 0)

    def test_signoff_lowercase_s_allowed(self):
        """-s is --signoff, which is permitted; only -S is gpg."""
        self.assertEqual(run_hook("git commit -s -m ok"), 0)

    def test_non_bash_tool(self):
        """Non-Bash tools are ignored."""
        self.assertEqual(run_hook("anything", tool="Read"), 0)

    def test_unrelated_bash(self):
        """Unrelated shell commands are ignored."""
        self.assertEqual(run_hook("ls -la"), 0)


class TestReadOnlyGitNotBlocked(unittest.TestCase):
    """Regression: read-only git commands must not trip the guard.

    The original matcher fired on any command containing both "git" and "commit",
    so `git log` inspecting commit messages was blocked.
    """

    def test_git_log_with_attribution_in_output_format(self):
        """git log is read-only and must pass even when the text appears in it."""
        self.assertEqual(run_hook(f"git log --format='%B' | grep '{TRAILER}'"), 0)

    def test_git_log_containing_the_word_commits(self):
        """Reproduces the real false positive: the substring 'commit' in prose.

        `git log ... | xargs echo "commits ahead"` contains both "git" and "commit",
        so the substring matcher blocked a read-only verification command.
        """
        self.assertEqual(
            run_hook('git log origin/main..HEAD --oneline | wc -l | xargs echo "commits ahead:"'),
            0,
        )

    def test_git_log_grep_for_attribution_audit(self):
        """Auditing history for attribution must not itself be blocked."""
        self.assertEqual(
            run_hook(f"git log -4 --format='%B' | grep -iE 'claude|{ROBOT}' # check commits"),
            0,
        )

    def test_git_log_grep_robot(self):
        """Searching history for the robot emoji is read-only."""
        self.assertEqual(run_hook(f"git log -20 | grep '{ROBOT}'"), 0)

    def test_git_show_allowed(self):
        """git show is read-only."""
        self.assertEqual(run_hook(f"git show HEAD | grep '{TRAILER}'"), 0)

    def test_git_diff_allowed(self):
        """git diff is read-only."""
        self.assertEqual(run_hook("git diff --stat"), 0)

    def test_word_commit_in_unrelated_command(self):
        """The bare word 'commit' in prose must not trigger on a non-git command."""
        self.assertEqual(run_hook("echo 'about to commit changes with git'"), 0)

    def test_readonly_then_real_commit_still_blocked(self):
        """A read-only command chained before a real commit must still block."""
        self.assertEqual(run_hook(f"git log -1 && git commit -m '{TRAILER}'"), 2)


class TestOtherWriteSubcommands(unittest.TestCase):
    """Attribution must stay blocked on commit-adjacent write subcommands."""

    def test_merge_with_attribution(self):
        """git merge carrying attribution is blocked."""
        self.assertEqual(run_hook(f"git merge --no-ff -m '{TRAILER}' topic"), 2)

    def test_tag_with_attribution(self):
        """git tag carrying attribution is blocked."""
        self.assertEqual(run_hook(f"git tag -a v1 -m '{TRAILER}'"), 2)

    def test_revert_with_attribution(self):
        """git revert carrying attribution is blocked."""
        self.assertEqual(run_hook(f"git revert --no-edit -m '{TRAILER}' HEAD"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
