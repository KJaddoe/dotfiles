#!/usr/bin/env python3
"""Tests for the duplicate-symbols Stop hook.

Run: python3 claude/hooks/tests/test_duplicate_symbols.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "duplicate-symbols.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("duplicate_symbols", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


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
    """Base fixture creating a throwaway git repo with one committed baseline file."""

    def setUp(self):
        """Create a temp git repo with an initial commit."""
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "test")
        (self.repo / "baseline.md").write_text("baseline\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "init")

    def write(self, name, content):
        """Write a file inside the repo, creating parent directories.

        :param name: repo-relative path
        :param content: file body
        :return: absolute Path written
        """
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def commit(self, message="change"):
        """Stage and commit everything currently in the working tree.

        :param message: commit message
        """
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", message)

    def analyse(self, changed=None):
        """Run the analyser over the fixture repo.

        :param changed: explicit changed set, or None to derive it from git
        :return: the analyse result dict
        """
        if changed is None:
            changed = hook.changed_files(self.repo)
        return hook.analyse(self.repo, changed)


class ExactTier(RepoFixture):
    """The high-confidence tier: one symbol name declared in two files."""

    def test_clean_repo_reports_nothing(self):
        """Happy path: distinct names across files produce no finding."""
        self.write("src/a.ts", "export function alpha() {}\n")
        self.write("src/b.ts", "export function beta() {}\n")
        result = self.analyse()
        self.assertEqual(result["exact"], {})
        self.assertEqual(hook.build_message(result), "")

    def test_same_name_in_two_files_is_flagged(self):
        """A name declared in two files is reported with both paths."""
        self.write("src/a.ts", "export interface Page {}\n")
        self.write("src/b.ts", "export interface Page {}\n")
        result = self.analyse()
        self.assertIn("Page", result["exact"])
        self.assertEqual(
            sorted(rel for _, rel in result["exact"]["Page"]),
            ["src/a.ts", "src/b.ts"],
        )

    def test_new_file_duplicating_committed_symbol_is_caught(self):
        """Regression: the index must cover the WHOLE repo, not only changed files.

        A brand-new file duplicating a symbol in untouched, committed code is the case worth
        catching. A changed-versus-changed scan would miss it entirely.
        """
        self.write("src/existing.ts", "export function paginate() {}\n")
        self.commit("add existing helper")
        self.write("src/new.ts", "export function paginate() {}\n")

        result = self.analyse()
        self.assertIn("paginate", result["exact"])
        self.assertIn("paginate", hook.build_message(result))

    def test_untouched_collision_is_counted_not_listed(self):
        """A pre-existing collision the session never touched is summarised, not listed."""
        self.write("src/a.ts", "export interface Page {}\n")
        self.write("src/b.ts", "export interface Page {}\n")
        self.commit("pre-existing duplication")
        self.write("src/unrelated.ts", "export function unrelated() {}\n")

        result = self.analyse()
        self.assertEqual(result["exact"], {})
        self.assertEqual(result["other_exact"], 1)
        self.assertEqual(hook.build_message(result), "")

    def test_all_mode_lists_untouched_collisions(self):
        """An empty changed set (the --all path) reports every collision."""
        self.write("src/a.ts", "export interface Page {}\n")
        self.write("src/b.ts", "export interface Page {}\n")
        self.commit("pre-existing duplication")

        result = self.analyse(changed=set())
        self.assertIn("Page", result["exact"])
        self.assertEqual(result["other_exact"], 0)


class ExactTierMustNotFire(RepoFixture):
    """Cases that must stay unflagged: the noise this tier would otherwise drown in."""

    def test_declarations_in_one_file_are_not_a_collision(self):
        """Overloads and merged declarations share a file and are deliberate."""
        self.write(
            "src/overloads.ts",
            "export function widen(a: string): void;\n" "export function widen(a: number): void;\n",
        )
        self.assertEqual(self.analyse()["exact"], {})

    def test_test_and_spec_files_are_excluded(self):
        """A spec redeclaring the type it exercises is not duplication."""
        self.write("src/thing.ts", "export interface Thing {}\n")
        self.write("src/thing.spec.ts", "export interface Thing {}\n")
        self.write("test/helpers.ts", "export interface Thing {}\n")
        self.assertEqual(self.analyse()["exact"], {})

    def test_ambient_declaration_files_are_excluded(self):
        """`.d.ts` files restate types by design."""
        self.write("src/thing.ts", "export interface Thing {}\n")
        self.write("src/thing.d.ts", "export interface Thing {}\n")
        self.assertEqual(self.analyse()["exact"], {})

    def test_generated_directories_are_skipped(self):
        """Vendored and built trees are not the project's own code."""
        self.write("src/thing.ts", "export interface Thing {}\n")
        self.write("node_modules/pkg/thing.ts", "export interface Thing {}\n")
        self.write("dist/thing.ts", "export interface Thing {}\n")
        self.assertEqual(self.analyse()["exact"], {})

    def test_migrations_are_excluded(self):
        """Generated migration classes repeat shapes and are never hand-reused."""
        self.write("src/thing.ts", "export class Snapshot {}\n")
        self.write("src/migrations/0001.ts", "export class Snapshot {}\n")
        self.assertEqual(self.analyse()["exact"], {})

    def test_reexports_are_not_declarations(self):
        """A barrel re-exporting a symbol does not declare a second copy of it."""
        self.write("src/thing.ts", "export interface Thing {}\n")
        self.write("src/index.ts", "export { Thing } from './thing';\n")
        self.assertEqual(self.analyse()["exact"], {})


class CSharpSupport(RepoFixture):
    """C# type declarations are indexed; methods deliberately are not."""

    def test_duplicate_type_is_flagged(self):
        """Two files declaring the same C# type collide."""
        self.write("src/A.cs", "public sealed class PagedResult { }\n")
        self.write("src/B.cs", "internal class PagedResult { }\n")
        self.assertIn("PagedResult", self.analyse()["exact"])

    def test_methods_are_not_indexed(self):
        """Overrides and interface implementations repeat method names legitimately."""
        self.write("src/A.cs", "public class Alpha\n{\n    public void Handle() { }\n}\n")
        self.write("src/B.cs", "public class Beta\n{\n    public void Handle() { }\n}\n")
        self.assertEqual(self.analyse()["exact"], {})


class NearTier(RepoFixture):
    """The low-confidence tier, constrained to a single directory."""

    def test_similar_names_in_one_directory_are_flagged(self):
        """`PageQueryDto` beside `PagedQueryDto` is the shape this tier exists for."""
        self.write("src/dto/page-query.dto.ts", "export class PageQueryDto {}\n")
        self.write("src/dto/paged-query.dto.ts", "export class PagedQueryDto {}\n")
        names = {hit[1] for hit in self.analyse()["near"]}
        self.assertIn("PageQueryDto", names)

    def test_similar_names_in_different_directories_are_ignored(self):
        """Layered architectures repeat names across folders by construction."""
        self.write("src/domain/contact.ts", "export interface ContactRecord {}\n")
        self.write("src/infra/ln-contact.ts", "export interface ContactRecords {}\n")
        self.assertEqual(self.analyse()["near"], [])

    def test_injection_token_beside_its_interface_is_ignored(self):
        """A CONST_CASE token named after its PascalCase interface is a convention."""
        self.write("src/ports/reader.port.ts", "export const CONTACT_READER = 'x';\n")
        self.write("src/ports/other.port.ts", "export interface ContactReader {}\n")
        self.assertEqual(self.analyse()["near"], [])

    def test_short_names_are_ignored(self):
        """Below the length floor, similarity is meaningless."""
        self.write("src/a.ts", "export const abc = 1;\n")
        self.write("src/b.ts", "export const abd = 1;\n")
        self.assertEqual(self.analyse()["near"], [])

    def test_dissimilar_names_are_ignored(self):
        """Names below the ratio floor are not reported."""
        self.write("src/a.ts", "export function serialiseCustomer() {}\n")
        self.write("src/b.ts", "export function retryPolicy() {}\n")
        self.assertEqual(self.analyse()["near"], [])


class HookBehaviour(RepoFixture):
    """End-to-end behaviour of the Stop-hook entry point."""

    def run_hook(self, mode=None, cwd=None):
        """Invoke the hook as a subprocess with Stop-hook stdin.

        :param mode: value for DUPE_SYMBOL_HOOK_MODE, or None to use the default
        :param cwd: cwd reported to the hook, defaulting to the fixture repo
        :return: the CompletedProcess
        """
        env = dict(os.environ)
        env.pop("DUPE_SYMBOL_HOOK_MODE", None)
        if mode:
            env["DUPE_SYMBOL_HOOK_MODE"] = mode
        env["HOME"] = str(self.repo / "fakehome")
        return subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps({"cwd": str(cwd or self.repo)}),
            capture_output=True,
            text=True,
            env=env,
        )

    def test_dry_run_reports_without_blocking(self):
        """The default mode warns on stderr and exits 0."""
        self.write("src/a.ts", "export interface Page {}\n")
        self.write("src/b.ts", "export interface Page {}\n")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0)
        self.assertIn("Page", result.stderr)
        self.assertIn("[dry-run]", result.stderr)

    def test_enforce_mode_blocks(self):
        """Enforce mode exits 2 so the finding is fed back to the model."""
        self.write("src/a.ts", "export interface Page {}\n")
        self.write("src/b.ts", "export interface Page {}\n")
        result = self.run_hook(mode="enforce")
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED by user policy", result.stderr)

    def test_off_mode_is_silent(self):
        """Off mode does nothing at all."""
        self.write("src/a.ts", "export interface Page {}\n")
        self.write("src/b.ts", "export interface Page {}\n")
        result = self.run_hook(mode="off")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_clean_tree_is_silent(self):
        """With no uncommitted work, reading a repo stays quiet."""
        self.write("src/a.ts", "export interface Page {}\n")
        self.write("src/b.ts", "export interface Page {}\n")
        self.commit("committed duplication")
        result = self.run_hook()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_outside_a_git_repo_is_silent(self):
        """A non-repo cwd is not an error."""
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        result = self.run_hook(cwd=outside)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_malformed_stdin_is_survived(self):
        """Bad hook input must never crash the session."""
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input="not json",
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)


class CliBehaviour(RepoFixture):
    """The --path CLI form used by CI."""

    def test_exits_one_when_findings_exist(self):
        """A CI job needs a non-zero exit to fail the build."""
        self.write("src/a.ts", "export interface Page {}\n")
        self.write("src/b.ts", "export interface Page {}\n")
        self.commit("committed duplication")
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "--path", str(self.repo), "--all"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Page", result.stdout)

    def test_exits_zero_when_clean(self):
        """A clean repo exits 0 with a plain message."""
        self.write("src/a.ts", "export function alpha() {}\n")
        self.commit("clean")
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "--path", str(self.repo), "--all"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("No duplicated symbol names", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
