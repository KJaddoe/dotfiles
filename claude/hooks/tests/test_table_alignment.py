#!/usr/bin/env python3
"""Tests for the table-alignment Stop hook.

Run: python3 claude/hooks/tests/test_table_alignment.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "table-alignment.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("table_alignment", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def formatted(header, data_rows, aligns=None, indent=""):
    """Build a Markdown table source string from the hook's own formatter.

    Widths are the widest cell per column, plus the two border spaces a content row reserves.
    Round-tripping through `render_table` this way sidesteps hand-computed padding: a table
    built from it is by construction the one `scan_file` considers clean, so a test mutates it
    from there rather than typing padding out by hand.

    :param header: header row cells
    :param data_rows: list of data row cell lists
    :param aligns: per-column alignment, defaulting to left throughout
    :param indent: leading whitespace shared by every row
    :return: source text, newline-terminated
    """
    aligns = aligns or ["left"] * len(header)
    placeholder_delimiter = [""] * len(header)
    rows = [header, placeholder_delimiter] + data_rows
    widths = [max(len(row[col]) for row in [header, *data_rows]) + 2 for col in range(len(header))]
    return "\n".join(hook.render_table(rows, aligns, indent, widths)) + "\n"


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


class ClassifyTests(unittest.TestCase):
    """A well-formatted table is left alone; a misaligned one is reported per row."""

    def findings(self, source):
        """Scan a snippet for misaligned rows.

        :param source: file content
        :return: list of (line number, expected line)
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.md"
            path.write_text(source, encoding="utf-8")
            return hook.scan_file(path)

    def test_aligned_table_is_accepted(self):
        source = formatted(["Name", "Purpose"], [["a", "first"], ["bb", "second"]])
        self.assertEqual(self.findings(source), [])

    def test_uniformly_wider_than_minimum_is_accepted(self):
        """The rule is internal consistency, not the minimal width a formatter would pick."""
        header, data_rows = ["Name", "Purpose"], [["a", "first"], ["bb", "second"]]
        minimal = [max(len(row[col]) for row in [header, *data_rows]) + 2 for col in range(2)]
        widths = [width + 3 for width in minimal]
        rows = [header, ["", ""], *data_rows]
        source = "\n".join(hook.render_table(rows, ["left", "left"], "", widths)) + "\n"
        self.assertEqual(self.findings(source), [])

    def test_ragged_table_is_reported_row_by_row(self):
        clean = formatted(["Name", "Purpose"], [["a", "first"], ["bb", "second"]])
        lines = clean.splitlines()
        lines[1] = "|---|---|"
        lines[2] = "| a | first |"
        found = self.findings("\n".join(lines) + "\n")
        self.assertEqual([line for line, _ in found], [2, 3])

    def test_right_alignment_is_respected(self):
        source = formatted(["Name", "Count"], [["a", "1"], ["bb", "22"]], aligns=["left", "right"])
        self.assertEqual(self.findings(source), [])

    def test_center_alignment_is_respected(self):
        source = formatted(["Name", "Mid"], [["a", "1"], ["bb", "22"]], aligns=["left", "center"])
        self.assertEqual(self.findings(source), [])

    def test_left_marked_alignment_is_respected(self):
        source = formatted(["Name", "Left"], [["a", "1"]], aligns=["left", "left-marked"])
        self.assertEqual(self.findings(source), [])

    def test_right_aligned_content_flush_left_is_reported(self):
        clean = formatted(["Name", "Count"], [["a", "1"]], aligns=["left", "right"])
        lines = clean.splitlines()
        lines[2] = "| a    | 1     |"
        found = self.findings("\n".join(lines) + "\n")
        self.assertEqual([line for line, _ in found], [3])

    def test_indented_table_is_measured_against_its_own_indent(self):
        source = formatted(["Name", "Purpose"], [["a", "first"]], indent="  ")
        self.assertEqual(self.findings(source), [])

    def test_table_missing_outer_pipes_is_ignored(self):
        found = self.findings("Name | Purpose\n---|---\na | first\n")
        self.assertEqual(found, [])

    def test_non_table_content_is_ignored(self):
        found = self.findings("Just prose.\n\nAnother line.\n")
        self.assertEqual(found, [])

    def test_mismatched_column_count_is_skipped(self):
        found = self.findings("| Name | Purpose |\n|---|---|\n| a | first | extra |\n")
        self.assertEqual(found, [])


class ScopeTests(unittest.TestCase):
    """Only uncommitted Markdown work is measured."""

    def misaligned_md(self):
        """A one-column table with a too-narrow delimiter row.

        :return: mapping suitable for `make_repo`
        """
        return {"a.md": "| Name |\n|---|\n| a    |\n"}

    def test_committed_work_is_not_reported(self):
        handle, repo = make_repo(self.misaligned_md())
        with handle:
            git(repo, "add", "-A")
            git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x")
            self.assertEqual(hook.analyse(repo, hook.changed_files(repo)), [])

    def test_uncommitted_work_is_reported(self):
        handle, repo = make_repo(self.misaligned_md())
        with handle:
            self.assertEqual(len(hook.analyse(repo, hook.changed_files(repo))), 1)

    def test_a_non_markdown_file_is_skipped(self):
        handle, repo = make_repo({"a.txt": self.misaligned_md()["a.md"]})
        with handle:
            self.assertEqual(hook.analyse(repo, hook.changed_files(repo)), [])

    def test_all_mode_measures_committed_work(self):
        handle, repo = make_repo(self.misaligned_md())
        with handle:
            git(repo, "add", "-A")
            git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-m", "x")
            self.assertEqual(hook.analyse(repo, hook.changed_files(repo)), [])
            self.assertEqual(len(hook.analyse(repo, hook.tracked_files(repo))), 1)

    def test_vendored_directories_are_skipped(self):
        handle, repo = make_repo({"vendor/a.md": self.misaligned_md()["a.md"]})
        with handle:
            self.assertEqual(hook.analyse(repo, hook.changed_files(repo)), [])


class HookModeTests(unittest.TestCase):
    """The Stop hook advises by default and blocks only when told to."""

    MISALIGNED = "| Name |\n|---|\n| a    |\n"

    def run_hook(self, repo, mode):
        """Invoke the hook as a subprocess with a Stop payload.

        :param repo: repository path
        :param mode: value for TABLE_ALIGN_HOOK_MODE
        :return: CompletedProcess
        """
        env = dict(os.environ, TABLE_ALIGN_HOOK_MODE=mode)
        return subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps({"cwd": str(repo), "stop_hook_active": False}),
            capture_output=True,
            text=True,
            env=env,
        )

    def test_dry_run_reports_without_blocking(self):
        handle, repo = make_repo({"a.md": self.MISALIGNED})
        with handle:
            result = self.run_hook(repo, "dry-run")
            self.assertEqual(result.returncode, 0)
            self.assertIn("not padded", result.stderr)

    def test_enforce_blocks(self):
        handle, repo = make_repo({"a.md": self.MISALIGNED})
        with handle:
            result = self.run_hook(repo, "enforce")
            self.assertEqual(result.returncode, 2)
            self.assertIn("BLOCKED", result.stderr)

    def test_off_does_nothing(self):
        handle, repo = make_repo({"a.md": self.MISALIGNED})
        with handle:
            result = self.run_hook(repo, "off")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")

    def test_a_clean_table_is_silent(self):
        handle, repo = make_repo({"a.md": formatted(["A"], [["bb"]])})
        with handle:
            result = self.run_hook(repo, "dry-run")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
