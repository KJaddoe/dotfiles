#!/usr/bin/env python3
"""Tests for the undocumented-env-vars Stop hook.

Run: python3 claude/hooks/tests/test_undocumented_env_vars.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import json
import os
import tempfile
import unittest

from _harness import RepoFixture, git, load_hook, run_standalone

hook = load_hook("undocumented-env-vars.py")

SECRET = "sk-live-51H8xQ2eZvKYlo0THISisNOTreal"


class EnvVarFixture(RepoFixture):
    """The shared repo fixture, with a JavaScript baseline and this hook's own invocation."""

    baseline = ("baseline.js", "const a = 1;\n")

    def run_hook(self, mode, cwd=None):
        """Invoke the hook with the given mode.

        Spawned rather than called in this process: the mode and the home directory are read from
        the ENVIRONMENT, which a hook resolves at import time and an in-process call cannot vary.

        :param mode: DOCS_ENV_HOOK_MODE value
        :param cwd: cwd reported to the hook, defaults to the fixture repo
        :return: CompletedProcess
        """
        return run_standalone(
            "undocumented-env-vars.py",
            stdin=json.dumps({"cwd": str(cwd or self.repo), "stop_hook_active": False}),
            env={
                **os.environ,
                "DOCS_ENV_HOOK_MODE": mode,
                "HOME": str(self.repo / "fakehome"),
            },
        )


class TestDetection(EnvVarFixture):
    """Happy path and core detection behaviour."""

    def test_undocumented_var_is_flagged(self):
        """An added env var with no documentation is reported."""
        self.write("api.js", "const k = process.env.STRIPE_API_KEY;\n")
        self.assertEqual(hook.find_undocumented(self.repo), ["STRIPE_API_KEY"])

    def test_documented_in_env_example_is_clean(self):
        """A var present in .env.example is not reported."""
        self.write("api.js", "const k = process.env.STRIPE_API_KEY;\n")
        self.write(".env.example", "STRIPE_API_KEY=pk_test_placeholder\n")
        self.assertEqual(hook.find_undocumented(self.repo), [])

    def test_documented_in_docs_markdown_is_clean(self):
        """A var documented under docs/ is not reported."""
        self.write("api.js", "const k = process.env.STRIPE_API_KEY;\n")
        self.write("docs/configuration.md", "| STRIPE_API_KEY | billing key | 1Password |\n")
        self.assertEqual(hook.find_undocumented(self.repo), [])

    def test_untracked_file_is_scanned(self):
        """Brand-new untracked files are scanned, not just tracked diffs."""
        self.write("brand-new.py", 'k = os.environ["SENDGRID_TOKEN"]\n')
        self.assertEqual(hook.find_undocumented(self.repo), ["SENDGRID_TOKEN"])

    def test_dotnet_and_python_accessors(self):
        """Non-JS accessors are detected across the stacks in use."""
        self.write("Config.cs", 'var v = Environment.GetEnvironmentVariable("DB_PASSWORD");\n')
        self.write("settings.py", 'v = os.getenv("REDIS_URL")\n')
        self.assertEqual(hook.find_undocumented(self.repo), ["DB_PASSWORD", "REDIS_URL"])


class TestBoundaries(EnvVarFixture):
    """Edge and boundary conditions."""

    def test_preexisting_var_is_not_flagged(self):
        """Vars already committed and untouched are out of scope: additions only."""
        self.write("legacy.js", "const k = process.env.OLD_UNDOCUMENTED;\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "legacy")
        self.assertEqual(hook.find_undocumented(self.repo), [])

    def test_platform_vars_ignored(self):
        """Well-known platform vars never count as project config."""
        self.write("app.js", "const e = process.env.NODE_ENV; const p = process.env.PATH;\n")
        self.assertEqual(hook.find_undocumented(self.repo), [])

    def test_clean_repo_reports_nothing(self):
        """A repo with no changes produces no findings."""
        self.assertEqual(hook.find_undocumented(self.repo), [])

    def test_test_files_are_not_scanned(self):
        """Regression: fake env vars in test fixtures must never be reported.

        Found by dry-running the hook against this repo, where its own test fixtures
        produced six false positives.
        """
        self.write("tests/test_api.py", 'k = os.environ["FAKE_FIXTURE_KEY"]\n')
        self.write("src/api.spec.ts", "const k = process.env.ANOTHER_FAKE;\n")
        self.write("__tests__/thing.js", "const k = process.env.THIRD_FAKE;\n")
        self.assertEqual(hook.find_undocumented(self.repo), [])

    def test_real_source_still_scanned_alongside_tests(self):
        """Excluding tests must not suppress findings in real source files."""
        self.write("tests/test_api.py", 'k = os.environ["FAKE_FIXTURE_KEY"]\n')
        self.write("src/api.js", "const k = process.env.REAL_CONFIG_VAR;\n")
        self.assertEqual(hook.find_undocumented(self.repo), ["REAL_CONFIG_VAR"])

    def test_tracked_file_edit_is_attributed_to_its_path(self):
        """Diff parsing must attribute added lines to the right file before excluding."""
        self.write("baseline.js", "const k = process.env.EDITED_FILE_VAR;\n")
        self.assertEqual(hook.find_undocumented(self.repo), ["EDITED_FILE_VAR"])

    def test_non_git_directory_exits_zero(self):
        """Outside a git repo the hook is a no-op."""
        with tempfile.TemporaryDirectory() as plain:
            result = self.run_hook("enforce", cwd=plain)
        self.assertEqual(result.returncode, 0)

    def test_malformed_stdin_exits_zero(self):
        """Unparseable stdin must never break the session."""
        result = run_standalone(
            "undocumented-env-vars.py",
            stdin="not json",
            env={**os.environ, "DOCS_ENV_HOOK_MODE": "enforce"},
        )
        self.assertEqual(result.returncode, 0)

    def test_stop_hook_active_exits_zero(self):
        """stop_hook_active short-circuits, preventing a block loop."""
        self.write("api.js", "const k = process.env.STRIPE_API_KEY;\n")
        result = run_standalone(
            "undocumented-env-vars.py",
            stdin=json.dumps({"cwd": str(self.repo), "stop_hook_active": True}),
            env={**os.environ, "DOCS_ENV_HOOK_MODE": "enforce"},
        )
        self.assertEqual(result.returncode, 0)


class TestModes(EnvVarFixture):
    """Mode switching must behave exactly as advertised."""

    def setUp(self):
        """Add an undocumented env var to every mode fixture."""
        super().setUp()
        self.write("api.js", "const k = process.env.STRIPE_API_KEY;\n")

    def test_enforce_mode_blocks(self):
        """enforce exits 2 so the reason is fed back to the model."""
        result = self.run_hook("enforce")
        self.assertEqual(result.returncode, 2)
        self.assertIn("STRIPE_API_KEY", result.stderr)

    def test_dry_run_never_blocks(self):
        """dry-run reports the finding but always exits 0."""
        result = self.run_hook("dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertIn("STRIPE_API_KEY", result.stderr)
        self.assertIn("[dry-run]", result.stderr)

    def test_off_mode_is_silent(self):
        """off produces no output and no block."""
        result = self.run_hook("off")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr.strip(), "")

    def test_default_mode_is_dry_run(self):
        """Absent configuration the hook must not block."""
        env = {k: v for k, v in os.environ.items() if k != "DOCS_ENV_HOOK_MODE"}
        env["HOME"] = str(self.repo / "fakehome")
        result = run_standalone(
            "undocumented-env-vars.py",
            stdin=json.dumps({"cwd": str(self.repo), "stop_hook_active": False}),
            env=env,
        )
        self.assertEqual(result.returncode, 0)


class TestSecretsMustNotLeak(EnvVarFixture):
    """Must-not-work cases: a secret value may never escape into output or logs."""

    def test_secret_value_absent_from_stderr(self):
        """A literal secret in the diff must not appear in the hook's message."""
        self.write("api.js", f'const k = process.env.STRIPE_API_KEY || "{SECRET}";\n')
        result = self.run_hook("enforce")
        self.assertEqual(result.returncode, 2)
        self.assertIn("STRIPE_API_KEY", result.stderr)
        self.assertNotIn(SECRET, result.stderr)

    def test_secret_value_absent_from_log(self):
        """A literal secret in the diff must not be written to the dry-run log."""
        self.write("api.js", f'const k = process.env.STRIPE_API_KEY || "{SECRET}";\n')
        result = self.run_hook("dry-run")
        self.assertEqual(result.returncode, 0)
        log = self.repo / "fakehome" / ".claude" / "logs" / "env-doc-hook.log"
        self.assertTrue(log.exists(), "dry-run should have written a log entry")
        contents = log.read_text()
        self.assertIn("STRIPE_API_KEY", contents)
        self.assertNotIn(SECRET, contents)

    def test_assignment_value_is_never_captured(self):
        """Extraction captures names only, never the assigned value."""
        found = hook.extract_env_vars([f'process.env.TOKEN = "{SECRET}"'])
        self.assertEqual(found, {"TOKEN"})
        self.assertNotIn(SECRET, "".join(found))


if __name__ == "__main__":
    unittest.main(verbosity=2)
