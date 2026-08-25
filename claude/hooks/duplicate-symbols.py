#!/usr/bin/env python3
"""Stop hook and CLI check: report symbol names this session duplicated elsewhere in the repo.

Enforces the reuse rule in ~/.claude/CLAUDE.md ("Code quality"): search for something that
already does the job before writing a function, and never add a parallel one alongside it.
Nothing measured that before this hook, so a second copy of an abstraction could land, be
reviewed file-by-file, and read as canonical from either side.

Two tiers, deliberately different in confidence:

  exact  the same exported symbol name declared in two different files. Near-certain
         duplication, measured at 1 hit across 175 exported symbols on a real repo, and that
         hit was a genuine duplicated abstraction.
  near   names >= 0.85 similar, declared in different files OF THE SAME DIRECTORY, with the
         same casing style. Measured at ~33% precision on that repo (6 pairs, 2 real), so it
         is a notice and must never be the thing that blocks.

The WHOLE repo is indexed every run (~0.1-0.5s for ~200 files), so a brand-new file duplicating
an untouched symbol is still caught; only the REPORT is filtered to pairs involving this
session's work. Collisions in code the session never touched are summarised as a count rather
than listed, so a repo with a known duplicate does not nag on every turn. Pass --all to list
them.

Detection is name-based by design, which bounds it: it catches a second `Page<T>` cold, but not
the same behaviour written under a genuinely different name in a different folder. A token-level
clone detector (jscpd) is the tool for that, and it is a per-project dependency rather than a
global hook.

Modes (DUPE_SYMBOL_HOOK_MODE):
  dry-run  default. Never blocks; appends findings to ~/.claude/logs/duplicate-symbol-hook.log.
  enforce  exit 2 + stderr, feeding the finding back to the model.
  off      no-op.

As a hook it reports only on pairs touching uncommitted work, so reading a repo stays quiet.
As a CLI it reports every collision in the repo:

    python3 duplicate-symbols.py --path . [--all]

exiting 1 when anything is found, which is what a CI job wants.

The git helpers come from _hookutil.py, shared with the other Stop hooks.
"""

import argparse
import difflib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from _hookutil import repo_root, run_git

LOG_PATH = Path.home() / ".claude" / "logs" / "duplicate-symbol-hook.log"

MAX_FILE_BYTES = 2_000_000
MAX_FILES = 5_000
NEAR_RATIO = 0.85
MIN_NEAR_LENGTH = 6

SKIPPED_DIRS = {
    ".git",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".venv",
    "__pycache__",
    "bin",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "obj",
    "out",
    "target",
    "vendor",
}

# Type and value declarations only. C# methods are excluded deliberately: overrides and
# interface implementations legitimately repeat a name across files, which would drown the
# exact tier in noise. Python is excluded entirely for the same reason (`def main`).
DECLARATION_PATTERNS = {
    ".ts": re.compile(
        r"^export\s+(?:default\s+)?(?:declare\s+)?(?:abstract\s+)?(?:async\s+)?"
        r"(class|interface|type|enum|function|const)\s+([A-Za-z_$][\w$]*)"
    ),
    ".cs": re.compile(
        r"^\s*(?:public|internal)\s+(?:(?:static|abstract|sealed|partial|readonly)\s+)*"
        r"(class|interface|record|struct|enum)\s+([A-Za-z_][\w]*)"
    ),
}
DECLARATION_PATTERNS[".tsx"] = DECLARATION_PATTERNS[".ts"]
DECLARATION_PATTERNS[".js"] = DECLARATION_PATTERNS[".ts"]
DECLARATION_PATTERNS[".jsx"] = DECLARATION_PATTERNS[".ts"]
DECLARATION_PATTERNS[".mts"] = DECLARATION_PATTERNS[".ts"]

EXCLUDED_PATH = re.compile(
    r"(^|/)(tests?|__tests__|specs?|fixtures?|mocks?|__mocks__|migrations?)(/|$)"
    r"|[._-](test|spec|e2e)\.[A-Za-z]+$"
    r"|\.d\.ts$",
    re.IGNORECASE,
)

CONST_CASE = re.compile(r"^[A-Z0-9_]+$")


def is_excluded(path):
    """Report whether a repo-relative path is test, fixture, migration or ambient code.

    Those legitimately repeat names (a spec redeclaring the type it exercises, a generated
    migration class), so scanning them produces false positives.

    :param path: repo-relative path
    :return: True when the path should be skipped
    """
    return bool(EXCLUDED_PATH.search(path))


def changed_files(repo):
    """Collect repo-relative paths holding uncommitted work.

    Tracked modifications and untracked files both count: a duplicate most often arrives as a
    brand-new file, which no diff against HEAD would show as modified.

    :param repo: repository root path
    :return: set of repo-relative paths changed since HEAD
    """
    changed = set()
    for line in run_git(repo, "diff", "HEAD", "--name-only", "--no-color").splitlines():
        if line.strip():
            changed.add(line.strip())
    for line in run_git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
        if line.strip():
            changed.add(line.strip())
    return changed


def index_symbols(repo):
    """Index every top-level declaration in the repo's source files.

    Indexes the whole tree rather than only changed files: a new file duplicating an untouched
    symbol is the case worth catching, and it is invisible to a changed-versus-changed scan.

    :param repo: repository root path
    :return: (records, truncated) where records are (name, kind, relpath, dirname) tuples and
             truncated is True when the file cap stopped the walk early
    """
    records = []
    seen_files = 0
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIPPED_DIRS]
        for filename in filenames:
            pattern = DECLARATION_PATTERNS.get(Path(filename).suffix)
            if pattern is None:
                continue
            path = Path(dirpath) / filename
            rel = str(path.relative_to(repo))
            if is_excluded(rel):
                continue
            if seen_files >= MAX_FILES:
                return records, True
            seen_files += 1
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            for line in text.splitlines():
                match = pattern.match(line)
                if match:
                    records.append((match.group(2), match.group(1), rel, str(Path(rel).parent)))
    return records, False


def find_exact(records):
    """Group records whose symbol name is declared in more than one file.

    :param records: indexed declaration tuples
    :return: dict of symbol name to the list of records declaring it, files deduplicated
    """
    by_name = defaultdict(dict)
    for name, kind, rel, _ in records:
        by_name[name].setdefault(rel, (kind, rel))
    return {
        name: sorted(files.values(), key=lambda item: item[1])
        for name, files in by_name.items()
        if len(files) > 1
    }


def find_near(records):
    """Find near-identical names declared in different files of the same directory.

    The same-directory constraint is what makes this tier usable: it removes the layered-
    architecture noise (a domain `Contact` beside an infrastructure `LnContact`, a
    `CreateXUseCase` beside an `UpdateXUseCase`) that a repo-wide comparison drowns in.
    Mixed casing styles are skipped too, since a CONST_CASE injection token named after its
    PascalCase interface is a convention, not a duplicate.

    :param records: indexed declaration tuples
    :return: list of (ratio, name_a, path_a, name_b, path_b) tuples
    """
    by_dir = defaultdict(list)
    for record in records:
        by_dir[record[3]].append(record)

    hits = []
    for entries in by_dir.values():
        for index, (name_a, _, rel_a, _) in enumerate(entries):
            for name_b, _, rel_b, _ in entries[index + 1 :]:
                if rel_a == rel_b or name_a == name_b:
                    continue
                if len(name_a) < MIN_NEAR_LENGTH or len(name_b) < MIN_NEAR_LENGTH:
                    continue
                if bool(CONST_CASE.match(name_a)) != bool(CONST_CASE.match(name_b)):
                    continue
                ratio = difflib.SequenceMatcher(None, name_a.lower(), name_b.lower()).ratio()
                if ratio >= NEAR_RATIO:
                    hits.append((round(ratio, 2), name_a, rel_a, name_b, rel_b))
    return sorted(hits, reverse=True)


def touches_changed(paths, changed):
    """Report whether any of `paths` is part of this session's uncommitted work.

    :param paths: repo-relative paths involved in a finding
    :param changed: set of repo-relative changed paths
    :return: True when at least one path was changed
    """
    return any(path in changed for path in paths)


def analyse(repo, changed):
    """Index the repo and split findings into session-relevant and pre-existing.

    :param repo: repository root path
    :param changed: set of repo-relative changed paths, empty to report everything
    :return: dict with exact hits, near hits, counts of skipped pre-existing pairs, and the
             truncated flag
    """
    records, truncated = index_symbols(repo)
    exact = find_exact(records)
    near = find_near(records)

    if not changed:
        return {
            "exact": exact,
            "near": near,
            "other_exact": 0,
            "other_near": 0,
            "truncated": truncated,
        }

    relevant_exact = {
        name: files
        for name, files in exact.items()
        if touches_changed([rel for _, rel in files], changed)
    }
    relevant_near = [hit for hit in near if touches_changed([hit[2], hit[4]], changed)]
    return {
        "exact": relevant_exact,
        "near": relevant_near,
        "other_exact": len(exact) - len(relevant_exact),
        "other_near": len(near) - len(relevant_near),
        "truncated": truncated,
    }


def build_message(result):
    """Compose the operator-facing message describing what looks duplicated.

    :param result: the dict returned by analyse
    :return: message string, empty when there is nothing to report
    """
    lines = []
    if result["exact"]:
        lines.append("Same symbol name declared in more than one file:")
        for name, files in sorted(result["exact"].items()):
            lines.append(f"  {name}")
            for kind, rel in files:
                lines.append(f"    {kind:9} {rel}")
    if result["near"]:
        lines.append("Near-identical names in the same directory (lower confidence):")
        for ratio, name_a, rel_a, name_b, rel_b in result["near"]:
            lines.append(f"  {ratio}  {name_a}  {rel_a}")
            lines.append(f"        {name_b}  {rel_b}")
    if not lines:
        return ""

    skipped = []
    if result["other_exact"]:
        skipped.append(f"{result['other_exact']} exact")
    if result["other_near"]:
        skipped.append(f"{result['other_near']} near")
    if skipped:
        lines.append(
            f"({' and '.join(skipped)} more in code this session did not touch, "
            "run with --all to list them.)"
        )
    if result["truncated"]:
        lines.append(
            f"(Repo exceeds {MAX_FILES} source files; indexing stopped early and this "
            "report is incomplete.)"
        )
    lines.append(
        "Per ~/.claude/CLAUDE.md (Code quality): search for something that already does the "
        "job before writing a function, and never add a parallel one alongside it. If both are "
        "needed, say why; if not, extend the existing one."
    )
    return "\n".join(lines)


def write_log(repo, result):
    """Append a dry-run finding to the hook log, creating the log directory as needed.

    Only symbol names and paths are recorded, never source lines.

    :param repo: repository root path
    :param result: the dict returned by analyse
    """
    names = sorted(result["exact"]) + [hit[1] for hit in result["near"]]
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as handle:
            handle.write(f"{repo}\t{','.join(names)}\n")
    except OSError:
        pass


def run_cli(path, report_all):
    """Run the check as a one-off CLI report over a repository.

    :param path: directory inside the repository to check
    :param report_all: when True, report every collision instead of only changed ones
    :return: process exit code, 1 when anything was found
    """
    repo = repo_root(path)
    if not repo:
        print(f"Not a git repository: {path}", file=sys.stderr)
        return 0
    changed = set() if report_all else changed_files(repo)
    message = build_message(analyse(repo, changed))
    if not message:
        print("No duplicated symbol names found.")
        return 0
    print(message)
    return 1


def run_hook():
    """Run the check as a Stop hook, honouring DUPE_SYMBOL_HOOK_MODE.

    :return: process exit code
    """
    mode = os.environ.get("DUPE_SYMBOL_HOOK_MODE", "dry-run").lower()
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

    result = analyse(repo, changed)
    message = build_message(result)
    if not message:
        return 0

    if mode == "enforce":
        print(f"BLOCKED by user policy: {message}", file=sys.stderr)
        return 2

    write_log(repo, result)
    print(f"[dry-run] {message}", file=sys.stderr)
    return 0


def main():
    """Entry point: dispatch to the CLI report or the Stop hook."""
    parser = argparse.ArgumentParser(
        description="Report symbol names duplicated across a repository."
    )
    parser.add_argument("--path", help="check this repository and exit")
    parser.add_argument(
        "--all",
        action="store_true",
        help="report every collision, not only those touching uncommitted work",
    )
    args = parser.parse_args()

    if args.path:
        sys.exit(run_cli(args.path, args.all))
    sys.exit(run_hook())


if __name__ == "__main__":
    main()
