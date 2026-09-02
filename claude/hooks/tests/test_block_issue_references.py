#!/usr/bin/env python3
"""Tests for the block-issue-references PreToolUse guard.

Run: python3 claude/hooks/tests/test_block_issue_references.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

Every reference the hook blocks is assembled from a HASH constant rather than written literally,
matching the convention in test_block_typographic_dashes.py. Editing this file must not trip the
guard it tests.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "block-issue-references.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("block_issue_references", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

HASH = "#"

BLOCK = 2
ALLOW = 0


def ref(number):
    """Build a hash-prefixed reference without writing one literally in this file.

    :param number: the number to reference
    :return: the reference as it would appear in text
    """
    return HASH + str(number)


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


def write(content, name="notes.md"):
    """Run the hook over a Write of new content to a named file.

    :param content: the content being written
    :param name: file name, which decides whether the file counts as prose
    :return: hook exit code
    """
    return run_hook("Write", {"file_path": f"/tmp/does-not-exist/{name}", "content": content})


class TestCuedCitation(unittest.TestCase):
    """A citation cue next to a number is refused wherever it appears."""

    def test_fixes_in_a_code_comment_is_blocked(self):
        """`Fixes <n>` in a source comment is the canonical case."""
        self.assertEqual(write(f"// Fixes {ref(12)}\n", "cart.js"), BLOCK)

    def test_see_issue_in_markdown_is_blocked(self):
        """A prose pointer to an issue is refused."""
        self.assertEqual(write(f"No version is pinned yet, see issue {ref(439)}.\n"), BLOCK)

    def test_closes_is_blocked(self):
        """`closes` is a cue like `fixes`."""
        self.assertEqual(write(f"# closes {ref(7)}\n", "run.sh"), BLOCK)

    def test_gh_dash_form_is_blocked(self):
        """The `GH-<n>` spelling is the same citation without a hash."""
        self.assertEqual(write("Guards against GH-123 coming back.\n"), BLOCK)


class TestTrackerUrl(unittest.TestCase):
    """A link into a tracker rots exactly like a bare number."""

    def test_github_issue_url_is_blocked(self):
        """A GitHub issue URL is a citation."""
        self.assertEqual(write("See https://github.com/o/r/issues/12 for context.\n"), BLOCK)

    def test_github_pull_url_is_blocked(self):
        """A GitHub pull URL is a citation."""
        self.assertEqual(write("See https://github.com/o/r/pull/12 for context.\n"), BLOCK)

    def test_jira_browse_url_is_blocked(self):
        """A Jira browse URL is a citation."""
        self.assertEqual(write("See https://acme.atlassian.net/browse/ABC-1 today.\n"), BLOCK)


class TestTrackerKey(unittest.TestCase):
    """Jira-style keys are citations, but standards identifiers share their shape."""

    def test_bare_project_key_is_blocked(self):
        """A project key in a comment is a ticket citation."""
        self.assertEqual(write("// ABC-1234: guard the cart\n", "cart.js"), BLOCK)

    def test_utf_8_is_allowed(self):
        """An encoding name is not a ticket."""
        self.assertEqual(write("Read the file as UTF-8 before parsing.\n"), ALLOW)

    def test_sha_256_is_allowed(self):
        """A hash algorithm is not a ticket."""
        self.assertEqual(write("Digest the payload with SHA-256.\n"), ALLOW)

    def test_cve_is_allowed(self):
        """A CVE identifier is durable and worth citing."""
        self.assertEqual(write("Patched for CVE-2024-1234 upstream.\n"), ALLOW)

    def test_rfc_is_allowed(self):
        """An RFC number is durable and worth citing."""
        self.assertEqual(write("Conditional requests follow RFC-7231.\n"), ALLOW)

    def test_toolchain_version_is_allowed(self):
        """A toolchain version shares the shape of a key but names a release."""
        self.assertEqual(write("Java early, so the JDK-17 provider lands first.\n"), ALLOW)


class TestBareNumber(unittest.TestCase):
    """A bare number in prose is blocked; an ordinal and a colour are not."""

    def test_bare_number_in_markdown_is_blocked(self):
        """Prose naming a number with no cue is still a citation."""
        self.assertEqual(write(f"Guards {ref(515)}: the cart used to decide.\n"), BLOCK)

    def test_bare_number_in_a_comment_is_blocked(self):
        """A comment naming a number with no cue is still a citation."""
        self.assertEqual(write(f"// guards {ref(515)}\n", "cart.js"), BLOCK)

    def test_ordinal_rule_is_allowed(self):
        """`rule <n>` counts an item in a list, it does not cite a tracker."""
        self.assertEqual(
            write(f"Prose rule {ref(41)} in a file of 40 rules fixes nothing.\n"), ALLOW
        )

    def test_ordinal_line_is_allowed(self):
        """`Line <n>` counts a line."""
        self.assertEqual(write(f"# =====[ Line {ref(1)} ]=====\n", "p10k.zsh"), ALLOW)

    def test_hex_colour_with_letters_is_allowed(self):
        """A hex colour is not a number reference."""
        self.assertEqual(write("Background is #1a2b3c in the dark theme.\n"), ALLOW)

    def test_six_digit_hex_colour_is_allowed(self):
        """Six digits is a colour, not a plausible issue number."""
        self.assertEqual(write("Background is #123456 in the dark theme.\n"), ALLOW)

    def test_number_in_code_is_allowed(self):
        """Outside a comment, source is not prose and is left alone."""
        self.assertEqual(write(f'value = data["{ref(5)}"]\n', "load.py"), ALLOW)


class TestDelta(unittest.TestCase):
    """The judgement is on what an edit ADDS, never on what the file already holds."""

    def test_write_carrying_an_existing_reference_through_is_allowed(self):
        """Rewriting a file without adding a reference passes."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.md"
            body = f"Guards {ref(515)}: the cart used to decide.\n"
            path.write_text(body, encoding="utf-8")
            code = run_hook("Write", {"file_path": str(path), "content": body + "More prose.\n"})
        self.assertEqual(code, ALLOW)

    def test_write_adding_a_second_reference_is_blocked(self):
        """Adding one to a file that already had one is still adding one."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.md"
            path.write_text(f"Guards {ref(515)}.\n", encoding="utf-8")
            code = run_hook(
                "Write",
                {"file_path": str(path), "content": f"Guards {ref(515)}.\nAlso {ref(496)}.\n"},
            )
        self.assertEqual(code, BLOCK)

    def test_edit_preserving_a_reference_is_allowed(self):
        """Touching a line that already cites an issue does not wedge the edit."""
        code = run_hook(
            "Edit",
            {
                "file_path": "/tmp/does-not-exist/notes.md",
                "old_string": f"Guards {ref(515)} loosely.",
                "new_string": f"Guards {ref(515)} tightly.",
            },
        )
        self.assertEqual(code, ALLOW)

    def test_edit_adding_a_reference_is_blocked(self):
        """Introducing a citation in an edit is refused."""
        code = run_hook(
            "Edit",
            {
                "file_path": "/tmp/does-not-exist/notes.md",
                "old_string": "Guards the cart.",
                "new_string": f"Guards the cart, see issue {ref(439)}.",
            },
        )
        self.assertEqual(code, BLOCK)


class TestBash(unittest.TestCase):
    """Content written through a heredoc must not bypass the guard."""

    def test_heredoc_body_with_a_citation_is_blocked(self):
        """A file written with `cat > f <<EOF` is file content."""
        command = f"cat > notes.md <<'EOF'\nFixes {ref(12)}\nEOF\n"
        self.assertEqual(run_hook("Bash", {"command": command}), BLOCK)

    def test_grep_for_a_reference_is_allowed(self):
        """Searching for a citation is not writing one."""
        self.assertEqual(run_hook("Bash", {"command": f"grep -rn '{ref(12)}' ."}), ALLOW)


class TestNotebook(unittest.TestCase):
    """A notebook cell is file content like any other."""

    def test_new_source_with_a_citation_is_blocked(self):
        """A citation in a notebook cell is refused."""
        code = run_hook("NotebookEdit", {"new_source": f"# Fixes {ref(12)}\n"})
        self.assertEqual(code, BLOCK)


class TestPayload(unittest.TestCase):
    """A hook that cannot read its payload must never wedge the session."""

    def test_malformed_payload_allows(self):
        """Unreadable stdin exits 0."""
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="not json",
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(result.returncode, ALLOW)

    def test_unrelated_tool_allows(self):
        """A tool carrying no file content is ignored."""
        self.assertEqual(run_hook("Read", {"file_path": "/etc/hosts"}), ALLOW)


if __name__ == "__main__":
    unittest.main(verbosity=2)
