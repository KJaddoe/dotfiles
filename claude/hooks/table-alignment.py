#!/usr/bin/env python3
"""Stop hook and CLI check: report Markdown tables whose columns are not padded to line up.

Enforces the table rule in ~/.claude/CLAUDE.md ("Code & artifacts"): pad every cell with
trailing spaces so the pipes line up and the raw source reads like a table. The rule asks for
internal consistency, not a specific column width, so the check does not recompute what a
formatter's minimal width would be: it takes the HEADER row's own width per column as the
table's declared width and requires every other row, delimiter included, to match it, padded
per the delimiter's alignment marker (trailing spaces by default, leading for `---:`, both for
`:---:`). Measured against this repo's own docs, a table already padded wider than its content
strictly needs (extra breathing room, kept uniform) reads as fine; a table where one row's
padding does not match the rest of that same column reads as wrong. That is also what "the
pipes line up" literally asks for.

A table is only recognised when every row, delimiter included, opens and closes with `|`,
which is the shape every table in this repo already uses; a table missing its outer pipes is
left alone rather than guessed at. Splitting a row on `|` does not account for an escaped
`\\|` or a pipe inside a code span, so a table using either is skipped outright once its
column count stops matching the header, rather than risk a false positive on content this
check cannot parse. Cell width is character count, not display width, so a table mixing wide
(e.g. CJK) characters into otherwise-ASCII columns may be judged wrong when it is not.

Scope is files holding uncommitted work, as with the other Stop hooks here, and only `.md`
files.

Modes (TABLE_ALIGN_HOOK_MODE):
  dry-run  default. Never blocks; appends findings to ~/.claude/logs/table-alignment.log.
  enforce  exits 2 with the message, which puts it in front of the model as a blocked Stop.
  off      does nothing.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from _hookutil import repo_root, run_git

LOG_PATH = Path.home() / ".claude" / "logs" / "table-alignment.log"

MARKDOWN_SUFFIXES = {".md"}

SKIP_DIRECTORIES = {
    "node_modules",
    "dist",
    "build",
    "out",
    ".git",
    "vendor",
    "__pycache__",
}

ROW = re.compile(r"^(?P<indent>[ \t]*)\|(?P<body>.*)\|[ \t]*$")
DELIMITER_CELL = re.compile(r"^\s*:?-+:?\s*$")


def split_cells(body):
    """Split a row's interior on `|`, with no escaping.

    :param body: text between a row's opening and closing pipe
    :return: list of raw cell strings
    """
    return body.split("|")


def find_tables(lines):
    """Locate every table: a pipe-delimited row followed by a matching delimiter row.

    :param lines: file content split into lines
    :return: list of (start, end, indent) with zero-based inclusive line indices
    """
    tables = []
    index = 0
    limit = len(lines) - 1
    while index < limit:
        header = ROW.match(lines[index])
        delim = ROW.match(lines[index + 1]) if header else None
        if header and delim:
            header_cells = split_cells(header.group("body"))
            delim_cells = split_cells(delim.group("body"))
            if len(header_cells) == len(delim_cells) and all(
                DELIMITER_CELL.match(cell) for cell in delim_cells
            ):
                end = index + 1
                while end + 1 < len(lines) and ROW.match(lines[end + 1]):
                    end += 1
                tables.append((index, end, header.group("indent")))
                index = end + 1
                continue
        index += 1
    return tables


def alignment(delimiter_cell):
    """Read one delimiter cell's alignment marker.

    A single leading colon (`:---`) is GFM's explicit-left marker: content justifies the same
    as the unmarked default, so only the delimiter row's own rendering needs to tell it apart.

    :param delimiter_cell: a cell from the delimiter row, e.g. " :---: "
    :return: "left", "left-marked", "right" or "center"
    """
    cell = delimiter_cell.strip()
    left, right = cell.startswith(":"), cell.endswith(":")
    if left and right:
        return "center"
    if right:
        return "right"
    if left:
        return "left-marked"
    return "left"


def render_table(rows, aligns, indent, widths):
    """Render a table against `widths`: each column's declared total pipe-to-pipe width.

    A content row reserves one border space on each side, so a column of width `w` holds
    `w - 2` characters of justified content. The delimiter row has no border spaces of its
    own: its dashes (and any alignment colons) fill the full `w`, which is what makes a
    delimiter row's raw width comparable to a content row's in the first place.

    :param rows: list of per-row cell lists, row 1 (index 1) being the delimiter row
    :param aligns: per-column alignment, from `alignment`
    :param indent: leading whitespace shared by every row
    :param widths: total pipe-to-pipe width per column, e.g. from the header row
    :return: list of formatted lines, one per row in `rows`
    """
    rendered = []
    for row_index, cells in enumerate(rows):
        pieces = []
        for col in range(len(cells)):
            width = widths[col]
            if row_index == 1:
                if aligns[col] == "center":
                    pieces.append(":" + "-" * (width - 2) + ":")
                elif aligns[col] == "right":
                    pieces.append("-" * (width - 1) + ":")
                elif aligns[col] == "left-marked":
                    pieces.append(":" + "-" * (width - 1))
                else:
                    pieces.append("-" * width)
                continue
            content = cells[col].strip()
            inner = width - 2
            if aligns[col] == "right":
                pieces.append(content.rjust(inner))
            elif aligns[col] == "center":
                pieces.append(content.center(inner))
            else:
                pieces.append(content.ljust(inner))
        if row_index == 1:
            rendered.append(f"{indent}|" + "|".join(pieces) + "|")
        else:
            rendered.append(f"{indent}| " + " | ".join(pieces) + " |")
    return rendered


def scan_file(path):
    """Check one file's tables against their formatted form.

    :param path: file to read
    :return: list of (line number, expected line) for each row that does not match
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError:
        return []

    findings = []
    for start, end, indent in find_tables(lines):
        rows = [split_cells(ROW.match(lines[i]).group("body")) for i in range(start, end + 1)]
        columns = len(rows[0])
        if any(len(row) != columns for row in rows):
            continue
        widths = [len(cell) for cell in rows[0]]
        aligns = [alignment(cell) for cell in rows[1]]
        expected = render_table(rows, aligns, indent, widths)
        for offset, expected_line in enumerate(expected):
            actual_line = lines[start + offset]
            if actual_line != expected_line:
                findings.append((start + offset + 1, expected_line))
    return findings


def changed_files(repo):
    """Collect repo-relative paths holding uncommitted work.

    :param repo: repository root path
    :return: set of repo-relative paths changed since HEAD
    """
    changed = set()
    for args in (
        ("diff", "HEAD", "--name-only", "--no-color"),
        ("ls-files", "--others", "--exclude-standard"),
    ):
        for line in run_git(repo, *args).splitlines():
            if line.strip():
                changed.add(line.strip())
    return changed


def tracked_files(repo):
    """Collect every tracked repo-relative path.

    :param repo: repository root path
    :return: set of repo-relative tracked paths
    """
    return {line.strip() for line in run_git(repo, "ls-files").splitlines() if line.strip()}


def candidate_paths(repo, relpaths):
    """Filter paths to Markdown files outside a skipped directory.

    :param repo: repository root path
    :param relpaths: repo-relative paths to consider
    :return: list of (relpath, absolute Path) pairs
    """
    out = []
    for rel in sorted(relpaths):
        path = Path(repo) / rel
        if path.suffix not in MARKDOWN_SUFFIXES or not path.is_file():
            continue
        if SKIP_DIRECTORIES & set(Path(rel).parts):
            continue
        out.append((rel, path))
    return out


def analyse(repo, relpaths):
    """Check every candidate file among `relpaths`.

    :param repo: repository root path
    :param relpaths: repo-relative paths to consider
    :return: list of (relpath, line number, expected line)
    """
    results = []
    for rel, path in candidate_paths(repo, relpaths):
        for line, expected in scan_file(path):
            results.append((rel, line, expected))
    return results


def build_message(results, limit=12):
    """Render findings as one advisory message.

    :param results: output of `analyse`
    :param limit: how many findings to name before summarising the rest
    :return: message string, empty when there is nothing to report
    """
    if not results:
        return ""

    lines = [
        f"{len(results)} table row(s) are not padded to line up "
        f"(~/.claude/CLAUDE.md -> Code & artifacts):"
    ]
    for rel, line, expected in results[:limit]:
        lines.append(f"  {rel}:{line}  expected: {expected}")
    if len(results) > limit:
        lines.append(f"  ... and {len(results) - limit} more")
    return "\n".join(lines)


def write_log(repo, results):
    """Append findings to the dry-run log.

    :param repo: repository root path
    :param results: output of `analyse`
    """
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            for rel, line, expected in results:
                handle.write(f"{repo}\t{rel}:{line}\texpected: {expected}\n")
    except OSError:
        pass


def run_cli(path, check_all=False):
    """Check a repository and report to stdout.

    :param path: repository to check
    :param check_all: measure every tracked file rather than only uncommitted work
    :return: process exit code
    """
    repo = repo_root(path)
    if not repo:
        print(f"Not a git repository: {path}", file=sys.stderr)
        return 1

    scope = tracked_files(repo) if check_all else changed_files(repo)
    results = analyse(repo, scope)
    message = build_message(results, limit=10_000)
    if message:
        print(message)
    else:
        where = "tracked file" if check_all else "uncommitted change"
        counted = len(candidate_paths(repo, scope))
        print(f"Every table is aligned across {counted} {where}(s).")
    return 1 if results else 0


def run_hook():
    """Run the check as a Stop hook, honouring TABLE_ALIGN_HOOK_MODE.

    :return: process exit code
    """
    mode = os.environ.get("TABLE_ALIGN_HOOK_MODE", "dry-run").lower()
    if mode == "off":
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if data.get("stop_hook_active"):
        return 0

    repo = repo_root(data.get("cwd") or os.getcwd())
    if not repo:
        return 0

    changed = changed_files(repo)
    if not changed:
        return 0

    results = analyse(repo, changed)
    message = build_message(results)
    if not message:
        return 0

    if mode == "enforce":
        print(f"BLOCKED by user policy: {message}", file=sys.stderr)
        return 2

    write_log(repo, results)
    print(f"[dry-run] {message}", file=sys.stderr)
    return 0


def main():
    """Entry point: dispatch to the CLI report or the Stop hook."""
    parser = argparse.ArgumentParser(description="Report Markdown tables that are not aligned.")
    parser.add_argument("--path", help="check this repository and exit")
    parser.add_argument(
        "--all",
        action="store_true",
        help="measure every tracked file, not only uncommitted work",
    )
    args = parser.parse_args()

    if args.path:
        sys.exit(run_cli(args.path, args.all))
    sys.exit(run_hook())


if __name__ == "__main__":
    main()
