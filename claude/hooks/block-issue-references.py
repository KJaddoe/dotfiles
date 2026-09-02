#!/usr/bin/env python3
"""PreToolUse(Write|Edit|NotebookEdit|Bash) guard: keep tracker references out of written files.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Code & artifacts):
never cite an issue or ticket in a repository artifact. The tracker and the repository have
different lifetimes. Issues get closed, renumbered, migrated between trackers and deleted, and
what survives in the file is a pointer to nothing. `git log` and `git blame` carry the history
instead, and they cannot rot.

Four shapes are refused:

- a citation cue next to a number (`fixes`, `closes`, `see issue`, ...), anywhere in the content,
  including inside a string, because the cue is what makes it a citation rather than a quantity
- a URL into a tracker: a GitHub issue or pull, a GitLab issue or merge request, a Jira browse link
- a Jira-style project key. Standards identifiers share that shape exactly, so `UTF-8`, `SHA-256`,
  `RFC-7231` and `CVE-2024-1234` are allowed by name, as are toolchain versions like `JDK-17`:
  they are durable and worth citing. The list is a running one, and a new collision joins it
- a bare hash-and-number, but only in PROSE: a prose file, or a comment line in a source file.
  Source that is not a comment is left alone, since a number there is far more likely to be data

Two things are deliberately allowed. Ordinals counting an item ("rule", "line", "step", ...) name
a position in a list rather than a ticket. Hex colours never match, because a run of six or eight
digits is a colour rather than a plausible issue number, and anything with a letter in it is not
a number at all.

The check is on what an edit ADDS, not on what a file contains, matching
block-typographic-dashes.py. An edit that carries an existing citation through unchanged passes,
so touching a legacy line is never wedged and a cleanup pass is never blocked; only introducing a
new reference is refused.

Exit 2 + stderr blocks the tool call and feeds the reason back to the model.

Scope is file content, whichever tool carries it. Under `Bash` only heredoc BODIES are read, since
those are the content; other shell write forms (`echo >> f`, `sed -i`) are still uncovered, and a
`grep` for a reference is deliberately left alone.

Nothing in the harness lets a hook see the assistant's chat prose, and a commit message, a pull
request body and a branch name are all outside a hook's reach as file content. That is correct:
the rule permits a number in exactly those places, because their lifetime matches the tracker's.

Every pattern below is assembled from a HASH constant rather than written literally, so this file
never contains a reference it would itself refuse.
"""

import re
import sys
from pathlib import Path

from _hookutil import heredoc_bodies, read_payload

HASH = "#"

PROSE_SUFFIXES = {".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc", ".org"}

LINE_COMMENT_STARTS = ("//", "--", ";", "*", "<!--", "%")

INLINE_COMMENT_MARKERS = ("//", "/*", "<!--", "--", ";")

CUE_WORDS = (
    "fix|fixes|fixed|close|closes|closed|resolve|resolves|resolved|ref|refs|references|"
    "see|issue|issues|ticket|tickets|bug|story|task|card|pr"
)

ORDINAL_WORDS = set(
    "rule rules line lines item items step steps option options figure fig table section note "
    "point phase stage part chapter page row column col example case entry version round "
    "attempt level tier day week question number no num".split()
)

STANDARDS_PREFIXES = set(
    "UTF SHA MD RFC ISO ASCII IEEE ANSI CVE CWE PEP WCAG ARIA HTTP TLS SSL AES RSA ECMA POSIX "
    "NIST FIPS PKCS OAUTH JWT UTC GMT USB PCI DDR ARM X IPV EN DIN BS SP GPL LGPL APL BSD MIT "
    "CC SPDX K8S EC S COVID JDK JRE JVM ES PHP NET GTK QT LTS GCC LLVM SDL".split()
)

CUED = re.compile(rf"\b(?:{CUE_WORDS})\b[\s:,]*{HASH}\d+", re.IGNORECASE)

GH_DASH = re.compile(r"\bGH-\d+\b", re.IGNORECASE)

TRACKER_URL = re.compile(
    r"https?://\S*?(?:/issues/\d+|/pull/\d+|/pulls/\d+|/merge_requests/\d+"
    r"|/-/issues/\d+|/browse/[A-Za-z][A-Za-z0-9]+-\d+)",
    re.IGNORECASE,
)

PROJECT_KEY = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-(\d{1,6})\b")

BARE_NUMBER = re.compile(rf"{HASH}(\d{{1,6}})\b")

WORD_BEFORE = re.compile(r"([A-Za-z]+)[\s:,]*$")


def is_prose_suffix(path):
    """Report whether a path names a file that is prose all the way through.

    :param path: file path, possibly empty
    :return: True when the suffix is a prose document suffix
    """
    if not path:
        return False
    return Path(path).suffix.lower() in PROSE_SUFFIXES


def line_is_prose(line, index, prose_file):
    """Report whether a position in a line sits in prose rather than in code.

    A prose file is prose throughout. Elsewhere only comments count, so a number in an
    expression or a string literal is left alone.

    :param line: the full line the match sits on
    :param index: character offset of the match within the line
    :param prose_file: whether the whole file is a prose document
    :return: True when the position counts as prose
    """
    if prose_file:
        return True

    stripped = line.lstrip()
    if stripped.startswith(HASH) and not stripped.startswith(HASH + "!"):
        return True
    if stripped.startswith(LINE_COMMENT_STARTS):
        return True

    before = line[:index]
    return any(marker in before for marker in INLINE_COMMENT_MARKERS)


def is_ordinal(line, index):
    """Report whether a hash-and-number is counting an item rather than citing a ticket.

    :param line: the full line the match sits on
    :param index: character offset of the match within the line
    :return: True when an ordinal word introduces the number
    """
    word = WORD_BEFORE.search(line[:index])
    return bool(word) and word.group(1).lower() in ORDINAL_WORDS


def is_colour(digits):
    """Report whether a run of digits is a hex colour rather than a number reference.

    Six and eight digits are a colour; no tracker numbers issues that far.

    :param digits: the digit run following the hash
    :return: True when the run is colour-shaped
    """
    return len(digits) in (6, 8)


def bare_hits(text, prose_file):
    """Find bare hash-and-number references sitting in prose.

    :param text: content to scan
    :param prose_file: whether the whole file is a prose document
    :return: list of the matched references
    """
    found = []
    for line in text.splitlines():
        for match in BARE_NUMBER.finditer(line):
            if is_colour(match.group(1)):
                continue
            if not line_is_prose(line, match.start(), prose_file):
                continue
            if is_ordinal(line, match.start()):
                continue
            found.append(match.group(0))
    return found


def key_hits(text):
    """Find Jira-style project keys, skipping standards identifiers that share the shape.

    :param text: content to scan
    :return: list of the matched keys
    """
    return [
        match.group(0)
        for match in PROJECT_KEY.finditer(text)
        if match.group(1).upper() not in STANDARDS_PREFIXES
    ]


def references(text, prose_file):
    """Collect every tracker reference in a piece of content.

    :param text: content to scan
    :param prose_file: whether the whole file is a prose document
    :return: list of the matched references
    """
    if not text:
        return []

    found = [match.group(0) for match in CUED.finditer(text)]
    found += [match.group(0) for match in GH_DASH.finditer(text)]
    found += [match.group(0) for match in TRACKER_URL.finditer(text)]
    found += key_hits(text)
    found += bare_hits(text, prose_file)
    return found


def existing_text(path):
    """Read a file's current content, treating anything unreadable as empty.

    A path that does not exist yet is a new file, where every reference in the content is added.

    :param path: file path
    :return: current content, empty when the file cannot be read
    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        return ""


def heredoc_targets_prose(command):
    """Report whether a shell command redirects into a prose document.

    :param command: the shell command
    :return: True when any redirect target has a prose suffix
    """
    return any(is_prose_suffix(target) for target in re.findall(r">>?\s*([^\s;&|]+)", command))


def added(tool, tool_input):
    """Report the tracker references a tool call would add.

    :param tool: tool name
    :param tool_input: the tool's input payload
    :return: list of references present in what the call adds
    """
    path = tool_input.get("file_path") or ""
    prose = is_prose_suffix(path)

    if tool == "Write":
        content = tool_input.get("content") or ""
        return surplus(references(content, prose), references(existing_text(path), prose))

    if tool == "Edit":
        new = references(tool_input.get("new_string") or "", prose)
        old = references(tool_input.get("old_string") or "", prose)
        return surplus(new, old)

    if tool == "Bash":
        command = tool_input.get("command") or ""
        bodies = "\n".join(heredoc_bodies(command))
        return references(bodies, heredoc_targets_prose(command))

    if tool == "NotebookEdit":
        markdown = (tool_input.get("cell_type") or "") == "markdown"
        return references(tool_input.get("new_source") or "", markdown)

    return []


def surplus(new, old):
    """Report the references an edit adds, ignoring those it carries through unchanged.

    :param new: references in the incoming content
    :param old: references in the content being replaced
    :return: the references that are genuinely new
    """
    remaining = list(old)
    extra = []
    for reference in new:
        if reference in remaining:
            remaining.remove(reference)
        else:
            extra.append(reference)
    return extra


def main():
    """Block a file write that would introduce a tracker reference."""
    data = read_payload()
    if data is None:
        sys.exit(0)

    tool = data.get("tool_name") or ""
    extra = added(tool, data.get("tool_input") or {})

    if not extra:
        sys.exit(0)

    listed = ", ".join(sorted(set(extra))[:5])
    print(
        f"BLOCKED by user policy: this edit adds {len(extra)} tracker reference(s) [{listed}].\n"
        "See ~/.claude/CLAUDE.md (Working Preferences): never cite an issue or ticket number in "
        "anything that lives in the repository.\nIssues get closed, renumbered, migrated and "
        "deleted, leaving a pointer to nothing; git log and git blame keep the history instead.\n"
        "Write the substance the number stood for: what the behaviour is, what broke, and why it "
        "must not come back. A number belongs only in a commit message, a pull request body, or a "
        "branch name, where the medium's lifetime matches the tracker's.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
