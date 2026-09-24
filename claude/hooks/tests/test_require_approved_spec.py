#!/usr/bin/env python3
"""Tests for the require-approved-spec PreToolUse gate.

Run: python3 claude/hooks/tests/test_require_approved_spec.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

HOME points at a throwaway directory per test, so the specs folder the hook reads is the
fixture's rather than the developer's own.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _harness import RepoFixture, git, invoke, load_hook, run_standalone
from _hookutil import repo_root, session_project_dir

HOOK = "require-approved-spec.py"
hook = load_hook(HOOK)

BLOCK = 2
ALLOW = 0


def document(kind, status, issue="7"):
    """Build a spec or plan document with front matter.

    :param kind: "spec" or "plan"
    :param status: the status value
    :param issue: the issue number it belongs to
    :return: the document text
    """
    return f"---\nissue: {issue}\nkind: {kind}\nstatus: {status}\n---\n\n# Title\n"


class GateFixture(RepoFixture):
    """A repo on issue branch 7, a private HOME, and a directory outside every repo."""

    def setUp(self):
        """Branch the fixture repo and isolate HOME."""
        super().setUp()
        self.home = Path(tempfile.mkdtemp(prefix="hookhome-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.outside = Path(tempfile.mkdtemp(prefix="hookplain-"))
        self.addCleanup(shutil.rmtree, self.outside, ignore_errors=True)
        git(self.repo, "checkout", "-qb", "7-fix-the-thing")

    @property
    def specs(self):
        """The session specs folder the hook consults for this repo."""
        return session_project_dir(repo_root(self.repo)) / "specs"

    def add_document(self, name, text):
        """Drop a document into the specs folder.

        :param name: file name
        :param text: file body
        """
        self.specs.mkdir(parents=True, exist_ok=True)
        (self.specs / name).write_text(text)

    def approve_both(self):
        """Give issue 7 an approved spec and an approved plan."""
        self.add_document("spec.md", document("spec", "approved"))
        self.add_document("plan.md", document("plan", "approved"))

    def run_tool(self, tool, tool_input, cwd=None):
        """Invoke the hook for one tool call.

        :param tool: tool name
        :param tool_input: the tool's input payload
        :param cwd: session directory, the repo when None
        :return: the HookRun
        """
        payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd or self.repo)}
        return invoke(hook, payload)

    def write_source(self):
        """Attempt a Write of a new source file inside the repo.

        :return: the HookRun
        """
        target = str(self.repo / "src" / "a.ts")
        return self.run_tool("Write", {"file_path": target, "content": "x\n"})


class TestLookup(GateFixture):
    """What counts as an approved spec and plan for the branch's issue."""

    def test_both_approved_passes(self):
        """An approved spec and plan for issue 7 lets the edit through."""
        self.approve_both()
        self.assertEqual(self.write_source().returncode, ALLOW)

    def test_no_specs_folder_blocks(self):
        """With nothing written, both documents are named as missing."""
        run = self.write_source()
        self.assertEqual(run.returncode, BLOCK)
        self.assertIn("no spec", run.stderr)
        self.assertIn("no plan", run.stderr)

    def test_missing_plan_blocks(self):
        """An approved spec alone is not enough."""
        self.add_document("spec.md", document("spec", "approved"))
        run = self.write_source()
        self.assertEqual(run.returncode, BLOCK)
        self.assertIn("no plan", run.stderr)
        self.assertNotIn("no spec", run.stderr)

    def test_draft_plan_blocks(self):
        """A plan that exists but is still a draft is named as unapproved."""
        self.add_document("spec.md", document("spec", "approved"))
        self.add_document("plan.md", document("plan", "draft"))
        run = self.write_source()
        self.assertEqual(run.returncode, BLOCK)
        self.assertIn("plan not approved", run.stderr)

    def test_other_issue_does_not_count(self):
        """Approved documents for a different issue leave this one blocked."""
        self.add_document("spec.md", document("spec", "approved", issue="8"))
        self.add_document("plan.md", document("plan", "approved", issue="8"))
        self.assertEqual(self.write_source().returncode, BLOCK)

    def test_malformed_front_matter_is_named(self):
        """A document the hook cannot parse is reported with the reason."""
        self.add_document("bad.md", "---\nissue 7\n---\n")
        run = self.write_source()
        self.assertEqual(run.returncode, BLOCK)
        self.assertIn("bad.md: line 2", run.stderr)

    def test_unclosed_front_matter_is_named(self):
        """Front matter with no closing fence is reported."""
        self.add_document("open.md", "---\nissue: 7\n")
        self.assertIn("never closed", self.write_source().stderr)

    def test_documents_without_front_matter_are_ignored(self):
        """Older notes in the folder neither count nor get in the way."""
        self.approve_both()
        self.add_document("old-notes.md", "# Notes\n")
        self.assertEqual(self.write_source().returncode, ALLOW)


class TestScope(GateFixture):
    """Where the gate applies at all."""

    def test_non_issue_branch_passes(self):
        """A branch without a leading issue number is not gated."""
        git(self.repo, "checkout", "-qb", "feature-without-number")
        self.assertEqual(self.write_source().returncode, ALLOW)

    def test_outside_repository_passes(self):
        """A write outside every repository is none of the gate's business."""
        run = self.run_tool("Write", {"file_path": str(self.outside / "a.ts"), "content": "x"})
        self.assertEqual(run.returncode, ALLOW)

    def test_edit_is_gated(self):
        """Edit goes through the same gate as Write."""
        edit = {"file_path": str(self.repo / "baseline.md"), "old_string": "a", "new_string": "b"}
        self.assertEqual(self.run_tool("Edit", edit).returncode, BLOCK)

    def test_notebook_edit_is_gated(self):
        """NotebookEdit names its file differently and is still gated."""
        edit = {"notebook_path": str(self.repo / "n.ipynb"), "new_source": "x"}
        self.assertEqual(self.run_tool("NotebookEdit", edit).returncode, BLOCK)


class TestBash(GateFixture):
    """Shell commands that write into the repo on an unapproved issue branch."""

    def bash(self, command):
        """Run the hook over a Bash command from inside the repo.

        :param command: the shell command
        :return: hook exit code
        """
        return self.run_tool("Bash", {"command": command}).returncode

    def test_writes_block(self):
        """Every recognised write form is refused without approval."""
        for command in (
            "python3 - <<'EOF'\nprint(1)\nEOF",
            "sed -i '' 's/a/b/' baseline.md",
            "perl -pi -e 's/a/b/' baseline.md",
            "cat > src/a.ts <<'EOF'\nx\nEOF",
            "printf x >> baseline.md",
            "tee baseline.md < /dev/null",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), BLOCK)

    def test_reads_and_runs_pass(self):
        """Commands that write nothing into the repo pass."""
        for command in (
            "npm test 2>&1 | tail -5",
            "git status",
            'echo "sed -i is gated"',
            "ls > /dev/null",
            "grep -rn foo src",
            f"printf x > {self.outside}/n.txt",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.bash(command), ALLOW)

    def test_redirect_after_cd_into_repo_blocks(self):
        """A relative redirect resolves where the command cd's to, not the session directory."""
        command = f"cd {self.repo} && printf x > b.txt"
        run = self.run_tool("Bash", {"command": command}, self.outside)
        self.assertEqual(run.returncode, BLOCK)

    def test_approval_unblocks_writes(self):
        """With both documents approved, shell writes go through."""
        self.approve_both()
        self.assertEqual(self.bash("python3 - <<'EOF'\nprint(1)\nEOF"), ALLOW)


class TestSelfApproval(GateFixture):
    """Claude cannot leave a session spec or plan reading approved."""

    def session_doc(self, text=None):
        """Path to a document in a session specs folder, optionally created.

        :param text: body to write first, or None to leave it absent
        :return: the Path
        """
        path = self.home / ".claude" / "projects" / "-some-project" / "specs" / "s.md"
        if text is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return path

    def test_write_approved_document_blocks(self):
        """Writing a document already marked approved is refused."""
        target = str(self.session_doc())
        run = self.run_tool(
            "Write", {"file_path": target, "content": document("spec", "approved")}, self.outside
        )
        self.assertEqual(run.returncode, BLOCK)
        self.assertIn("only the user", run.stderr)

    def test_write_draft_document_passes(self):
        """A draft is exactly what Claude should write."""
        target = str(self.session_doc())
        run = self.run_tool(
            "Write", {"file_path": target, "content": document("spec", "draft")}, self.outside
        )
        self.assertEqual(run.returncode, ALLOW)

    def test_edit_flipping_status_blocks(self):
        """Changing draft to approved is refused."""
        target = str(self.session_doc(document("spec", "draft")))
        edit = {"file_path": target, "old_string": "draft", "new_string": "approved"}
        self.assertEqual(self.run_tool("Edit", edit, self.outside).returncode, BLOCK)

    def test_edit_inside_approved_document_blocks(self):
        """An approved document is frozen, whatever the edit touches."""
        target = str(self.session_doc(document("spec", "approved")))
        edit = {"file_path": target, "old_string": "# Title", "new_string": "# Better"}
        self.assertEqual(self.run_tool("Edit", edit, self.outside).returncode, BLOCK)

    def test_shell_rewrite_blocks(self):
        """An in-place shell edit toward approved is refused."""
        target = self.session_doc(document("spec", "draft"))
        command = f"sed -i '' 's/draft/approved/' {target}"
        self.assertEqual(
            self.run_tool("Bash", {"command": command}, self.outside).returncode, BLOCK
        )

    def test_shell_read_passes(self):
        """Checking a status from the shell writes nothing and passes."""
        target = self.session_doc(document("spec", "approved"))
        command = f"grep approved {target}"
        self.assertEqual(
            self.run_tool("Bash", {"command": command}, self.outside).returncode, ALLOW
        )

    def test_specs_folder_elsewhere_passes(self):
        """Only session specs folders are protected, not any folder named specs."""
        target = str(self.outside / "specs" / "x.md")
        run = self.run_tool(
            "Write", {"file_path": target, "content": document("spec", "approved")}, self.outside
        )
        self.assertEqual(run.returncode, ALLOW)


class TestPayload(unittest.TestCase):
    """A hook that cannot read its payload must never wedge the session."""

    def test_malformed_payload_allows(self):
        """Unreadable stdin exits 0."""
        self.assertEqual(run_standalone(HOOK, stdin="not json").returncode, ALLOW)

    def test_unrelated_tool_allows(self):
        """A tool that writes nothing is ignored."""
        run = invoke(hook, {"tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"}})
        self.assertEqual(run.returncode, ALLOW)


if __name__ == "__main__":
    unittest.main(verbosity=2)
