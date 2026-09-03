#!/usr/bin/env python3
"""Stop hook and CLI check: report doc-comments whose shape breaks the rule.

Enforces the doc-comment half of ~/.claude/CLAUDE.md ("Code & artifacts"). Four properties are
mechanically checkable, and every one of them was got wrong by hand before this hook existed:

  no-description  the block carries `@param`/`@returns`/`@throws` but no prose above them. Tags
                  alone are never the deliverable: the parameter list is already in the
                  signature, and the sentence saying what the callable is FOR is the part only a
                  person can supply. Stripping the prose and keeping the tags looks tidy in a
                  diff and leaves the block saying nothing.
  prose-ceiling   more than three prose lines before the first tag. Past that it is rationale,
                  and rationale belongs in docs/architecture.md or an ADR, never above a
                  declaration.
  compacted       the whole block on one line (`/** text */`). The rule wants it expanded: the
                  opening delimiter alone, a star on every continuation, the closing alone.
  layout          a continuation line with no `*` prefix, or no bare `*` line separating the
                  prose from the tags.

What it deliberately does NOT check is whether the prose merely RESTATES the declaration, which
is the most valuable review question here and the least mechanical one: answering it needs the
name, the type and the domain at once. A checker guessing would nag about the lines that carry
real information ("or null while it is loading") and stay silent on the ones that do not
("Enters edit mode"), which is worse than not checking. Nor does it check that the tag list is
COMPLETE against the signature: that needs a parser per language, and a wrong answer there would
train the reader to ignore the output.

Scope is files holding uncommitted work, as with the other Stop hooks here, and only languages
whose doc convention is a `/** */` block. C# `///`, Python docstrings and Go `//` comments have
their own shape and are out of scope rather than silently mis-measured.

Modes (DOC_SHAPE_HOOK_MODE):
  dry-run  default. Never blocks; appends findings to ~/.claude/logs/doc-comment-shape.log.
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

LOG_PATH = Path.home() / ".claude" / "logs" / "doc-comment-shape.log"

PROSE_CEILING = 3

# Languages whose doc convention is a `/** */` block.
BLOCK_DOC_SUFFIXES = {
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".java",
    ".kt",
    ".kts",
    ".swift",
    ".scala",
    ".groovy",
    ".dart",
    ".php",
}

SKIP_DIRECTORIES = {
    "node_modules",
    "dist",
    "build",
    "out",
    "coverage",
    ".git",
    ".angular",
    ".next",
    ".nuxt",
    "vendor",
    "__pycache__",
}

ONE_LINE_BLOCK = re.compile(r"^\s*/\*\*.*\*/\s*$")
STAR_PREFIX = re.compile(r"^\s*\*")
TAG_LINE = re.compile(r"^\s*\*\s*@\w+")
CONTENT_AFTER_STAR = re.compile(r"^\s*\*\s?(.*)$")


def doc_blocks(lines):
    """Locate every `/** ... */` block in a file.

    A one-line block is reported as a zero-height span so the caller can flag it without
    special-casing the scan.

    :param lines: file content split into lines
    :return: list of (start, end) zero-based line indices, inclusive
    """
    spans = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("/**"):
            if stripped.endswith("*/") and len(stripped) > 4:
                spans.append((index, index))
            else:
                end = index + 1
                while end < len(lines) and "*/" not in lines[end]:
                    end += 1
                if end < len(lines):
                    spans.append((index, end))
                index = end
        index += 1
    return spans


def classify(lines, start, end):
    """Name every shape rule the block at (start, end) breaks.

    :param lines: file content split into lines
    :param start: index of the opening delimiter
    :param end: index of the closing delimiter
    :return: list of problem slugs, empty when the block is well formed
    """
    problems = []

    if start == end:
        return ["compacted"]

    if lines[start].strip() != "/**":
        problems.append("layout: text beside the opening delimiter")
    if lines[end].strip() != "*/":
        problems.append("layout: text beside the closing delimiter")

    prose = []
    first_tag = None
    for index in range(start + 1, end):
        line = lines[index]
        if not STAR_PREFIX.match(line) and line.strip():
            problems.append("layout: continuation without a star prefix")
            continue
        if TAG_LINE.match(line):
            first_tag = index
            break
        content = CONTENT_AFTER_STAR.match(line)
        if content and content.group(1).strip():
            prose.append(content.group(1).strip())

    if first_tag is not None and not prose:
        problems.append("no-description: tags with nothing said above them")
    if len(prose) > PROSE_CEILING:
        problems.append(f"prose-ceiling: {len(prose)} lines before the tags")
    if first_tag is not None and prose and lines[first_tag - 1].strip() != "*":
        problems.append("layout: no bare star line before the tags")

    return problems


def scan_file(path):
    """Check one file's doc-comments.

    :param path: file to read
    :return: list of (line number, problems) for each offending block
    """
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError:
        return []

    findings = []
    for start, end in doc_blocks(lines):
        problems = classify(lines, start, end)
        if problems:
            findings.append((start + 1, problems))
    return findings


def changed_files(repo):
    """Collect repo-relative paths holding uncommitted work.

    Tracked modifications and untracked files both count: a new file is exactly where a
    hand-written doc-comment lands.

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

    The Stop hook only ever looks at uncommitted work, but an audit of an already-committed tree
    needs the whole thing: on a clean checkout the changed-file scan has nothing to measure and
    would report "well formed" without having looked at a single line.

    :param repo: repository root path
    :return: set of repo-relative tracked paths
    """
    return {line.strip() for line in run_git(repo, "ls-files").splitlines() if line.strip()}


def candidate_paths(repo, relpaths):
    """Filter paths to files this check understands.

    :param repo: repository root path
    :param relpaths: repo-relative paths to consider
    :return: list of (relpath, absolute Path) pairs
    """
    out = []
    for rel in sorted(relpaths):
        path = Path(repo) / rel
        if path.suffix not in BLOCK_DOC_SUFFIXES or not path.is_file():
            continue
        if SKIP_DIRECTORIES & set(Path(rel).parts):
            continue
        out.append((rel, path))
    return out


def analyse(repo, relpaths):
    """Check every candidate file among `relpaths`.

    :param repo: repository root path
    :param relpaths: repo-relative paths to consider
    :return: list of (relpath, line number, problems)
    """
    results = []
    for rel, path in candidate_paths(repo, relpaths):
        for line, problems in scan_file(path):
            results.append((rel, line, problems))
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
        f"{len(results)} doc-comment(s) break the shape rule "
        f"(~/.claude/CLAUDE.md -> Code & artifacts):"
    ]
    for rel, line, problems in results[:limit]:
        lines.append(f"  {rel}:{line}  {'; '.join(problems)}")
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
            for rel, line, problems in results:
                handle.write(f"{repo}\t{rel}:{line}\t{'; '.join(problems)}\n")
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
        print(f"Every doc-comment is well formed across {counted} {where}(s).")
    return 1 if results else 0


def run_hook():
    """Run the check as a Stop hook, honouring DOC_SHAPE_HOOK_MODE.

    :return: process exit code
    """
    mode = os.environ.get("DOC_SHAPE_HOOK_MODE", "dry-run").lower()
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
    parser = argparse.ArgumentParser(description="Report doc-comments whose shape breaks the rule.")
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
