#!/usr/bin/env python3
"""PreToolUse(Write|Edit|NotebookEdit|Bash) guard: keep typographic dashes out of written files.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Code & artifacts):
a plain hyphen, never an em dash or an en dash. The user reads them as a tell that text was
machine-written, and does not want them anywhere.

The check is on what an edit ADDS, not on what a file contains. An edit that carries an existing
dash through unchanged passes, so touching a line that already has one is never wedged; only
introducing a new one is refused. Blocking rather than prompting is deliberate: the fix is always
available, and the right fix is usually to reword the sentence rather than swap the character for
a hyphen, which often reads worse than either.

Exit 2 + stderr blocks the tool call and feeds the reason back to the model.

Scope is file content, whichever tool carries it. Write/Edit/NotebookEdit is the obvious path;
`Bash` is the one that was missing, because content written through a heredoc (`cat > f <<EOF`)
never touches the Write tool and so bypassed a Write-only matcher entirely. Only heredoc BODIES
are read there, since those are the content; other shell write forms (`echo >> f`, `sed -i`) are
still uncovered, and a plain `grep` for a dash is deliberately left alone.

Nothing in the harness lets a hook see or rewrite the assistant's own chat prose, which is where
the user first noticed the habit, so the rule carries that half alone.

The dashes are written as escapes below so this file never contains the characters it blocks, and
its tests assemble them the same way.
"""

import sys
from pathlib import Path

from _hookutil import heredoc_bodies, read_payload

EM_DASH = "\u2014"

EN_DASH = "\u2013"

BANNED = (EM_DASH, EN_DASH)

NAMES = {EM_DASH: "em dash (U+2014)", EN_DASH: "en dash (U+2013)"}


def count_banned(text):
    """Count typographic dashes in a piece of text.

    :param text: text to scan
    :return: total number of banned dash characters
    """
    return sum(text.count(dash) for dash in BANNED)


def names_in(text):
    """Name the banned dashes present in a piece of text.

    :param text: text to scan
    :return: human-readable list of the dash kinds found
    """
    return ", ".join(NAMES[dash] for dash in BANNED if dash in text)


def existing_text(path):
    """Read a file's current content, treating anything unreadable as empty.

    A path that does not exist yet is a new file, where every dash in the content is added.

    :param path: file path
    :return: current content, empty when the file cannot be read
    """
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        return ""


def added_count(tool, tool_input):
    """Report how many banned dashes a tool call would add.

    :param tool: tool name
    :param tool_input: the tool's input payload
    :return: (added, text) where text is the content the count came from
    """
    if tool == "Write":
        content = tool_input.get("content") or ""
        current = existing_text(tool_input.get("file_path") or "")
        return count_banned(content) - count_banned(current), content

    if tool == "Edit":
        new = tool_input.get("new_string") or ""
        old = tool_input.get("old_string") or ""
        return count_banned(new) - count_banned(old), new

    if tool == "Bash":
        written = "\n".join(heredoc_bodies(tool_input.get("command") or ""))
        return count_banned(written), written

    if tool == "NotebookEdit":
        source = tool_input.get("new_source") or ""
        return count_banned(source), source

    return 0, ""


def main():
    """Block a file write that would introduce a typographic dash."""
    data = read_payload()
    if data is None:
        sys.exit(0)

    tool = data.get("tool_name") or ""
    added, text = added_count(tool, data.get("tool_input") or {})

    if added <= 0:
        sys.exit(0)

    print(
        f"BLOCKED by user policy: this edit adds {added} typographic dash(es) "
        f"[{names_in(text)}].\n"
        "See ~/.claude/CLAUDE.md (Working Preferences): use a plain hyphen, never an em or en "
        "dash.\nPrefer rewording the sentence over swapping the character in place, since a "
        "hyphen standing in for an em dash usually reads worse than either.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
