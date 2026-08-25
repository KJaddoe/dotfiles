#!/usr/bin/env python3
"""Tests for the block-typographic-dashes PreToolUse guard.

Run: python3 claude/hooks/tests/test_block_typographic_dashes.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

The dashes are assembled from escapes so this file never contains the characters the hook blocks,
matching the convention in test_block_claude_attribution.py. Editing this file must not trip the
guard it tests.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "block-typographic-dashes.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("block_typographic_dashes", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

EM = "\u2014"
EN = "\u2013"

BLOCK = 2
ALLOW = 0


def run_hook(tool, tool_input):
    """Invoke the hook with a payload and return its exit code.

    :param tool: tool name to report
    :param tool_input: the tool's input payload
    :return: hook exit code (2 blocks, 0 allows)
    """
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    return result.returncode


class TestWrite(unittest.TestCase):
    """Writing a new file must not introduce a typographic dash."""

    def test_new_file_with_em_dash_is_blocked(self):
        """An em dash in new content is refused."""
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp, "new.md"))
            self.assertEqual(run_hook("Write", {"file_path": path, "content": f"a {EM} b"}), BLOCK)

    def test_new_file_with_en_dash_is_blocked(self):
        """An en dash is refused too."""
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp, "new.md"))
            self.assertEqual(run_hook("Write", {"file_path": path, "content": f"a {EN} b"}), BLOCK)

    def test_plain_hyphen_is_allowed(self):
        """The replacement the rule asks for passes."""
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp, "new.md"))
            self.assertEqual(run_hook("Write", {"file_path": path, "content": "a - b"}), ALLOW)

    def test_rewrite_preserving_existing_dashes_is_allowed(self):
        """Rewriting a file that already had dashes, without adding any, passes."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "existing.md")
            path.write_text(f"one {EM} two {EM} three", encoding="utf-8")
            content = f"ONE {EM} TWO {EM} THREE"
            self.assertEqual(run_hook("Write", {"file_path": str(path), "content": content}), ALLOW)

    def test_rewrite_adding_one_more_is_blocked(self):
        """Adding a dash to a file that already had some is still refused."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "existing.md")
            path.write_text(f"one {EM} two", encoding="utf-8")
            content = f"one {EM} two {EM} three"
            self.assertEqual(run_hook("Write", {"file_path": str(path), "content": content}), BLOCK)

    def test_removing_dashes_is_allowed(self):
        """The cleanup pass must not be blocked by the guard."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "existing.md")
            path.write_text(f"one {EM} two {EM} three", encoding="utf-8")
            self.assertEqual(
                run_hook("Write", {"file_path": str(path), "content": "one - two - three"}), ALLOW
            )


class TestEdit(unittest.TestCase):
    """An edit is judged on what it adds, not on what it touches."""

    def test_adding_a_dash_is_blocked(self):
        """Introducing a dash in new_string is refused."""
        payload = {"file_path": "/tmp/x.md", "old_string": "a - b", "new_string": f"a {EM} b"}
        self.assertEqual(run_hook("Edit", payload), BLOCK)

    def test_carrying_a_dash_through_is_allowed(self):
        """An unrelated edit to a line that already has a dash passes."""
        payload = {
            "file_path": "/tmp/x.md",
            "old_string": f"old text {EM} tail",
            "new_string": f"new text {EM} tail",
        }
        self.assertEqual(run_hook("Edit", payload), ALLOW)

    def test_removing_a_dash_is_allowed(self):
        """Replacing a dash with a hyphen passes."""
        payload = {"file_path": "/tmp/x.md", "old_string": f"a {EM} b", "new_string": "a - b"}
        self.assertEqual(run_hook("Edit", payload), ALLOW)

    def test_plain_edit_is_allowed(self):
        """An edit with no dashes anywhere passes."""
        payload = {"file_path": "/tmp/x.md", "old_string": "a", "new_string": "b"}
        self.assertEqual(run_hook("Edit", payload), ALLOW)


class TestOtherTools(unittest.TestCase):
    """Coverage of the remaining write paths, and of what must be ignored."""

    def test_notebook_edit_is_blocked(self):
        """A notebook cell carrying a dash is refused."""
        self.assertEqual(run_hook("NotebookEdit", {"new_source": f"# a {EM} b"}), BLOCK)

    def test_bash_is_ignored(self):
        """This guard does not police shell commands."""
        self.assertEqual(run_hook("Bash", {"command": f"echo 'a {EM} b'"}), ALLOW)

    def test_read_is_ignored(self):
        """Reading is never blocked."""
        self.assertEqual(run_hook("Read", {"file_path": "/tmp/x.md"}), ALLOW)

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
        self.assertEqual(result.returncode, ALLOW)


class TestMessage(unittest.TestCase):
    """The refusal must say what to do instead."""

    def test_message_names_the_dash_and_the_fix(self):
        """The model is told which dash was found and to reword rather than swap."""
        payload = json.dumps(
            {
                "tool_name": "Edit",
                "tool_input": {"old_string": "a", "new_string": f"a {EM} b"},
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
        self.assertIn("U+2014", result.stderr)
        self.assertIn("reword", result.stderr)


class TestSourceIsClean(unittest.TestCase):
    """The guard and its tests must not contain what they block."""

    def test_hook_source_has_no_literal_dashes(self):
        """The hook builds its constants from escapes."""
        source = HOOK_PATH.read_text(encoding="utf-8")
        self.assertEqual(hook.count_banned(source), 0)

    def test_this_test_file_has_no_literal_dashes(self):
        """Editing this file must never trip the guard it tests."""
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertEqual(hook.count_banned(source), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
