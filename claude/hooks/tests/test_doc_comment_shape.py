#!/usr/bin/env python3
"""Tests for the doc-comment-shape Stop hook.

Run: python3 claude/hooks/tests/test_doc_comment_shape.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "doc-comment-shape.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("doc_comment_shape", HOOK_PATH)
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


def make_repo(files):
    """Create a temporary git repository holding `files` as uncommitted work.

    :param files: mapping of relative path to file content
    :return: (TemporaryDirectory handle, repository path)
    """
    handle = tempfile.TemporaryDirectory()
    repo = Path(handle.name)
    git(repo, "init")
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return handle, repo


def slugs(results):
    """Reduce findings to the set of problem categories reported.

    :param results: output of `hook.analyse`
    :return: set of slugs, each the part before the first colon
    """
    return {p.split(":")[0] for _, _, problems in results for p in problems}


class ClassifyTests(unittest.TestCase):
    """Each shape rule is caught, and a well-formed block is left alone."""

    def findings(self, source):
        """Classify every block in a snippet.

        :param source: file content
        :return: list of (line number, problems)
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.ts"
            path.write_text(source, encoding="utf-8")
            return hook.scan_file(path)

    def test_well_formed_block_is_accepted(self):
        found = self.findings(
            "/**\n"
            " * Reads one contact.\n"
            " *\n"
            " * @param id The contact code.\n"
            " * @returns The contact.\n"
            " */\n"
            "function get(id: string) {}\n"
        )
        self.assertEqual(found, [])

    def test_prose_only_block_is_accepted(self):
        found = self.findings("/**\n * The application shell.\n */\nclass App {}\n")
        self.assertEqual(found, [])

    def test_tags_without_a_description_are_reported(self):
        found = self.findings(
            "/**\n"
            " * @param id The contact code.\n"
            " * @returns The contact.\n"
            " */\n"
            "function get(id: string) {}\n"
        )
        self.assertEqual(len(found), 1)
        self.assertIn("no-description", found[0][1][0])

    def test_compacted_block_is_reported(self):
        found = self.findings("/** Reads one contact. */\nfunction get() {}\n")
        self.assertEqual(found, [(1, ["compacted"])])

    def test_prose_over_the_ceiling_is_reported(self):
        found = self.findings(
            "/**\n" " * One.\n" " * Two.\n" " * Three.\n" " * Four.\n" " */\n" "class Thing {}\n"
        )
        self.assertEqual(len(found), 1)
        self.assertIn("prose-ceiling", found[0][1][0])

    def test_missing_star_line_before_tags_is_reported(self):
        found = self.findings(
            "/**\n"
            " * Reads one contact.\n"
            " * @param id The contact code.\n"
            " */\n"
            "function get(id: string) {}\n"
        )
        self.assertEqual(len(found), 1)
        self.assertIn("no bare star line", found[0][1][0])

    def test_continuation_without_a_star_is_reported(self):
        found = self.findings("/**\n * Reads one contact.\n   and more.\n */\nfunction get() {}\n")
        self.assertEqual(len(found), 1)
        self.assertIn("star prefix", found[0][1][0])

    def test_three_prose_lines_sit_exactly_on_the_ceiling(self):
        found = self.findings("/**\n * One.\n * Two.\n * Three.\n */\nclass Thing {}\n")
        self.assertEqual(found, [])

    def test_a_plain_block_comment_is_not_a_doc_comment(self):
        found = self.findings("/*\n  @param whatever\n*/\nfunction get() {}\n")
        self.assertEqual(found, [])


class ScopeTests(unittest.TestCase):
    """Only uncommitted work in a understood language is measured."""

    def test_committed_work_is_not_reported(self):
        handle, repo = make_repo({"a.ts": "/** Compacted. */\nclass A {}\n"})
        with handle:
            git(repo, "add", "-A")
            git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x")
            self.assertEqual(hook.analyse(repo, hook.changed_files(repo)), [])

    def test_uncommitted_work_is_reported(self):
        handle, repo = make_repo({"a.ts": "/** Compacted. */\nclass A {}\n"})
        with handle:
            self.assertEqual(slugs(hook.analyse(repo, hook.changed_files(repo))), {"compacted"})

    def test_a_language_without_block_docs_is_skipped(self):
        handle, repo = make_repo({"a.py": '"""Doc."""\n', "b.cs": "/** Compacted. */\n"})
        with handle:
            self.assertEqual(hook.analyse(repo, hook.changed_files(repo)), [])

    def test_all_mode_measures_committed_work(self):
        handle, repo = make_repo({"a.ts": "/** Compacted. */\nclass A {}\n"})
        with handle:
            git(repo, "add", "-A")
            git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x")
            # the changed-file scan sees nothing on a clean tree; --all still measures the file
            self.assertEqual(hook.analyse(repo, hook.changed_files(repo)), [])
            self.assertEqual(slugs(hook.analyse(repo, hook.tracked_files(repo))), {"compacted"})

    def test_vendored_directories_are_skipped(self):
        handle, repo = make_repo({"node_modules/p/a.ts": "/** Compacted. */\nclass A {}\n"})
        with handle:
            self.assertEqual(hook.analyse(repo, hook.changed_files(repo)), [])


class HookModeTests(unittest.TestCase):
    """The Stop hook advises by default and blocks only when told to."""

    def run_hook(self, repo, mode):
        """Invoke the hook as a subprocess with a Stop payload.

        :param repo: repository path
        :param mode: value for DOC_SHAPE_HOOK_MODE
        :return: CompletedProcess
        """
        import os

        env = dict(os.environ, DOC_SHAPE_HOOK_MODE=mode)
        return subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps({"cwd": str(repo), "stop_hook_active": False}),
            capture_output=True,
            text=True,
            env=env,
        )

    def test_dry_run_reports_without_blocking(self):
        handle, repo = make_repo({"a.ts": "/** Compacted. */\nclass A {}\n"})
        with handle:
            result = self.run_hook(repo, "dry-run")
            self.assertEqual(result.returncode, 0)
            self.assertIn("compacted", result.stderr)

    def test_enforce_blocks(self):
        handle, repo = make_repo({"a.ts": "/** Compacted. */\nclass A {}\n"})
        with handle:
            result = self.run_hook(repo, "enforce")
            self.assertEqual(result.returncode, 2)
            self.assertIn("BLOCKED", result.stderr)

    def test_off_does_nothing(self):
        handle, repo = make_repo({"a.ts": "/** Compacted. */\nclass A {}\n"})
        with handle:
            result = self.run_hook(repo, "off")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

    def test_a_clean_repository_is_silent(self):
        handle, repo = make_repo({"a.ts": "/**\n * The shell.\n */\nclass A {}\n"})
        with handle:
            result = self.run_hook(repo, "dry-run")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
