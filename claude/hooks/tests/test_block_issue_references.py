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
import shutil
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


def run_hook(tool, tool_input, cwd=""):
    """Invoke the hook with a payload and return its exit code.

    :param tool: tool name to report
    :param tool_input: the tool's input payload
    :param cwd: session working directory to report
    :return: hook exit code (2 blocks, 0 allows)
    """
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd)})
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    return result.returncode


class HookFixture(unittest.TestCase):
    """Base fixture giving each test a git working tree and a directory outside every tree.

    The guard only applies inside a repository, so a test writing to a plain temporary directory
    would pass for the wrong reason.
    """

    def setUp(self):
        """Create a throwaway repository and a plain directory beside it."""
        self.repo = Path(tempfile.mkdtemp(prefix="hookrepo-"))
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self.outside = Path(tempfile.mkdtemp(prefix="hookplain-"))
        self.addCleanup(shutil.rmtree, self.outside, ignore_errors=True)
        subprocess.run(
            ["git", "init", "-q", str(self.repo)], capture_output=True, check=False, timeout=20
        )

    def write(self, content, name="notes.md"):
        """Run the hook over a Write of new content to a named file in the repository.

        :param content: the content being written
        :param name: file name, which decides whether the file counts as prose
        :return: hook exit code
        """
        return run_hook(
            "Write", {"file_path": str(self.repo / name), "content": content}, cwd=self.repo
        )


class TestCuedCitation(HookFixture):
    """A citation cue next to a number is refused wherever it appears."""

    def test_fixes_in_a_code_comment_is_blocked(self):
        """`Fixes <n>` in a source comment is the canonical case."""
        self.assertEqual(self.write(f"// Fixes {ref(12)}\n", "cart.js"), BLOCK)

    def test_see_issue_in_markdown_is_blocked(self):
        """A prose pointer to an issue is refused."""
        self.assertEqual(self.write(f"No version is pinned yet, see issue {ref(439)}.\n"), BLOCK)

    def test_closes_is_blocked(self):
        """`closes` is a cue like `fixes`."""
        self.assertEqual(self.write(f"# closes {ref(7)}\n", "run.sh"), BLOCK)

    def test_gh_dash_form_is_blocked(self):
        """The `GH-<n>` spelling is the same citation without a hash."""
        self.assertEqual(self.write("Guards against GH-123 coming back.\n"), BLOCK)


class TestTrackerUrl(HookFixture):
    """A link into a tracker rots exactly like a bare number."""

    def test_github_issue_url_is_blocked(self):
        """A GitHub issue URL is a citation."""
        self.assertEqual(self.write("See https://github.com/o/r/issues/12 for context.\n"), BLOCK)

    def test_github_pull_url_is_blocked(self):
        """A GitHub pull URL is a citation."""
        self.assertEqual(self.write("See https://github.com/o/r/pull/12 for context.\n"), BLOCK)

    def test_jira_browse_url_is_blocked(self):
        """A Jira browse URL is a citation."""
        self.assertEqual(self.write("See https://acme.atlassian.net/browse/ABC-1 today.\n"), BLOCK)


class TestTrackerKey(HookFixture):
    """Jira-style keys are citations, but standards identifiers share their shape."""

    def test_bare_project_key_is_blocked(self):
        """A project key in a comment is a ticket citation."""
        self.assertEqual(self.write("// ABC-1234: guard the cart\n", "cart.js"), BLOCK)

    def test_utf_8_is_allowed(self):
        """An encoding name is not a ticket."""
        self.assertEqual(self.write("Read the file as UTF-8 before parsing.\n"), ALLOW)

    def test_sha_256_is_allowed(self):
        """A hash algorithm is not a ticket."""
        self.assertEqual(self.write("Digest the payload with SHA-256.\n"), ALLOW)

    def test_cve_is_allowed(self):
        """A CVE identifier is durable and worth citing."""
        self.assertEqual(self.write("Patched for CVE-2024-1234 upstream.\n"), ALLOW)

    def test_rfc_is_allowed(self):
        """An RFC number is durable and worth citing."""
        self.assertEqual(self.write("Conditional requests follow RFC-7231.\n"), ALLOW)

    def test_toolchain_version_is_allowed(self):
        """A toolchain version shares the shape of a key but names a release."""
        self.assertEqual(self.write("Java early, so the JDK-17 provider lands first.\n"), ALLOW)


class TestBareNumber(HookFixture):
    """A bare number in prose is blocked; an ordinal and a colour are not."""

    def test_bare_number_in_markdown_is_blocked(self):
        """Prose naming a number with no cue is still a citation."""
        self.assertEqual(self.write(f"Guards {ref(515)}: the cart used to decide.\n"), BLOCK)

    def test_bare_number_in_a_comment_is_blocked(self):
        """A comment naming a number with no cue is still a citation."""
        self.assertEqual(self.write(f"// guards {ref(515)}\n", "cart.js"), BLOCK)

    def test_ordinal_rule_is_allowed(self):
        """`rule <n>` counts an item in a list, it does not cite a tracker."""
        self.assertEqual(
            self.write(f"Prose rule {ref(41)} in a file of 40 rules fixes nothing.\n"), ALLOW
        )

    def test_ordinal_line_is_allowed(self):
        """`Line <n>` counts a line."""
        self.assertEqual(self.write(f"# =====[ Line {ref(1)} ]=====\n", "p10k.zsh"), ALLOW)

    def test_hex_colour_with_letters_is_allowed(self):
        """A hex colour is not a number reference."""
        self.assertEqual(self.write("Background is #1a2b3c in the dark theme.\n"), ALLOW)

    def test_six_digit_hex_colour_is_allowed(self):
        """Six digits is a colour, not a plausible issue number."""
        self.assertEqual(self.write("Background is #123456 in the dark theme.\n"), ALLOW)

    def test_number_in_code_is_allowed(self):
        """Outside a comment, source is not prose and is left alone."""
        self.assertEqual(self.write(f'value = data["{ref(5)}"]\n', "load.py"), ALLOW)


class TestDelta(HookFixture):
    """The judgement is on what an edit ADDS, never on what the file already holds."""

    def test_write_carrying_an_existing_reference_through_is_allowed(self):
        """Rewriting a file without adding a reference passes."""
        with tempfile.TemporaryDirectory(dir=self.repo) as tmp:
            path = Path(tmp) / "legacy.md"
            body = f"Guards {ref(515)}: the cart used to decide.\n"
            path.write_text(body, encoding="utf-8")
            code = run_hook("Write", {"file_path": str(path), "content": body + "More prose.\n"})
        self.assertEqual(code, ALLOW)

    def test_write_adding_a_second_reference_is_blocked(self):
        """Adding one to a file that already had one is still adding one."""
        with tempfile.TemporaryDirectory(dir=self.repo) as tmp:
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
                "file_path": str(self.repo / "notes.md"),
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
                "file_path": str(self.repo / "notes.md"),
                "old_string": "Guards the cart.",
                "new_string": f"Guards the cart, see issue {ref(439)}.",
            },
        )
        self.assertEqual(code, BLOCK)


class TestBash(HookFixture):
    """Content written through a heredoc must not bypass the guard."""

    def test_heredoc_body_with_a_citation_is_blocked(self):
        """A file written with `cat > f <<EOF` is file content."""
        command = f"cat > notes.md <<'EOF'\nFixes {ref(12)}\nEOF\n"
        self.assertEqual(run_hook("Bash", {"command": command}), BLOCK)

    def test_grep_for_a_reference_is_allowed(self):
        """Searching for a citation is not writing one."""
        self.assertEqual(run_hook("Bash", {"command": f"grep -rn '{ref(12)}' ."}), ALLOW)


class TestNotebook(HookFixture):
    """A notebook cell is file content like any other."""

    def test_new_source_with_a_citation_is_blocked(self):
        """A citation in a notebook cell is refused."""
        code = run_hook(
            "NotebookEdit",
            {
                "notebook_path": str(self.repo / "analysis.ipynb"),
                "new_source": f"# Fixes {ref(12)}\n",
            },
        )
        self.assertEqual(code, BLOCK)


class TestRepositoryScope(HookFixture):
    """The guard applies inside a git working tree and nowhere else."""

    def test_same_content_outside_a_repository_is_allowed(self):
        """A plan or a note written outside every repository is not a repository artifact."""
        body = f"Guards {ref(515)}: the cart used to decide.\n"
        code = run_hook("Write", {"file_path": str(self.outside / "plan.md"), "content": body})
        self.assertEqual(code, ALLOW)

    def test_same_content_inside_a_repository_is_blocked(self):
        """The identical content is refused once it lands in a repository."""
        body = f"Guards {ref(515)}: the cart used to decide.\n"
        code = run_hook("Write", {"file_path": str(self.repo / "plan.md"), "content": body})
        self.assertEqual(code, BLOCK)

    def test_edit_outside_a_repository_is_allowed(self):
        """An edit is scoped the same way a write is."""
        code = run_hook(
            "Edit",
            {
                "file_path": str(self.outside / "notes.md"),
                "old_string": "Guards the cart.",
                "new_string": f"Guards the cart, see issue {ref(439)}.",
            },
        )
        self.assertEqual(code, ALLOW)

    def test_heredoc_redirected_outside_a_repository_is_allowed(self):
        """A heredoc is judged by where it redirects, not by where the session sits."""
        command = f"cat >> {self.outside}/plan.md <<'EOF'\nFixes {ref(12)}\nEOF\n"
        self.assertEqual(run_hook("Bash", {"command": command}), ALLOW)

    def test_heredoc_redirected_into_a_quoted_repository_path_is_blocked(self):
        """A quoted target names a path, so the quotes must not hide it."""
        command = f"cat >> \"{self.repo}/plan.md\" <<'EOF'\nFixes {ref(12)}\nEOF\n"
        self.assertEqual(run_hook("Bash", {"command": command}), BLOCK)

    def test_heredoc_without_a_redirect_follows_the_session_directory(self):
        """A script on stdin names no file, so the session's own directory answers for it."""
        command = f"python3 - <<'PY'\nprint('Fixes {ref(12)}')\nPY\n"
        self.assertEqual(run_hook("Bash", {"command": command}, cwd=self.outside), ALLOW)
        self.assertEqual(run_hook("Bash", {"command": command}, cwd=self.repo), BLOCK)

    def test_target_behind_a_shell_variable_fails_closed(self):
        """An unexpanded variable is not a path the hook can resolve, so the session answers."""
        command = f"cat >> $OUT/plan.md <<'EOF'\nFixes {ref(12)}\nEOF\n"
        self.assertEqual(run_hook("Bash", {"command": command}, cwd=self.repo), BLOCK)
        self.assertEqual(run_hook("Bash", {"command": command}, cwd=self.outside), ALLOW)

    def test_write_into_a_directory_that_does_not_exist_yet_resolves_upward(self):
        """A new directory inside a tree is still inside it."""
        body = f"Guards {ref(515)}.\n"
        path = str(self.repo / "new" / "deep" / "n.md")
        code = run_hook("Write", {"file_path": path, "content": body})
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
