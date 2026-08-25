#!/usr/bin/env python3
"""Tests for the docs-coverage-floor Stop hook.

Run: python3 claude/hooks/tests/test_docs_coverage_floor.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "docs-coverage-floor.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("docs_coverage_floor", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

FULL_README = """
# Widget Service

Widget Service keeps warehouse widgets in step with the ledger.

## Glossary

A *widget* is one physical unit; a *consignment* is a shipment of them.

## Maintainers

Owned by the platform team; who to ask: the on-call platform engineer.

## Prerequisites

Node 22 and Docker. Install with `npm install`.

## Architecture

The repository layout splits api/ from worker/.

## Running

`docker compose up` starts everything.

## Testing

Run `npm test` for the unit tests.

## Configuration

Every environment variable is listed in `.env.example`.

## Deployment

Deploy by pushing to main.

## Rolling back

To roll back, redeploy the previous tag from the Actions tab.
"""


def git(repo, *args):
    """Run a git command in `repo`, raising on failure.

    :param repo: repository path
    :param args: git arguments
    """
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class RepoFixture(unittest.TestCase):
    """Base fixture creating a throwaway git repo."""

    def setUp(self):
        """Create a temp git repo with an initial commit.

        The repo is initialised from an empty template so the developer's own
        `init.templateDir` (which installs this repo's pre-commit hook) cannot reach into the
        fixture and reject its throwaway files.
        """
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        empty_template = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty_template, ignore_errors=True)
        git(self.repo, "init", "-q", f"--template={empty_template}")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "test")
        (self.repo / "baseline.txt").write_text("x\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "init")

    def write(self, name, content):
        """Write a file inside the fixture repo, creating parent directories.

        :param name: repo-relative path
        :param content: file contents
        """
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def make_deployed_service(self, readme=FULL_README):
        """Turn the fixture into a fully documented deployed service.

        :param readme: README contents to write
        """
        self.write("Dockerfile", "FROM node:22-alpine\n")
        self.write("README.md", readme)

    def run_hook(self, mode=None, stop_hook_active=False, stdin=None):
        """Invoke the hook as a subprocess the way Claude Code does.

        :param mode: value for DOCS_FLOOR_HOOK_MODE, or None to leave it unset
        :param stop_hook_active: value for the payload's stop_hook_active flag
        :param stdin: raw stdin override, bypassing JSON construction
        :return: CompletedProcess
        """
        # HOME must sit OUTSIDE the repo: Python caches bytecode under
        # $HOME/Library/Caches on macOS, and inside the repo those files read as untracked
        # work, so a tree the test just committed would look dirty to the hook.
        env = {"HOME": str(self.home), "PATH": subprocess.os.environ.get("PATH", "")}
        if mode:
            env["DOCS_FLOOR_HOOK_MODE"] = mode
        payload = json.dumps({"cwd": str(self.repo), "stop_hook_active": stop_hook_active})
        return subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=stdin if stdin is not None else payload,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )


class TestArchetypeDetection(RepoFixture):
    """Classification of a repo into project kinds."""

    def test_dockerfile_is_a_deployed_service(self):
        """A Dockerfile marks the repo as a deployed service."""
        self.write("Dockerfile", "FROM alpine\n")
        self.assertIn("deployed-service", hook.detect_archetypes(self.repo))

    def test_deploy_workflow_is_a_deployed_service(self):
        """A deploy workflow marks the repo as a deployed service."""
        self.write(".github/workflows/deploy-dev.yml", "name: Deploy\n")
        self.assertIn("deployed-service", hook.detect_archetypes(self.repo))

    def test_package_bin_is_a_cli(self):
        """A package.json `bin` entry marks the repo as a CLI."""
        self.write("package.json", json.dumps({"name": "t", "bin": {"t": "./cli.js"}}))
        self.assertIn("cli", hook.detect_archetypes(self.repo))

    def test_private_package_is_not_a_library(self):
        """A private package is an app, not a published library."""
        self.write("package.json", json.dumps({"name": "t", "main": "i.js", "private": True}))
        self.assertNotIn("library", hook.detect_archetypes(self.repo))

    def test_published_package_is_a_library(self):
        """A non-private package with an entry point is a library."""
        self.write("package.json", json.dumps({"name": "t", "main": "index.js"}))
        self.assertIn("library", hook.detect_archetypes(self.repo))

    def test_dotbot_config_is_infra(self):
        """A dotbot manifest marks the repo as infra/dotfiles."""
        self.write("dotbot.conf.yaml", "- link:\n")
        self.assertIn("infra", hook.detect_archetypes(self.repo))

    def test_archetypes_union(self):
        """A repo that is several kinds at once reports all of them."""
        self.write("Dockerfile", "FROM alpine\n")
        self.write("package.json", json.dumps({"name": "t", "bin": {"t": "./c.js"}}))
        self.assertEqual(["cli", "deployed-service"], hook.detect_archetypes(self.repo))

    def test_malformed_package_json_does_not_crash(self):
        """Unparseable JSON is ignored rather than raising."""
        self.write("package.json", "{ not json")
        self.assertEqual([], hook.detect_archetypes(self.repo))


class TestGapDetection(RepoFixture):
    """Which floor topics count as covered."""

    def test_fully_documented_service_has_no_gaps(self):
        """The happy path: every floor topic is mentioned, so nothing is reported."""
        self.make_deployed_service()
        archetypes, missing = hook.find_gaps(self.repo)
        self.assertEqual(["deployed-service"], archetypes)
        self.assertEqual([], missing)

    def test_missing_rollback_is_reported(self):
        """The 3-of-3 case: a deployed service documenting everything but rollback."""
        self.make_deployed_service(
            FULL_README.replace("## Rolling back", "## Notes").replace(
                "To roll back, redeploy the previous tag from the Actions tab.", "Nothing yet."
            )
        )
        _, missing = hook.find_gaps(self.repo)
        self.assertIn("rollback", missing)

    def test_rollback_not_required_without_deployment(self):
        """A plain library is never asked for a rollback procedure."""
        self.write("package.json", json.dumps({"name": "t", "main": "index.js"}))
        self.write("README.md", FULL_README)
        _, missing = hook.find_gaps(self.repo)
        self.assertNotIn("rollback", missing)

    def test_scaffold_readme_fails_what_it_is(self):
        """A generated README describes the generator, not the project."""
        self.write("Dockerfile", "FROM alpine\n")
        self.write("README.md", "# App\n\nThis project was generated using Angular CLI 21.2.6.\n")
        _, missing = hook.find_gaps(self.repo)
        self.assertIn("what-it-is", missing)

    def test_nest_starter_readme_fails_what_it_is(self):
        """The Nest starter blurb is recognised as boilerplate."""
        self.write("README.md", "Nest framework TypeScript starter repository.\n")
        _, missing = hook.find_gaps(self.repo)
        self.assertIn("what-it-is", missing)

    def test_empty_readme_fails_what_it_is(self):
        """An empty README covers nothing."""
        self.write("README.md", "   \n")
        _, missing = hook.find_gaps(self.repo)
        self.assertIn("what-it-is", missing)

    def test_repo_with_no_docs_reports_the_whole_base_floor(self):
        """A repo shipping no documentation is missing every base topic."""
        _, missing = hook.find_gaps(self.repo)
        for slug in hook.BASE_TOPICS:
            self.assertIn(slug, missing)

    def test_docs_subdirectory_counts(self):
        """Evidence in docs/ counts, not just the README."""
        self.write("README.md", "# Widget Service\n\nKeeps widgets in step.\n")
        self.write("docs/architecture.md", "Repository layout: api/ and worker/.\n")
        _, missing = hook.find_gaps(self.repo)
        self.assertNotIn("structure", missing)

    def test_dot_env_reference_counts_as_config(self):
        """Regression: `\\b` before a literal dot never matches, so `.env` was missed."""
        self.write("README.md", "# Svc\n\nCopy `.env.example` to `.env` for local development.\n")
        _, missing = hook.find_gaps(self.repo)
        self.assertNotIn("config-env", missing)

    def test_npm_run_test_counts_as_testing(self):
        """Regression: `npm t(est)?` missed the `npm run test` form."""
        self.write("README.md", "# Svc\n\n## Run tests\n\n`npm run test`\n")
        _, missing = hook.find_gaps(self.repo)
        self.assertNotIn("how-to-test", missing)

    def test_install_script_counts_as_running(self):
        """An infra repo is run by its install script, not by a dev server."""
        self.write("README.md", "# Dotfiles\n\nRun `./install` to set everything up.\n")
        _, missing = hook.find_gaps(self.repo)
        self.assertNotIn("how-to-run", missing)

    def test_test_command_in_a_table_row_counts(self):
        """Regression: a docs table row labelled Test documents testing just as well as prose."""
        self.write("README.md", "# Svc\n\nA service.\n")
        self.write("docs/architecture.md", "| Task | Command |\n| Test | `python3 t.py` |\n")
        _, missing = hook.find_gaps(self.repo)
        self.assertNotIn("how-to-test", missing)

    def test_infra_repo_is_not_asked_for_a_glossary(self):
        """A dotfiles repo has no business domain, so the glossary topic is exempt."""
        self.write("dotbot.conf.yaml", "- link:\n")
        self.write("README.md", "# Dotfiles\n")
        archetypes, missing = hook.find_gaps(self.repo)
        self.assertIn("infra", archetypes)
        self.assertNotIn("glossary", missing)

    def test_ownership_and_glossary_are_required(self):
        """The newcomer-shippability additions are part of the base floor."""
        self.write("README.md", "# Widget Service\n\nKeeps widgets in step with the ledger.\n")
        _, missing = hook.find_gaps(self.repo)
        self.assertIn("ownership", missing)
        self.assertIn("glossary", missing)


class TestHookBehaviour(RepoFixture):
    """Mode handling and the conditions under which the hook stays silent."""

    def make_gap_with_uncommitted_work(self):
        """Create a repo that has a floor gap and uncommitted changes."""
        self.write("Dockerfile", "FROM alpine\n")
        self.write("README.md", "# App\n\nThis project was generated using Angular CLI.\n")

    def test_enforce_blocks(self):
        """Enforce mode exits 2 so the finding reaches the model."""
        self.make_gap_with_uncommitted_work()
        result = self.run_hook(mode="enforce")
        self.assertEqual(2, result.returncode)
        self.assertIn("coverage floor", result.stderr)

    def test_dry_run_never_blocks(self):
        """Dry-run reports on stderr but exits 0."""
        self.make_gap_with_uncommitted_work()
        result = self.run_hook()
        self.assertEqual(0, result.returncode)
        self.assertIn("[dry-run]", result.stderr)

    def test_off_is_a_noop(self):
        """Off mode reports nothing even when the floor is unmet."""
        self.make_gap_with_uncommitted_work()
        result = self.run_hook(mode="off")
        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)

    def test_clean_tree_stays_quiet(self):
        """Reading a repo without changing it must not nag, gaps or not."""
        self.make_gap_with_uncommitted_work()
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "add app")
        result = self.run_hook(mode="enforce")
        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)

    def test_stop_hook_active_short_circuits(self):
        """A re-entrant Stop hook invocation exits immediately."""
        self.make_gap_with_uncommitted_work()
        result = self.run_hook(mode="enforce", stop_hook_active=True)
        self.assertEqual(0, result.returncode)

    def test_malformed_stdin_exits_cleanly(self):
        """Garbage on stdin must not raise or block the session."""
        self.make_gap_with_uncommitted_work()
        result = self.run_hook(mode="enforce", stdin="not json")
        self.assertEqual(0, result.returncode)

    def test_log_records_slugs_only(self):
        """The log carries topic slugs, never documentation text."""
        self.make_gap_with_uncommitted_work()
        self.run_hook()
        log = self.home / ".claude" / "logs" / "docs-floor-hook.log"
        self.assertTrue(log.exists())
        self.assertIn("what-it-is", log.read_text(encoding="utf-8"))
        self.assertNotIn("Angular CLI", log.read_text(encoding="utf-8"))


class TestCli(RepoFixture):
    """The standalone entry point a CI job calls."""

    def test_cli_passes_on_a_documented_repo(self):
        """Exit 0 and a one-line OK when the floor is met."""
        self.make_deployed_service()
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "--path", str(self.repo)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode)
        self.assertIn("OK", result.stdout)

    def test_cli_fails_on_a_gap(self):
        """Exit 1 naming the missing topic, which is what fails a CI job."""
        self.make_deployed_service(
            FULL_README.replace("## Rolling back", "## Notes").replace(
                "To roll back, redeploy the previous tag from the Actions tab.", "Nothing yet."
            )
        )
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "--path", str(self.repo)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("how to roll back", result.stderr)

    def test_cli_reports_regardless_of_uncommitted_work(self):
        """Unlike the hook, the CLI checks a clean tree too."""
        self.write("Dockerfile", "FROM alpine\n")
        self.write("README.md", "# App\n\nThis project was generated using Angular CLI.\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "add app")
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "--path", str(self.repo)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(1, result.returncode)


if __name__ == "__main__":
    unittest.main(verbosity=2)
