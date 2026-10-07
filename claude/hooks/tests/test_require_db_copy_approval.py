#!/usr/bin/env python3
"""Tests for the require-db-copy-approval PreToolUse hook.

Run: python3 claude/hooks/tests/test_require_db_copy_approval.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import unittest

from _harness import (
    NON_PROMPTING_MODES,
    PROMPTING_MODES,
    bash_decision,
    load_hook,
    run_standalone,
)

HOOK = "require-db-copy-approval.py"
hook = load_hook(HOOK)


def run_hook(command, mode="default", tool="Bash"):
    """Ask the gate what it would decide about `command`.

    :param command: the shell command the model would run
    :param mode: permission mode reported by the session
    :param tool: tool name to report
    :return: the hookSpecificOutput dict, or None when the hook stayed silent
    """
    return bash_decision(hook, command, mode, tool)


def gated(command):
    """Report whether a command would be put to the user.

    :param command: the shell command the model would run
    :return: True when the hook returns a decision
    """
    return run_hook(command) is not None


class TestCopiesAreGated(unittest.TestCase):
    """Every way a backup or restore reaches SQL Server from the shell is gated."""

    def test_backup_in_a_query_flag(self):
        """A backup passed with -Q is gated."""
        self.assertTrue(
            gated("sqlcmd -S localhost -Q \"BACKUP DATABASE AppDb TO DISK='/tmp/a.bak'\"")
        )

    def test_restore_as_a_new_database(self):
        """Restoring a backup under a new name is how a per-PR copy is made."""
        self.assertTrue(
            gated(
                "docker exec db sqlcmd -Q \"RESTORE DATABASE AppDb_pr1 FROM DISK='/b/a.bak' "
                "WITH MOVE 'AppDb' TO '/d/AppDb_pr1.mdf'\""
            )
        )

    def test_statement_in_a_heredoc_fed_to_sqlcmd(self):
        """A heredoc body fed to sqlcmd is executed, so it is scanned."""
        self.assertTrue(
            gated("sqlcmd -S localhost <<'SQL'\nBACKUP DATABASE AppDb TO DISK='x'\nSQL")
        )

    def test_statement_echoed_into_sqlcmd(self):
        """Printed text piped into sqlcmd is executed, so it is scanned."""
        self.assertTrue(gated("echo \"RESTORE DATABASE AppDb FROM DISK='x'\" | sqlcmd"))

    def test_lower_case_and_spread_out(self):
        """T-SQL keywords are case-insensitive and take any whitespace between them."""
        self.assertTrue(gated("sqlcmd -Q \"backup\n   database AppDb to disk='x'\""))

    def test_log_backup_and_restore(self):
        """Log backups and restores are the same waste and are gated too."""
        self.assertTrue(gated("sqlcmd -Q \"BACKUP LOG AppDb TO DISK='x'\""))
        self.assertTrue(gated("sqlcmd -Q \"RESTORE LOG AppDb FROM DISK='x'\""))


class TestOtherCommandsPassThrough(unittest.TestCase):
    """What neither backs up nor restores is left alone."""

    def test_read_only_restore_variants(self):
        """Inspecting a backup file creates nothing."""
        for verb in ("FILELISTONLY", "HEADERONLY", "VERIFYONLY"):
            with self.subTest(verb=verb):
                self.assertFalse(gated(f"sqlcmd -Q \"RESTORE {verb} FROM DISK='x'\""))

    def test_ordinary_queries(self):
        """Queries against the database under test are what the rule asks for."""
        self.assertFalse(gated('sqlcmd -Q "SELECT name FROM sys.databases"'))
        self.assertFalse(gated('sqlcmd -Q "EXEC dbo.usp_Example"'))

    def test_keyword_inside_an_identifier(self):
        """A word that merely ends in BACKUP is not the statement."""
        self.assertFalse(gated('sqlcmd -Q "SELECT * FROM NIGHTLYBACKUP DATABASES"'))

    def test_other_tools_are_ignored(self):
        """The gate only reads Bash calls."""
        self.assertIsNone(run_hook("BACKUP DATABASE AppDb TO DISK='x'", tool="Write"))


class TestModeHandling(unittest.TestCase):
    """The decision follows the shared approval contract: ask where possible, never allow."""

    command = "sqlcmd -Q \"BACKUP DATABASE AppDb TO DISK='x'\""

    def test_prompting_modes_ask(self):
        """Every mode that renders a dialog gets one."""
        for mode in PROMPTING_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(run_hook(self.command, mode)["permissionDecision"], "ask")

    def test_non_prompting_modes_deny(self):
        """A mode that cannot prompt is denied rather than allowed."""
        for mode in NON_PROMPTING_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(run_hook(self.command, mode)["permissionDecision"], "deny")

    def test_reason_names_this_rule(self):
        """The prompt cites the local-database rule, not the CLAUDE.md working preferences."""
        reason = run_hook(self.command)["permissionDecisionReason"]
        self.assertIn("tested in place", reason)
        self.assertNotIn("Working Preferences", reason)

    def test_summary_lists_each_statement_once(self):
        """A command repeating a statement names it once."""
        reason = run_hook(
            "sqlcmd -Q \"BACKUP DATABASE A TO DISK='a'; backup database B TO DISK='b'; "
            "RESTORE DATABASE C FROM DISK='a'\""
        )["permissionDecisionReason"]
        self.assertIn("runs BACKUP DATABASE, RESTORE DATABASE.", reason)


class TestMalformedInput(unittest.TestCase):
    """A payload the hook cannot read never takes the tool call down."""

    def test_non_json_stdin(self):
        """Garbage on stdin exits cleanly and decides nothing."""
        result = run_standalone(HOOK, stdin="not json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_missing_command(self):
        """A Bash payload without a command decides nothing."""
        self.assertIsNone(run_hook(""))


if __name__ == "__main__":
    unittest.main()
