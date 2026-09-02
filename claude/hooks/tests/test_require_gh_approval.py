#!/usr/bin/env python3
"""Tests for the require-gh-approval PreToolUse hook.

Run: python3 claude/hooks/tests/test_require_gh_approval.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

Two properties matter: nothing that writes to GitHub reaches the API unapproved, and reading
GitHub stays friction-free: a gate that fires on `gh pr view` is a gate that gets switched off.
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "require-gh-approval.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("require_gh_approval", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

NON_PROMPTING_MODES = ["auto", "acceptEdits", "dontAsk", "bypassPermissions"]


def run_hook(command, mode="default", tool="Bash"):
    """Invoke the hook with a payload and return its parsed decision.

    :param command: the shell command the model would run
    :param mode: permission mode reported by the session
    :param tool: tool name to report
    :return: the hookSpecificOutput dict, or None when the hook stayed silent
    """
    payload = json.dumps(
        {
            "tool_name": tool,
            "tool_input": {"command": command},
            "permission_mode": mode,
            "cwd": str(Path.cwd()),
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


class TestWritesAreGated(unittest.TestCase):
    """Anything that speaks as the user must be approved."""

    def test_issue_create(self):
        """Opening an issue is gated."""
        self.assertEqual(run_hook("gh issue create -t x -b y")["permissionDecision"], "ask")

    def test_pr_create(self):
        """Opening a PR is gated."""
        self.assertEqual(run_hook("gh pr create --fill")["permissionDecision"], "ask")

    def test_pr_comment(self):
        """Commenting notifies people and is gated."""
        self.assertEqual(run_hook("gh pr comment 12 -b 'lgtm'")["permissionDecision"], "ask")

    def test_pr_merge(self):
        """Merging is gated."""
        self.assertEqual(run_hook("gh pr merge 12 --squash")["permissionDecision"], "ask")

    def test_pr_review(self):
        """Submitting a review is gated."""
        self.assertEqual(run_hook("gh pr review 12 --approve")["permissionDecision"], "ask")

    def test_release_create(self):
        """Cutting a release is gated."""
        out = run_hook("gh release create 1.0.0 --generate-notes")
        self.assertEqual(out["permissionDecision"], "ask")

    def test_repo_delete(self):
        """Destructive repo operations are gated."""
        self.assertEqual(run_hook("gh repo delete owner/x")["permissionDecision"], "ask")

    def test_secret_set(self):
        """Writing a secret is gated."""
        self.assertEqual(run_hook("gh secret set TOKEN")["permissionDecision"], "ask")

    def test_workflow_run(self):
        """Triggering CI is gated."""
        self.assertEqual(run_hook("gh workflow run deploy.yml")["permissionDecision"], "ask")

    def test_gist_create(self):
        """Publishing a gist is gated."""
        self.assertEqual(run_hook("gh gist create notes.md")["permissionDecision"], "ask")

    def test_global_flag_before_subcommand(self):
        """A global flag and its value are not mistaken for the subcommand."""
        out = run_hook("gh --repo owner/x issue create -t y")
        self.assertEqual(out["permissionDecision"], "ask")

    def test_compound_command(self):
        """A write hidden behind && is caught."""
        out = run_hook("gh pr view 1 && gh pr comment 1 -b hi")
        self.assertEqual(out["permissionDecision"], "ask")

    def test_unknown_subcommand_fails_closed(self):
        """An unrecognised gh command is gated rather than assumed harmless."""
        self.assertEqual(run_hook("gh newthing publish")["permissionDecision"], "ask")

    def test_project_write_verbs(self):
        """The hyphenated project verbs that write are gated, unlike item-list."""
        for cmd in (
            "gh project item-create 4 --title x",
            "gh project item-edit --id X --title y",
            "gh project field-create 4 --name x",
            "gh project delete 4",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(run_hook(cmd)["permissionDecision"], "ask")


class TestApiIsClassifiedByMethod(unittest.TestCase):
    """The bypass a verb denylist misses: gh api with no write verb in it."""

    def test_field_flags_imply_a_post(self):
        """Adding parameters makes gh api a POST, so it is gated."""
        cmd = "gh api repos/owner/x/issues -f title=bug -f body=details"
        self.assertEqual(run_hook(cmd)["permissionDecision"], "ask")

    def test_explicit_write_method(self):
        """An explicit non-GET method is gated."""
        out = run_hook("gh api -X DELETE repos/owner/x/issues/comments/1")
        self.assertEqual(out["permissionDecision"], "ask")

    def test_method_with_equals_form(self):
        """--method=PATCH is recognised."""
        out = run_hook("gh api --method=PATCH repos/owner/x")
        self.assertEqual(out["permissionDecision"], "ask")

    def test_input_flag(self):
        """--input sends a body, so it is gated."""
        self.assertEqual(
            run_hook("gh api repos/owner/x --input b.json")["permissionDecision"], "ask"
        )

    def test_plain_get_is_not_gated(self):
        """A default gh api call only reads."""
        self.assertIsNone(run_hook("gh api repos/owner/x/pulls"))

    def test_explicit_get_with_fields_is_not_gated(self):
        """--method GET with parameters is still a read."""
        self.assertIsNone(run_hook("gh api --method GET search/issues -f q=is:open"))


class TestGraphqlIsClassifiedByOperation(unittest.TestCase):
    """A board read is a POST with a field flag, and must not be gated for looking like one."""

    BOARD_QUERY = (
        "gh api graphql -f query='query($org: String!) { organization(login: $org) "
        "{ projectV2(number: 1) { items(first: 50) { nodes { id } } } } }' -f org=owner"
    )

    def test_board_read_is_not_gated(self):
        """The regression: reading a project board asked for approval every time."""
        self.assertIsNone(run_hook(self.BOARD_QUERY))

    def test_board_write_is_gated(self):
        """A mutation that publishes still needs approval."""
        cmd = "gh api graphql -f query='mutation { addComment(input: {}) { clientMutationId } }'"
        self.assertEqual(run_hook(cmd)["permissionDecision"], "ask")

    def test_board_field_mutation_is_carved_out(self):
        """Setting board Status is bookkeeping the rules mandate, so it is not gated."""
        cmd = (
            "gh api graphql -f query='mutation { updateProjectV2ItemFieldValue"
            "(input: {}) { clientMutationId } }'"
        )
        self.assertIsNone(run_hook(cmd))

    def test_document_the_hook_cannot_read_is_gated(self):
        """A document behind a shell variable is not classifiable, so it fails closed."""
        self.assertEqual(run_hook('gh api graphql -f query="$QUERY"')["permissionDecision"], "ask")


class TestReadsPassThrough(unittest.TestCase):
    """Reading GitHub must stay friction-free."""

    def test_read_only_invocations(self):
        """The common read commands are untouched."""
        for cmd in (
            "gh pr view 12",
            "gh pr list --state open",
            "gh pr diff 12",
            "gh pr checks 12",
            "gh issue list --assignee @me",
            "gh run watch",
            "gh run view 99 --log",
            "gh repo clone owner/x",
            "gh pr checkout 12",
            "gh release download 1.0.0",
            "gh search issues cats",
            "gh status",
            "gh browse",
            "gh project item-list 4",
            "gh project field-list 4",
            "gh project view 4",
        ):
            with self.subTest(cmd=cmd):
                self.assertIsNone(run_hook(cmd))

    def test_issue_develop_is_carved_out(self):
        """The branch-creation step the rules mandate is allowed through."""
        self.assertIsNone(run_hook("gh issue develop 42 --checkout"))

    def test_help_is_not_gated(self):
        """Printing usage touches nothing, so it must not cost an approval."""
        for cmd in ("gh project item-edit --help", "gh issue create --help"):
            with self.subTest(cmd=cmd):
                self.assertIsNone(run_hook(cmd))

    def test_help_bound_as_a_value_is_gated(self):
        """`-t --help` would title a real issue `--help`, so it stays gated."""
        self.assertEqual(run_hook("gh issue create -t --help -b body")["permissionDecision"], "ask")

    def test_board_bookkeeping_is_carved_out(self):
        """Placing an issue on the board and setting its fields notifies nobody."""
        for cmd in (
            "gh project item-add 4 --owner @me --url https://github.com/o/r/issues/N",
            "gh project item-edit --id I --project-id P --field-id F --single-select-option-id S",
            "gh project item-edit --id I --project-id P --field-id F --text 'In Progress'",
            "gh project item-edit --id I --project-id P --field-id F --clear",
        ):
            with self.subTest(cmd=cmd):
                self.assertIsNone(run_hook(cmd))

    def test_draft_issue_prose_stays_gated(self):
        """`item-edit` also rewrites draft-issue prose, which publishes, so it fails closed."""
        for cmd in (
            "gh project item-edit --id I --title 'a new title'",
            "gh project item-edit --id I --body 'a new body'",
            "gh project item-edit --id I --field-id F --text x --title 'smuggled'",
            "gh project item-edit --id I",
            "gh project item-delete --id I",
        ):
            with self.subTest(cmd=cmd):
                self.assertEqual(run_hook(cmd)["permissionDecision"], "ask")

    def test_non_gh_command(self):
        """Unrelated commands are ignored."""
        self.assertIsNone(run_hook("ls -la"))

    def test_non_bash_tool(self):
        """A non-Bash tool call is ignored."""
        self.assertIsNone(run_hook("gh issue create", tool="Edit"))

    def test_prose_mentioning_gh(self):
        """The word in prose is not an invocation."""
        self.assertIsNone(run_hook("echo 'use gh to open the pr'"))

    def test_heredoc_body_mentioning_gh(self):
        """A script written via heredoc is data, not an invocation."""
        self.assertIsNone(run_hook("cat > x.sh <<'EOF'\ngh issue create -t x\nEOF"))

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


class TestModes(unittest.TestCase):
    """Mode handling matches the commit and push gates."""

    def test_every_non_prompting_mode_denies(self):
        """Where a prompt would be auto-approved, the action is denied."""
        for mode in NON_PROMPTING_MODES:
            with self.subTest(mode=mode):
                out = run_hook("gh issue create -t x", mode=mode)
                self.assertEqual(out["permissionDecision"], "deny")

    def test_never_allows(self):
        """No mode produces an allow decision for a write."""
        modes = ["default", "plan"] + NON_PROMPTING_MODES
        decisions = [run_hook("gh issue create -t x", mode=m)["permissionDecision"] for m in modes]
        self.assertNotIn("allow", decisions)


class TestSummary(unittest.TestCase):
    """The prompt must say what would be published, and where."""

    def test_action_and_target_are_named(self):
        """The subcommand and the target repo reach the user."""
        reason = run_hook("gh issue create -R owner/x -t 'Bug'")["permissionDecisionReason"]
        self.assertIn("gh issue create", reason)
        self.assertIn("owner/x", reason)

    def test_full_command_is_shown(self):
        """The content being published is visible, not just the verb."""
        reason = run_hook("gh pr comment 1 -b 'ship it'")["permissionDecisionReason"]
        self.assertIn("ship it", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
