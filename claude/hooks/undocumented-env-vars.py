#!/usr/bin/env python3
"""Stop hook: flag env vars introduced this session that no doc mentions.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Project documentation"): an env var is not
done until it's documented — name, purpose, required/optional, default, placeholder, and where
the real value lives.

Modes (DOCS_ENV_HOOK_MODE):
  dry-run  default. Never blocks; appends findings to ~/.claude/logs/env-doc-hook.log.
  enforce  exit 2 + stderr, feeding the finding back to the model.
  off      no-op.

SECURITY: only variable NAMES are ever captured or logged. The matched source line is never
recorded, so a secret VALUE sitting in the diff cannot leak into the log.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LOG_PATH = Path.home() / ".claude" / "logs" / "env-doc-hook.log"

ENV_PATTERNS = [
    re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)"),
    re.compile(r"process\.env\[\s*['\"]([A-Z][A-Z0-9_]*)['\"]"),
    re.compile(r"import\.meta\.env\.([A-Z][A-Z0-9_]*)"),
    re.compile(r"Environment\.GetEnvironmentVariable\(\s*\"([A-Z][A-Z0-9_]*)\""),
    re.compile(r"os\.environ\[\s*['\"]([A-Z][A-Z0-9_]*)['\"]"),
    re.compile(r"os\.environ\.get\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]"),
    re.compile(r"os\.getenv\(\s*['\"]([A-Z][A-Z0-9_]*)['\"]"),
]

IGNORED_VARS = {
    "CI",
    "DEBUG",
    "HOME",
    "HOST",
    "HOSTNAME",
    "LANG",
    "LC_ALL",
    "NODE_ENV",
    "PATH",
    "PWD",
    "SHELL",
    "TERM",
    "TMPDIR",
    "TZ",
    "USER",
}

DOC_GLOBS = [
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
    "README*",
    "CLAUDE.md",
    "CONTRIBUTING*",
    "docs/**/*.md",
    "doc/**/*.md",
    "*/README*",
    "*/.env.example",
]

MAX_DOC_BYTES = 2_000_000

EXCLUDED_PATH = re.compile(
    r"(^|/)(tests?|__tests__|specs?|fixtures?|mocks?|__mocks__)(/|$)"
    r"|(^|/)test_[^/]*$"
    r"|[._-](test|spec)\.[A-Za-z]+$",
    re.IGNORECASE,
)


def run_git(repo, *args):
    """Run a git command in `repo`, returning stdout or "" if git fails.

    :param repo: repository root path
    :param args: git arguments following the subcommand
    :return: decoded stdout, empty on any failure
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def repo_root(cwd):
    """Resolve the git repository root containing `cwd`.

    :param cwd: directory to resolve from
    :return: Path to the repo root, or None when not inside a git repo
    """
    top = run_git(cwd, "rev-parse", "--show-toplevel").strip()
    return Path(top) if top else None


def is_excluded(path):
    """Report whether a repo-relative path is test or fixture code.

    Test files legitimately contain invented env var names, so scanning them produces
    false positives.

    :param path: repo-relative path
    :return: True when the path should be skipped
    """
    return bool(EXCLUDED_PATH.search(path))


def added_lines(repo):
    """Collect lines added in uncommitted work (tracked diff plus untracked files).

    Only additions are considered, so pre-existing undocumented vars stay out of scope.
    Test and fixture paths are skipped.

    :param repo: repository root path
    :return: list of added source lines, without the leading diff marker
    """
    lines = []
    diff = run_git(repo, "diff", "HEAD", "--unified=0", "--no-color")
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith(("+++", "---")):
            current = None
        elif line.startswith("+") and current and not is_excluded(current):
            lines.append(line[1:])

    untracked = run_git(repo, "ls-files", "--others", "--exclude-standard")
    for name in untracked.splitlines():
        if is_excluded(name):
            continue
        path = repo / name
        try:
            if path.is_file() and path.stat().st_size <= MAX_DOC_BYTES:
                lines.extend(path.read_text(errors="ignore").splitlines())
        except OSError:
            continue
    return lines


def extract_env_vars(lines):
    """Extract env var names referenced in the given source lines.

    Captures the name only — never the surrounding line — so secret values cannot escape.

    :param lines: source lines to scan
    :return: set of candidate env var names, minus well-known platform vars
    """
    found = set()
    for line in lines:
        for pattern in ENV_PATTERNS:
            found.update(pattern.findall(line))
    return found - IGNORED_VARS


def documented_names(repo):
    """Build the set of tokens appearing anywhere in the repo's documentation.

    :param repo: repository root path
    :return: concatenated lowercase text of all discovered doc files
    """
    blob = []
    seen = set()
    for pattern in DOC_GLOBS:
        for path in repo.glob(pattern):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            try:
                if path.stat().st_size <= MAX_DOC_BYTES:
                    blob.append(path.read_text(errors="ignore"))
            except OSError:
                continue
    return "\n".join(blob)


def find_undocumented(repo):
    """Determine which newly-referenced env vars appear in no documentation.

    :param repo: repository root path
    :return: sorted list of undocumented env var names
    """
    candidates = extract_env_vars(added_lines(repo))
    if not candidates:
        return []
    docs = documented_names(repo)
    return sorted(v for v in candidates if v not in docs)


def write_log(repo, missing):
    """Append a dry-run finding to the hook log, creating the log directory as needed.

    :param repo: repository root path
    :param missing: undocumented env var names
    """
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as handle:
            handle.write(f"{repo}\t{','.join(missing)}\n")
    except OSError:
        pass


def build_message(missing):
    """Compose the operator-facing message describing what is undocumented.

    :param missing: undocumented env var names
    :return: message string
    """
    return (
        f"Undocumented env var(s) introduced: {', '.join(missing)}.\n"
        "Per ~/.claude/CLAUDE.md (Project documentation), each needs: name, purpose, required vs "
        "optional, default, a safe placeholder, and WHERE the real value comes from — the "
        "location, never the value. Add them to .env.example (if present) and the project docs.\n"
        "Use the `writing-project-docs` skill for the format."
    )


def main():
    """Entry point: scan for undocumented env vars and act per the configured mode."""
    mode = os.environ.get("DOCS_ENV_HOOK_MODE", "dry-run").lower()
    if mode == "off":
        sys.exit(0)

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if data.get("stop_hook_active"):
        sys.exit(0)

    repo = repo_root(data.get("cwd") or os.getcwd())
    if not repo:
        sys.exit(0)

    missing = find_undocumented(repo)
    if not missing:
        sys.exit(0)

    if mode == "enforce":
        print(f"BLOCKED by user policy: {build_message(missing)}", file=sys.stderr)
        sys.exit(2)

    write_log(repo, missing)
    print(f"[dry-run] {build_message(missing)}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
