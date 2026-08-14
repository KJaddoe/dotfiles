#!/usr/bin/env python3
"""Stop hook and CLI check: report coverage-floor topics a repo's docs never cover.

Enforces the coverage floor in ~/.claude/CLAUDE.md ("Project documentation"). The floor is a
list of questions every project's docs must answer, extended per project kind. Nothing verified
it before this hook, so a repo could accrue changes for its whole life without ever being
measured against it.

Detection is deliberately coarse: a topic counts as covered when the docs mention it at all.
That yields false "covered" on a passing mention, and the check is therefore a floor, never a
quality bar — it catches the topic nobody thought about, not the topic covered badly.

Modes (DOCS_FLOOR_HOOK_MODE):
  dry-run  default. Never blocks; appends findings to ~/.claude/logs/docs-floor-hook.log.
  enforce  exit 2 + stderr, feeding the finding back to the model.
  off      no-op.

As a hook it reports only when the session left uncommitted work, so reading a repo stays quiet.
As a CLI it always reports:

    python3 docs-coverage-floor.py --path .

exiting 1 when anything is missing, which is what a CI job wants.

The git helpers are duplicated from undocumented-env-vars.py rather than shared: each hook has to
stay runnable on its own as `python3 ~/.claude/hooks/<name>.py`, and a shared module would only
resolve when the hooks directory happens to lead sys.path.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LOG_PATH = Path.home() / ".claude" / "logs" / "docs-floor-hook.log"

MAX_DOC_BYTES = 2_000_000

DOC_GLOBS = [
    "README*",
    "CONTRIBUTING*",
    "CLAUDE.md",
    "docs/**/*.md",
    "doc/**/*.md",
    "*/README*",
    ".env.example",
]

# Generator boilerplate. A README still carrying one of these has never been told what the
# project is, whatever else it says — the highest-precision signal available here.
SCAFFOLD_MARKERS = [
    re.compile(r"this project was generated (with|using)", re.IGNORECASE),
    re.compile(r"framework typescript starter repository", re.IGNORECASE),
    re.compile(r"bootstrapped with \[create[- ]react[- ]app\]", re.IGNORECASE),
    re.compile(r"getting started with create react app", re.IGNORECASE),
    re.compile(r"^\s*TODO:? *(add|write) (a )?(readme|description)", re.IGNORECASE | re.MULTILINE),
]

# slug -> (human label, evidence pattern)
TOPICS = {
    "what-it-is": ("what the project is", None),
    "setup": (
        "setup / install",
        r"\b(install(ation|ing)?|set ?up|getting started|prerequisite)",
    ),
    "tooling-versions": (
        "tooling versions",
        r"\b(node|dotnet|\.net|python|ruby|java|go)\b[^\n]{0,40}\b\d+(\.\d+)?"
        r"|\b(nvmrc|tool-versions|global\.json|engines)\b",
    ),
    "how-to-run": (
        "how to run it",
        r"\b(npm (run )?start|ng serve|dotnet run|docker compose up|docker-compose up"
        r"|flask run|rails s(erver)?|make run|running the (app|project|application))"
        r"|\./(install|bootstrap|setup|run)\b",
    ),
    "how-to-test": (
        "how to test it",
        r"\b(npm (run )?test|yarn test|dotnet test|pytest|jest|vitest|go test|rspec"
        r"|run(ning)? (the )?(unit )?tests)"
        r"|^#{1,6} .*\btest|^\|\s*test\b",
    ),
    "structure": (
        "structure / architecture",
        r"\b(architecture|project structure|repository layout|directory (layout|structure)"
        r"|folder structure|bounded context|module layout)",
    ),
    "config-env": (
        "config & env vars",
        r"\b(environment variable|env var|appsettings|configuration key|config key"
        r"|comes from the environment)|(^|\s)\.env|\benv\.example",
    ),
    "deploy-steps": (
        "deploy / release steps",
        r"\b(deploy(ment|ing|s)?|release (process|steps)|publish(ing)? (a )?release)",
    ),
    "rollback": (
        "how to roll back",
        r"\b(roll ?back|rolling back|revert (the )?(deploy|release)"
        r"|redeploy[^\n]{0,40}(previous|earlier|prior|last known)"
        r"|deploy[^\n]{0,40}(previous|earlier|prior) (tag|release|version))",
    ),
    "public-api": ("public API", r"\b(public api|api reference|exported|usage example)"),
    "versioning": (
        "versioning & compatibility",
        r"\b(semver|semantic version|versioning|compatib)",
    ),
    "commands-flags": ("commands & flags", r"(--help|\busage:|\bflags\b|\boptions\b)"),
    "exit-codes": ("exit codes", r"\bexit (code|status)"),
    "what-it-manages": (
        "what it manages",
        r"\b(manages|provisions|what('s| is) in here|topics?)\b",
    ),
    "bootstrap": (
        "bootstrap on a fresh machine",
        r"\b(bootstrap|fresh (machine|install)|new machine)",
    ),
    "os-parity": ("OS parity", r"\b(macos|mac os|linux|ubuntu|debian|windows)\b"),
    "ownership": (
        "who to ask / ownership",
        r"\b(maintainer|code ?owner|who to (ask|contact)|point of contact|owned by|team:)",
    ),
    "glossary": (
        "domain glossary",
        r"\b(glossary|terminology|domain (model|language|term)|ubiquitous language)",
    ),
}

BASE_TOPICS = [
    "what-it-is",
    "setup",
    "tooling-versions",
    "how-to-run",
    "how-to-test",
    "structure",
    "ownership",
    "glossary",
]

ARCHETYPE_TOPICS = {
    "deployed-service": ["config-env", "deploy-steps", "rollback"],
    "library": ["public-api", "versioning"],
    "cli": ["commands-flags", "config-env", "exit-codes"],
    "infra": ["what-it-manages", "bootstrap", "os-parity"],
}

# A base topic that stops making sense for a kind. An infra/dotfiles repo has no business
# domain, so asking it for a glossary reports noise rather than a gap.
ARCHETYPE_EXEMPTIONS = {"infra": ["glossary"]}


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


def has_uncommitted_work(repo):
    """Report whether the working tree has changes worth auditing.

    Keeps the hook silent in a repo that was only read during the session.

    :param repo: repository root path
    :return: True when tracked files differ from HEAD or untracked files exist
    """
    if run_git(repo, "diff", "HEAD", "--name-only").strip():
        return True
    return bool(run_git(repo, "ls-files", "--others", "--exclude-standard").strip())


def read_json(path):
    """Parse a JSON file, returning an empty dict when it is absent or malformed.

    :param path: file path
    :return: parsed object, or {} on any failure
    """
    try:
        with path.open(encoding="utf-8", errors="ignore") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def detect_archetypes(repo):
    """Classify the repo into zero or more project kinds from files it ships.

    A repo can be several at once (a published CLI that is also a library); the caller unions
    their required topics.

    :param repo: repository root path
    :return: sorted list of archetype names
    """
    found = set()

    deployed = ["Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Procfile", "fly.toml"]
    if any((repo / name).exists() for name in deployed):
        found.add("deployed-service")
    if list(repo.glob(".github/workflows/*deploy*")) or list(repo.glob("**/k8s/*.y*ml")):
        found.add("deployed-service")

    package = read_json(repo / "package.json")
    if package:
        if package.get("bin"):
            found.add("cli")
        exports = any(package.get(key) for key in ("main", "module", "exports", "types"))
        if exports and not package.get("private"):
            found.add("library")

    if (repo / "pyproject.toml").exists():
        text = read_text(repo / "pyproject.toml")
        if "[project.scripts]" in text:
            found.add("cli")
        elif "[project]" in text:
            found.add("library")

    infra = ["dotbot.conf.yaml", "ansible.cfg", ".chezmoiroot", "install.sh", "bootstrap"]
    if any((repo / name).exists() for name in infra):
        found.add("infra")

    return sorted(found)


def read_text(path):
    """Read a file as text, returning "" when it is unreadable or oversized.

    :param path: file path
    :return: file contents, or "" on any failure
    """
    try:
        if path.stat().st_size > MAX_DOC_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def collect_docs(repo):
    """Concatenate every documentation file the repo ships.

    :param repo: repository root path
    :return: tuple of (combined lowercase text, README text as written)
    """
    blob = []
    readme = ""
    seen = set()
    for pattern in DOC_GLOBS:
        for path in sorted(repo.glob(pattern)):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            text = read_text(path)
            if not text:
                continue
            blob.append(text)
            if not readme and path.parent == repo and path.name.upper().startswith("README"):
                readme = text
    return "\n".join(blob).lower(), readme


def required_topics(archetypes):
    """Build the ordered topic list a repo of these kinds must cover.

    :param archetypes: archetype names from detect_archetypes
    :return: list of topic slugs, base floor first, without duplicates
    """
    slugs = list(BASE_TOPICS)
    for archetype in archetypes:
        for slug in ARCHETYPE_TOPICS.get(archetype, []):
            if slug not in slugs:
                slugs.append(slug)
    exempt = {slug for archetype in archetypes for slug in ARCHETYPE_EXEMPTIONS.get(archetype, [])}
    return [slug for slug in slugs if slug not in exempt]


def covers(slug, docs, readme):
    """Decide whether the docs show evidence of a floor topic.

    `what-it-is` is judged by absence of generator boilerplate rather than by keyword, because
    every scaffold README describes *something* while saying nothing about this project.

    :param slug: topic slug
    :param docs: combined lowercase documentation text
    :param readme: root README text as written
    :return: True when the topic looks covered
    """
    if slug == "what-it-is":
        if not readme.strip():
            return False
        return not any(marker.search(readme) for marker in SCAFFOLD_MARKERS)
    pattern = TOPICS[slug][1]
    return bool(re.search(pattern, docs, re.MULTILINE))


def find_gaps(repo):
    """Determine which coverage-floor topics this repo's docs never address.

    :param repo: repository root path
    :return: tuple of (archetypes, list of missing topic slugs)
    """
    archetypes = detect_archetypes(repo)
    docs, readme = collect_docs(repo)
    missing = [slug for slug in required_topics(archetypes) if not covers(slug, docs, readme)]
    return archetypes, missing


def write_log(repo, missing):
    """Append a dry-run finding to the hook log, creating the log directory as needed.

    :param repo: repository root path
    :param missing: missing topic slugs
    """
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"{repo}\t{','.join(missing)}\n")
    except OSError:
        pass


def build_message(archetypes, missing):
    """Compose the operator-facing message naming the uncovered topics.

    :param archetypes: detected archetype names
    :param missing: missing topic slugs
    :return: message string
    """
    kinds = ", ".join(archetypes) if archetypes else "generic project"
    items = "\n".join(f"  - {TOPICS[slug][0]}" for slug in missing)
    return (
        f"Documentation coverage floor not met ({kinds}). No doc in this repo answers:\n"
        f"{items}\n"
        "The floor is in ~/.claude/CLAUDE.md (Project documentation). Fill a gap when your work "
        "touches that area, and report the rest rather than backfilling the whole set unasked.\n"
        "Use the `writing-project-docs` skill for the procedure."
    )


def run_cli(path):
    """Run the check as a standalone command, for CI or a manual sweep.

    :param path: directory inside the repo to check
    :return: process exit code, 1 when anything is missing
    """
    repo = repo_root(path) or Path(path).resolve()
    archetypes, missing = find_gaps(repo)
    if not missing:
        kinds = ", ".join(archetypes) if archetypes else "generic project"
        print(f"docs coverage floor: OK ({kinds})")
        return 0
    print(build_message(archetypes, missing), file=sys.stderr)
    return 1


def run_hook():
    """Run the check as a Stop hook, honouring DOCS_FLOOR_HOOK_MODE.

    :return: process exit code, 2 when enforcing a finding
    """
    mode = os.environ.get("DOCS_FLOOR_HOOK_MODE", "dry-run").lower()
    if mode == "off":
        return 0

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if data.get("stop_hook_active"):
        return 0

    repo = repo_root(data.get("cwd") or os.getcwd())
    if not repo or not has_uncommitted_work(repo):
        return 0

    archetypes, missing = find_gaps(repo)
    if not missing:
        return 0

    message = build_message(archetypes, missing)
    if mode == "enforce":
        print(f"BLOCKED by user policy: {message}", file=sys.stderr)
        return 2

    write_log(repo, missing)
    print(f"[dry-run] {message}", file=sys.stderr)
    return 0


def main():
    """Entry point: dispatch to the CLI check or the Stop hook."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--path", help="check this directory and exit, instead of reading a hook payload"
    )
    args = parser.parse_args()

    sys.exit(run_cli(args.path) if args.path else run_hook())


if __name__ == "__main__":
    main()
