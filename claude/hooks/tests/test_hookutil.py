#!/usr/bin/env python3
"""Tests for the shared hook git helpers, and for the import they depend on.

Run: python3 claude/hooks/tests/test_hookutil.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

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


class CommandPatterns(unittest.TestCase):
    """The patterns two PreToolUse guards now share."""

    def test_short_flag_matches_clusters(self):
        """A letter is found bare and inside a cluster."""
        self.assertTrue(hookutil.short_flag("git commit -a -m x", "a"))
        self.assertTrue(hookutil.short_flag("git commit -am x", "a"))

    def test_short_flag_ignores_long_flags(self):
        """A long flag containing the letter is not that short flag."""
        self.assertFalse(hookutil.short_flag("git commit --amend", "a"))

    def test_short_flag_is_case_sensitive(self):
        """Signing and sign-off must not be confused."""
        self.assertTrue(hookutil.short_flag("git commit -S", "S"))
        self.assertFalse(hookutil.short_flag("git commit -s", "S"))

    def test_strip_heredocs_removes_the_body(self):
        """The body goes, the surrounding command stays."""
        stripped = hookutil.strip_heredocs("cat <<'EOF'\nsecret line\nEOF\nls -la")
        self.assertNotIn("secret line", stripped)
        self.assertIn("ls -la", stripped)
        self.assertIn("cat <<'EOF'", stripped)

    def test_strip_heredocs_handles_dash_form(self):
        """The `<<-` indented form is recognised."""
        self.assertNotIn("body", hookutil.strip_heredocs("cat <<-EOF\n\tbody\n\tEOF"))

    def test_strip_heredocs_leaves_plain_commands(self):
        """A command with no heredoc is returned unchanged."""
        self.assertEqual(hookutil.strip_heredocs("ls -la"), "ls -la")

    def test_heredoc_bodies_is_the_inverse_of_stripping(self):
        """What stripping discards is exactly what this returns."""
        cmd = "cat > f.md <<'EOF'\nline one\nline two\nEOF\nls"
        self.assertEqual(hookutil.heredoc_bodies(cmd), ["line one\nline two"])

    def test_heredoc_bodies_finds_every_body(self):
        """A command with two heredocs yields two bodies."""
        cmd = "cat > a <<'EOF'\nfirst\nEOF\ncat > b <<'EOF'\nsecond\nEOF"
        self.assertEqual(hookutil.heredoc_bodies(cmd), ["first", "second"])

    def test_heredoc_bodies_without_a_heredoc(self):
        """A plain command has no bodies."""
        self.assertEqual(hookutil.heredoc_bodies("ls -la"), [])

    def test_strip_heredocs_survives_an_unterminated_body(self):
        """A missing delimiter must not raise or lose the opening line."""
        self.assertIn("cat <<'EOF'", hookutil.strip_heredocs("cat <<'EOF'\ndangling"))


class GhClassification(unittest.TestCase):
    """The gh helpers shared by require-gh-approval and block-claude-attribution.

    They moved here once a second hook needed them. These assert the shared contract both
    callers rely on: which invocations a command contains, and which of them write.
    """

    def test_invocations_found_across_separators(self):
        """Each gh invocation in a compound command is returned separately."""
        found = hookutil.gh_invocations("gh issue list && gh pr view 3")
        self.assertEqual(found, [["issue", "list"], ["pr", "view", "3"]])

    def test_subcommand_skips_global_flags(self):
        """A global flag and its value are not mistaken for the subcommand."""
        self.assertEqual(
            hookutil.gh_subcommand(["--repo", "owner/name", "pr", "view"]), ("pr", "view")
        )

    def test_write_verb_is_a_write(self):
        """Creating an issue writes."""
        self.assertTrue(hookutil.gh_writes_to_github(["issue", "create", "-t", "x"]))

    def test_read_verb_is_not_a_write(self):
        """Listing issues does not write."""
        self.assertFalse(hookutil.gh_writes_to_github(["issue", "list"]))

    def test_issue_develop_is_carved_out(self):
        """`gh issue develop` publishes only a branch name."""
        self.assertFalse(hookutil.gh_writes_to_github(["issue", "develop", "7"]))

    def test_api_is_classified_by_method(self):
        """A plain `gh api` reads; field flags make it a write."""
        self.assertFalse(hookutil.gh_writes_to_github(["api", "repos/o/n"]))
        self.assertTrue(hookutil.gh_writes_to_github(["api", "repos/o/n", "-f", "title=x"]))

    def test_unrecognised_subcommand_fails_closed(self):
        """An unparseable invocation is treated as a write."""
        self.assertTrue(hookutil.gh_writes_to_github(["--some-new-flag"]))


class GhGraphqlClassification(unittest.TestCase):
    """GraphQL is classified by operation type, because the method rule cannot see past it.

    Every `gh api graphql` call is a POST carrying `-f query=`, so classifying it by method gated
    every project-board read: `projectV2` has no REST endpoint. What the call actually does is in
    the document, and a document that is not a readable literal still fails closed.
    """

    def writes(self, document, flag="-f"):
        """Report whether a graphql call carrying `document` counts as a write.

        :param document: the GraphQL document passed as the query field
        :param flag: the field flag carrying it
        :return: True when the invocation would be gated
        """
        return hookutil.gh_writes_to_github(["api", "graphql", flag, f"query={document}"])

    def test_query_operation_reads(self):
        """The named read a board query is made of."""
        self.assertFalse(self.writes("query Board { organization { login } }"))

    def test_anonymous_shorthand_reads(self):
        """The `{ ... }` shorthand is a query by definition."""
        self.assertFalse(self.writes("{ viewer { login } }"))

    def test_variable_definitions_read(self):
        """A parameterised query is still a query, `$` and all."""
        self.assertFalse(
            self.writes("query B($org: String!, $after: String) { rateLimit { cost } }")
        )

    def test_mutation_operation_writes(self):
        """Changing a board field is a write."""
        self.assertTrue(
            self.writes("mutation { updateProjectV2ItemFieldValue { clientMutationId } }")
        )

    def test_subscription_is_not_a_read(self):
        """Only a query reads; anything else is gated."""
        self.assertTrue(self.writes("subscription { events { id } }"))

    def test_mutation_behind_a_fragment_writes(self):
        """The operation keyword is found wherever it sits at the top level."""
        self.assertTrue(self.writes("fragment F on Issue { id } mutation Go { closeIssue { id } }"))

    def test_second_operation_writes(self):
        """A read operation first does not license the write that follows it."""
        self.assertTrue(
            self.writes("query A { viewer { login } } mutation B { addComment { id } }")
        )

    def test_mutation_shaped_field_name_reads(self):
        """A field inside a selection set is not an operation keyword."""
        self.assertFalse(self.writes("query { node { clientMutationId mutationLog } }"))

    def test_the_word_in_a_string_argument_reads(self):
        """A string literal is data, not an operation."""
        self.assertFalse(self.writes('query { search(query: "mutation", type: ISSUE) { id } }'))

    def test_the_word_in_a_comment_reads(self):
        """A comment is not an operation either."""
        self.assertFalse(self.writes("# mutation\nquery { viewer { login } }"))

    def test_shell_expansion_fails_closed(self):
        """The hook cannot know what a variable holds, so it does not guess."""
        self.assertTrue(self.writes("$QUERY"))
        self.assertTrue(self.writes("$OP { viewer { login } }"))

    def test_document_from_a_file_fails_closed(self):
        """`-F query=@file` reads the document from disk, where the hook cannot follow."""
        self.assertTrue(self.writes("@board.graphql", flag="-F"))

    def test_input_flag_fails_closed(self):
        """--input carries the document in a file or on stdin."""
        self.assertTrue(hookutil.gh_writes_to_github(["api", "graphql", "--input", "q.json"]))

    def test_missing_query_field_fails_closed(self):
        """Nothing to classify is no reason to allow."""
        self.assertTrue(hookutil.gh_writes_to_github(["api", "graphql"]))

    def test_method_flag_does_not_decide(self):
        """gh sends graphql as a POST, so the method says nothing about the operation."""
        tokens = ["api", "graphql", "--method", "POST", "-f", "query={ viewer { login } }"]
        self.assertFalse(hookutil.gh_writes_to_github(tokens))

    def test_rest_endpoint_keeps_the_method_rule(self):
        """Only the graphql endpoint changes; a REST call with fields is still a write."""
        self.assertTrue(hookutil.gh_writes_to_github(["api", "repos/o/n", "-f", "title=x"]))


class GhCommandPosition(unittest.TestCase):
    """`gh` counts as an invocation only where a command can actually start.

    Regression: the word "gh" was matched anywhere in a command's tokens, and the command was
    split on newlines BEFORE being lexed. A multi-line commit message with "gh" on a line of its
    own therefore parsed as a gh invocation and was denied, which is how this was found.
    """

    def gated(self, command):
        """Report whether any gh invocation in `command` would be treated as a write."""
        return any(hookutil.gh_writes_to_github(t) for t in hookutil.gh_invocations(command))

    def test_multiline_quoted_argument_is_not_split(self):
        """A quoted argument spanning lines stays one token, so "gh" inside it is prose."""
        message = 'git commit -m "refactor: x\n\nExplains which gh invocations write.\n"'
        self.assertFalse(self.gated(message))

    def test_bare_word_as_an_argument(self):
        """Searching for the word is not running the command."""
        self.assertFalse(self.gated("grep -rn gh docs/"))

    def test_quoted_prose(self):
        """The word inside a quoted string is not an invocation."""
        self.assertFalse(self.gated("echo 'the gh cli is nice'"))

    def test_piping_a_read_into_a_search_for_the_word(self):
        """Neither half of this is a write."""
        self.assertFalse(self.gated("gh pr view 3 | grep gh"))

    def test_command_position_after_a_separator(self):
        """A real invocation after `&&` is still found."""
        self.assertTrue(self.gated("cd /tmp && gh issue create -t x"))

    def test_separator_without_surrounding_spaces(self):
        """The lexer treats `&&` as an operator even when it is not spaced out."""
        self.assertTrue(self.gated("cd /tmp&&gh issue create -t x"))

    def test_behind_a_wrapper_or_env_assignment(self):
        """A wrapper in front of the command does not hide it."""
        self.assertTrue(self.gated("sudo gh issue create -t x"))
        self.assertTrue(self.gated("FOO=1 gh issue create -t x"))


class GhAssignmentCarveOut(unittest.TestCase):
    """Assigning yourself is bookkeeping the rules mandate; editing the text is publishing.

    `edit` cannot be carved out by verb, because the same subcommand rewrites titles and bodies.
    The carve-out is by flag, and fails closed on anything it does not recognise.
    """

    def writes(self, tokens):
        """Report whether the invocation counts as needing approval."""
        return hookutil.gh_writes_to_github(tokens)

    def test_assigning_self(self):
        """The mundane case the workflow needs."""
        self.assertFalse(self.writes(["issue", "edit", "42", "--add-assignee", "@me"]))

    def test_inline_flag_form(self):
        """`--flag=value` is handled as well as `--flag value`."""
        self.assertFalse(self.writes(["issue", "edit", "42", "--add-assignee=@me"]))

    def test_alongside_a_targeting_flag(self):
        """Naming the repo picks the target without changing it."""
        self.assertFalse(
            self.writes(["issue", "edit", "42", "-R", "owner/repo", "--add-assignee", "@me"])
        )

    def test_unassigning_self(self):
        """Handing work back is the same kind of bookkeeping."""
        self.assertFalse(self.writes(["issue", "edit", "42", "--remove-assignee", "@me"]))

    def test_pull_requests_too(self):
        """`gh pr edit` gets the same treatment."""
        self.assertFalse(self.writes(["pr", "edit", "7", "--add-assignee", "@me"]))

    def test_assigning_someone_else_is_gated(self):
        """Putting work in a colleague's queue notifies them; that is not mundane."""
        self.assertTrue(self.writes(["issue", "edit", "42", "--add-assignee", "a-colleague"]))

    def test_editing_content_alongside_is_gated(self):
        """An assignment must not smuggle a body or title rewrite past the gate."""
        for extra in (["--body", "rewritten"], ["--title", "new"], ["--add-label", "bug"]):
            with self.subTest(extra=extra):
                self.assertTrue(
                    self.writes(["issue", "edit", "42", "--add-assignee", "@me", *extra])
                )

    def test_editing_without_assigning_is_gated(self):
        """The carve-out needs an assignment flag to apply at all."""
        self.assertTrue(self.writes(["issue", "edit", "42", "--body", "rewritten"]))

    def test_unknown_flag_fails_closed(self):
        """A flag the carve-out does not recognise gates the whole invocation."""
        self.assertTrue(
            self.writes(["issue", "edit", "42", "--add-assignee", "@me", "--some-new-flag"])
        )


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
