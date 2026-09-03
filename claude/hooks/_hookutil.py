#!/usr/bin/env python3
"""Git helpers and command patterns shared by the hooks in this directory.

The hooks keep needing the same handful of things: run a git command without letting a failure
escape, resolve the repository root for the session's cwd, recognise a commit invocation and its
short flags inside a shell command, and classify what a `gh` invocation would do to GitHub. Each
was duplicated across hooks before this module existed.

The `gh_*` helpers answer one question, "which gh invocations does this command contain and which
of them write", for two callers that react to the answer differently: `require-gh-approval.py`
puts a write to the user for approval, `block-claude-attribution.py` scans a write for attribution.
The allowlist reasoning behind the classification lives in the former's module docstring.

Importing this works because Python puts a script's OWN directory at the front of `sys.path`,
and the hooks are invoked as `python3 ~/.claude/hooks/<name>.py`, so `~/.claude/hooks` leads
the path regardless of the cwd git happens to be run from. Loading a hook by file path instead
(`importlib.util.spec_from_file_location`, as the tests do) does NOT do that, so a caller taking
that route has to put this directory on `sys.path` itself.

The leading underscore marks it as internal to the hooks directory: it is not a hook, and
`settings.json` never invokes it.
"""

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

GIT_TIMEOUT_SECONDS = 8

GIT_FLAGS = r"(?:\s+-{1,2}[\w-]+(?:[= ]\S+)?)*"

COMMIT_SUBCOMMAND = re.compile(rf"\bgit\b{GIT_FLAGS}\s+commit\b", re.IGNORECASE)

HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# `git -C <dir>` names the repository outright, so it wins over any preceding `cd`.
GIT_C_TARGET = re.compile(rf"\bgit\b{GIT_FLAGS}\s+-C\s+([^\s;&|]+)")

# A `cd` in command position. `cd -` and a bare `cd` are excluded: neither names a directory the
# command text can resolve.
CD_TARGET = re.compile(r"(?:^|[;&|]|&&)\s*cd\s+(?!-)([^\s;&|]+)")


PROMPTING_MODES = {"default", "plan"}

SUMMARY_LINE_LIMIT = 40

RULE_REFERENCE = "~/.claude/CLAUDE.md -> Working Preferences"

SHELL_SEPARATORS = re.compile(r"&&|\|\||;|\||\n")

# Operator tokens a punctuation-aware lexer emits, used to find where one command ends.
SEPARATOR_TOKENS = {"&&", "||", ";", "|", "&", "(", ")", "\n"}

ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# Wrappers that can sit in front of the real command without changing what it is.
COMMAND_PREFIXES = {"command", "env", "nohup", "sudo", "time", "xargs"}

# Every top-level `gh` command, so the subcommand can be located without guessing which tokens
# are flag values. A command absent from this set is unrecognised and therefore gated.
GH_TOP_LEVEL = {
    "alias",
    "api",
    "attestation",
    "auth",
    "browse",
    "cache",
    "codespace",
    "completion",
    "config",
    "extension",
    "gist",
    "gpg-key",
    "issue",
    "label",
    "org",
    "pr",
    "project",
    "release",
    "repo",
    "ruleset",
    "run",
    "search",
    "secret",
    "ssh-key",
    "status",
    "variable",
    "workflow",
}

# Top-level commands that only ever read.
GH_READ_ONLY_COMMANDS = {"browse", "completion", "search", "status"}

# Verbs that only read, whichever group they belong to. `clone` and `checkout` write locally
# but publish nothing. `gh project` spells its read verbs with a hyphen, and every other
# hyphenated project verb (item-create, field-delete, …) writes.
GH_READ_ONLY_VERBS = {
    "checkout",
    "checks",
    "clone",
    "diff",
    "download",
    "field-list",
    "item-list",
    "list",
    "status",
    "view",
    "watch",
}

# Verbs carved out whole, because nothing they can do publishes prose or notifies anyone:
# `gh issue develop` publishes a branch name, and `gh project item-add` places an issue on a
# board. See the module docstring of require-gh-approval.py.
GH_ALLOWED_PAIRS = {("issue", "develop"), ("project", "item-add")}

# `edit` can rewrite the title or body, which IS publishing, so it cannot be carved out by verb.
# It is carved out by FLAG instead: see `only_reassigns_to_self`.
GH_ASSIGNABLE_PAIRS = {("issue", "edit"), ("pr", "edit")}

GH_ASSIGNMENT_FLAGS = {"--add-assignee", "--remove-assignee"}

# Flags that pick the target without changing it, so they may accompany an assignment.
GH_TARGETING_FLAGS = {"-R", "--repo"}

# The only assignee the carve-out accepts. Assigning someone ELSE puts work in their queue and
# notifies them, which is not a mundane act and is not what the carve-out is for.
GH_SELF = {"@me"}

# `gh project item-edit` sets one board field's value, the bookkeeping the rules mandate before
# work starts. It also rewrites a DRAFT issue's title and body, which IS publishing, so like
# `issue edit` it is carved out by FLAG rather than by verb: see `only_edits_board_fields`.
GH_PROJECT_FIELD_PAIRS = {("project", "item-edit")}

# Flags that set or clear a field's value, and nothing else.
GH_PROJECT_FIELD_FLAGS = {
    "--clear",
    "--date",
    "--iteration-id",
    "--number",
    "--single-select-option-id",
    "--text",
}

# Flags that pick the item and field, or shape the output, without changing anything. `--title`
# and `--body` are deliberately absent: they edit draft-issue prose, so they fail closed.
GH_PROJECT_TARGETING_FLAGS = {
    "--field-id",
    "--format",
    "--id",
    "--jq",
    "--owner",
    "--project-id",
    "--template",
    "-q",
    "-t",
}

# `--help` makes gh print usage and exit without touching the API, so an invocation asking for it
# reads whatever verb it names. Only the LONG form counts: `-h` is not universally help in gh
# (`gh auth login -h` is `--hostname`). It must also be the FIRST flag-like token, so a `--help`
# bound as another flag's VALUE (`gh issue create -t --help`) still gates.
GH_HELP_FLAG = "--help"

GH_API_PAYLOAD_FLAGS = {"-f", "--raw-field", "-F", "--field", "--input"}

GH_METHOD_FLAGS = {"-X", "--method"}

# `gh api graphql` is the one endpoint the method rule cannot classify. GraphQL is always a POST
# and always carries its document in a field flag, so classifying by method gated every read; the
# board queries this repo's workflow depends on go through it, because `projectV2` has no REST
# endpoint. The operation type in the document decides instead.
GRAPHQL_QUERY_FIELD = "query"

# String literals and comments, lexed together so whichever opens first wins: a `#` inside a
# string is not a comment, and a quote inside a comment does not open a string.
GRAPHQL_IGNORED = re.compile(r'"""(?:.|\n)*?"""|"(?:\\.|[^"\\\n])*"|#[^\n]*')

# What may remain at a document's top level once selection sets and variable definitions are
# blanked: operation and fragment keywords, the names they carry, and directives. Anything else
# (a `$` from an unexpanded shell variable, a backtick, a path) means this is not a document the
# hook can read, and an unreadable document fails closed.
GRAPHQL_TOP_LEVEL = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_]*|@[A-Za-z_][A-Za-z0-9_]*|[\s,])*")

# An executable document's top level holds only operations and fragments, so a keyword scan there
# is exact. `subscription` is included because only a query reads.
GRAPHQL_WRITE_OPERATION = re.compile(r"\b(?:mutation|subscription)\b")

GRAPHQL_SUBSCRIPTION = re.compile(r"\bsubscription\b")

# Every executable operation and fragment keyword. A document declaring more than one of them
# cannot be classified by reading a single selection set, so it fails closed.
GRAPHQL_OPERATIONS = re.compile(r"\b(?:query|mutation|subscription|fragment)\b")

# What may remain of a root selection set once nested sets and arguments are blanked: field
# names, aliases, directives and separators. A fragment spread's `...` is not here, so a document
# hiding its root fields behind one cannot be read and fails closed.
GRAPHQL_SELECTION = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_]*|@[A-Za-z_][A-Za-z0-9_]*|[:\s,])*")

# A root selection, whose field name is what follows an optional `alias:`.
GRAPHQL_FIELD = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_]*\s*:\s*)?([A-Za-z_][A-Za-z0-9_]*)")

# The only mutations carved out: each sets or clears ONE field value on ONE board item, which is
# the bookkeeping ~/.claude/CLAUDE.md mandates before work starts. Every other mutation is gated.
GRAPHQL_BOARD_FIELD_MUTATIONS = {
    "clearProjectV2ItemFieldValue",
    "updateProjectV2ItemFieldValue",
}


def clip_summary(text):
    """Trim a summary to a length that stays readable inside a permission prompt.

    :param text: full summary text
    :return: the text, truncated with a count of the omitted lines
    """
    lines = text.splitlines()
    if len(lines) <= SUMMARY_LINE_LIMIT:
        return text
    hidden = len(lines) - SUMMARY_LINE_LIMIT
    return "\n".join(lines[:SUMMARY_LINE_LIMIT] + [f"... {hidden} more lines"])


def approval_decision(mode, action, summary):
    """Build the PreToolUse decision that puts an action to the user for approval.

    "ask" is only honoured where a prompt can render. In the modes that auto-approve, asking
    would silently become allowing, precisely where the model runs unsupervised, so the action
    is denied instead, with instructions to get approval in the conversation and re-run from
    `default`. Allowing is never an outcome.

    :param mode: the session's reported permission mode
    :param action: what is being gated, named for the user ("commit", "push")
    :param summary: summary of what the action would do
    :return: (permissionDecision, permissionDecisionReason) pair
    """
    if mode in PROMPTING_MODES:
        return "ask", (
            f"This {action} needs your explicit approval ({RULE_REFERENCE}).\n\n{summary}\n\n"
            "Approve only if this is what you reviewed."
        )

    return "deny", (
        f"BLOCKED: permission mode is '{mode}', where an approval prompt is auto-approved, so "
        f"this {action} cannot be put to the user ({RULE_REFERENCE}).\n\n"
        f"{summary}\n\n"
        f"Show this to the user, get explicit approval in the conversation, and re-run the "
        f"{action} in 'default' permission mode."
    )


def emit_decision(decision, reason):
    """Print a PreToolUse decision in the shape the harness expects.

    :param decision: "ask", "deny" or "allow"
    :param reason: text shown to the user, or fed back to the model on a denial
    """
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def read_payload():
    """Read a hook payload from stdin.

    Shared by every event, not only PreToolUse: the payload envelope is the same shape whichever
    hook is being invoked. A malformed payload is reported as absent rather than raised, so a
    guard can never take a tool call down with it.

    :return: the parsed payload, or None when stdin does not carry one
    """
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None


def read_bash_payload():
    """Read a PreToolUse payload from stdin, for the guards that only care about Bash.

    Every PreToolUse(Bash) guard opens the same way: parse stdin, ignore other tools, pull the
    command out.

    :return: (payload, command) for a Bash tool call, or (None, "") for anything else
    """
    data = read_payload()
    if data is None or data.get("tool_name") != "Bash":
        return None, ""

    return data, (data.get("tool_input") or {}).get("command") or ""


def strip_heredocs(cmd):
    """Return `cmd` with heredoc bodies removed, leaving the commands themselves.

    A heredoc body is data the shell feeds to a program (a script being written, a document,
    a payload), not something the shell executes. Matching command patterns against it is how a
    guard ends up blocking a script that merely *mentions* the thing it guards against.

    The delimiter lines are kept so the surrounding command text stays intact. Callers that care
    about the CONTENT of a command (a commit message passed on stdin, say) must scan the original
    string; this is for deciding what is being INVOKED.

    :param cmd: full shell command, possibly multi-line
    :return: the command with heredoc bodies elided
    """
    lines = cmd.split("\n")
    kept = []
    index = 0
    while index < len(lines):
        line = lines[index]
        kept.append(line)
        match = HEREDOC_START.search(line)
        index += 1
        if not match:
            continue
        delimiter = match.group(2)
        while index < len(lines) and lines[index].strip() != delimiter:
            index += 1
        if index < len(lines):
            kept.append(lines[index])
            index += 1
    return "\n".join(kept)


def heredoc_bodies(cmd):
    """Return the heredoc bodies in `cmd`: the content it feeds to a program.

    The exact inverse of `strip_heredocs`. That one answers "what is being INVOKED" by discarding
    the data; this answers "what is being WRITTEN" by keeping only the data. A guard that inspects
    file CONTENT needs this, because content passed through a heredoc never reaches the Write tool
    and so is invisible to a Write/Edit matcher.

    :param cmd: full shell command, possibly multi-line
    :return: list of heredoc bodies, delimiter lines excluded
    """
    lines = cmd.split("\n")
    bodies = []
    index = 0
    while index < len(lines):
        match = HEREDOC_START.search(lines[index])
        index += 1
        if not match:
            continue
        delimiter = match.group(2)
        body = []
        while index < len(lines) and lines[index].strip() != delimiter:
            body.append(lines[index])
            index += 1
        index += 1
        bodies.append("\n".join(body))
    return bodies


def short_flag(cmd, letter):
    """Report whether `letter` is present as a short flag in `cmd`.

    Matches the bare flag and clustered forms (`-a`, `-am`, `-vam`) while ignoring long flags
    that merely contain the letter, so `--amend` does not read as `-a`. Matching is
    case-sensitive, keeping opposites like signing and sign-off distinct.

    :param cmd: full shell command
    :param letter: single flag letter to look for
    :return: True when the letter is present as a short flag
    """
    return bool(re.search(rf"(?<![\w-])-[A-Za-z]*{re.escape(letter)}[A-Za-z]*(?![\w-])", cmd))


def command_head(tokens):
    """Strip the env assignments and wrappers that can precede the real command.

    `FOO=1 gh ...` and `sudo gh ...` are still gh invocations. A wrapper carrying its own
    arguments (`sudo -u someone gh ...`) is NOT resolved, and reads as not-gh.

    :param tokens: one command's tokens
    :return: the tokens from the real command word onward
    """
    index = 0
    while index < len(tokens) and (
        ENV_ASSIGNMENT.match(tokens[index]) or tokens[index] in COMMAND_PREFIXES
    ):
        index += 1
    return tokens[index:]


def gh_invocations(cmd):
    """Split a shell command into the argument list of each `gh` invocation it contains.

    `gh` counts only in COMMAND POSITION, never as a bare word somewhere in the arguments.
    The word appears in ordinary prose, and treating it as an invocation gated `grep -rn gh docs/`
    and, worse, any multi-line commit message with "gh" on a line of its own: the newline read as
    a command separator, which broke the quoting and left `gh` looking like a command.

    That is also why the whole command is lexed BEFORE it is split on operators, rather than
    split on a newline regex first: a quoted argument spanning lines has to survive as one token.

    :param cmd: full shell command, heredoc bodies already stripped
    :return: list of token lists, one per gh invocation, each excluding the `gh` itself
    """
    try:
        lexer = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = cmd.split()

    found, segment = [], []
    for token in [*tokens, ";"]:
        if token in SEPARATOR_TOKENS:
            head = command_head(segment)
            if head and head[0] == "gh":
                found.append(head[1:])
            segment = []
        else:
            segment.append(token)
    return found


def gh_subcommand(tokens):
    """Resolve the (command, verb) pair a gh invocation targets.

    The command is matched against the known top-level set rather than taken positionally, so a
    global flag and its value (`gh --repo X pr view`) cannot be mistaken for the subcommand.

    :param tokens: gh arguments, excluding `gh`
    :return: (command, verb) with either element empty when it cannot be resolved
    """
    command = next((token for token in tokens if token in GH_TOP_LEVEL), "")
    if not command:
        return "", ""

    rest = tokens[tokens.index(command) + 1 :]
    verb = next((token for token in rest if not token.startswith("-")), "")
    return command, verb


def graphql_top_level(document):
    """Blank everything nested inside a GraphQL document, leaving its top level.

    Selection sets and variable definitions are where a document's data lives: a field named
    `clientMutationId`, an argument spelled `query:`, a `$cursor` variable. None of them say what
    the operation is, and all of them are noise a keyword scan would trip over.

    :param document: the GraphQL document text
    :return: the document with braced and parenthesised groups replaced by spaces
    """
    text = GRAPHQL_IGNORED.sub(" ", document)
    kept = []
    braces = 0
    parens = 0
    for char in text:
        if char == "{":
            braces += 1
        elif char == "}":
            braces = max(braces - 1, 0)
        elif braces == 0 and char == "(":
            parens += 1
        elif braces == 0 and char == ")":
            parens = max(parens - 1, 0)
        elif braces == 0 and parens == 0:
            kept.append(char)
            continue
        kept.append(" ")
    return "".join(kept)


def graphql_root_fields(document):
    """Return the field names an operation selects at the root of its selection set.

    Arguments and every nested selection are blanked, so what remains is the operation's own
    root selection: the fields that say what it actually does. An alias resolves to the field it
    names, because `x: deleteRepository` deletes a repository just the same.

    :param document: the GraphQL document text
    :return: the set of root field names, or None when the document cannot be read
    """
    text = GRAPHQL_IGNORED.sub(" ", document)
    start = text.find("{")
    if start < 0:
        return None

    kept = []
    depth = 0
    parens = 0
    for char in text[start:]:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif char == "(" and depth == 1:
            parens += 1
        elif char == ")" and depth == 1:
            parens = max(parens - 1, 0)
        elif depth == 1 and parens == 0:
            kept.append(char)
            continue
        kept.append(" ")
        if depth == 0:
            break

    selection = "".join(kept)
    if not GRAPHQL_SELECTION.fullmatch(selection):
        return None

    return {match.group(1) for match in GRAPHQL_FIELD.finditer(selection)}


def graphql_is_board_bookkeeping(document, top_level):
    """Report whether a writing document does nothing but set or clear board field values.

    The test is the whole root selection, not its first field, so a board mutation cannot smuggle
    a second one alongside it. A document declaring more than one operation, a subscription, or
    root fields hidden behind a fragment spread all fail closed: the selection read would not be
    provably the one that writes.

    :param document: the GraphQL document text
    :param top_level: the document's top level, per `graphql_top_level`
    :return: True when every root field is a board field mutation
    """
    if GRAPHQL_SUBSCRIPTION.search(top_level):
        return False

    if len(GRAPHQL_OPERATIONS.findall(top_level)) != 1:
        return False

    fields = graphql_root_fields(document)
    return bool(fields) and fields <= GRAPHQL_BOARD_FIELD_MUTATIONS


def graphql_document_writes(document):
    """Report whether a GraphQL document contains anything but read operations.

    :param document: the GraphQL document text
    :return: True when it writes, or cannot be read as a document at all
    """
    if "{" not in document:
        return True

    top_level = graphql_top_level(document)
    if not GRAPHQL_TOP_LEVEL.fullmatch(top_level):
        return True

    if not GRAPHQL_WRITE_OPERATION.search(top_level):
        return False

    return not graphql_is_board_bookkeeping(document, top_level)


def gh_graphql_writes(tokens):
    """Report whether a `gh api graphql` invocation would change anything.

    The document has to be a literal the hook can read. Passed by file (`--input`, `-F query=@f`)
    or behind a shell variable, what it does is unknowable here, so it is gated.

    :param tokens: gh arguments, excluding `gh`
    :return: True when the request would write
    """
    if any(token.partition("=")[0] == "--input" for token in tokens):
        return True

    documents = [
        value.partition("=")[2]
        for value in flag_values(tokens, GH_API_PAYLOAD_FLAGS)
        if value.partition("=")[0] == GRAPHQL_QUERY_FIELD
    ]
    if not documents:
        return True

    return any(graphql_document_writes(document) for document in documents)


def gh_api_writes(tokens):
    """Report whether a `gh api` invocation sends anything other than a GET.

    :param tokens: gh arguments, excluding `gh`
    :return: True when the request would write
    """
    if any(token.lstrip("/") == "graphql" for token in tokens):
        return gh_graphql_writes(tokens)

    for index, token in enumerate(tokens):
        if token in GH_METHOD_FLAGS and index + 1 < len(tokens):
            return tokens[index + 1].upper() != "GET"
        if token.startswith("--method="):
            return token.split("=", 1)[1].upper() != "GET"

    return any(token.split("=", 1)[0] in GH_API_PAYLOAD_FLAGS for token in tokens)


def flag_values(tokens, names):
    """Collect the values given to any of `names`, in both `--flag value` and `--flag=value` form.

    :param tokens: gh arguments, excluding `gh`
    :param names: flag names to collect values for
    :return: list of values
    """
    values = []
    for index, token in enumerate(tokens):
        name, _, inline = token.partition("=")
        if name not in names:
            continue
        if inline:
            values.append(inline)
        elif index + 1 < len(tokens):
            values.append(tokens[index + 1])
    return values


def only_reassigns_to_self(tokens):
    """Report whether an edit does nothing but assign the issue or PR to the user.

    Assigning yourself is bookkeeping: it publishes no prose, and the rules mandate it before
    starting work. Rewriting a title or body from the same subcommand is not, so this fails closed
    on any flag it does not recognise rather than allowlisting `edit` wholesale.

    :param tokens: gh arguments, excluding `gh`
    :return: True when the only mutation is assigning the user to it
    """
    names = {token.partition("=")[0] for token in tokens if token.startswith("-")}
    if not names & GH_ASSIGNMENT_FLAGS:
        return False
    if not names <= (GH_ASSIGNMENT_FLAGS | GH_TARGETING_FLAGS):
        return False

    values = flag_values(tokens, GH_ASSIGNMENT_FLAGS)
    return bool(values) and all(value in GH_SELF for value in values)


def only_edits_board_fields(tokens):
    """Report whether an item edit does nothing but set or clear a board field's value.

    A field value is bookkeeping: it publishes no prose and notifies nobody, and the rules mandate
    setting Status before work starts. The same subcommand also rewrites a draft issue's title and
    body, which IS publishing, so this fails closed on any flag it does not recognise rather than
    allowlisting `item-edit` wholesale.

    :param tokens: gh arguments, excluding `gh`
    :return: True when the only mutation is a board field value
    """
    names = {token.partition("=")[0] for token in tokens if token.startswith("-")}
    if not names & GH_PROJECT_FIELD_FLAGS:
        return False

    return names <= (GH_PROJECT_FIELD_FLAGS | GH_PROJECT_TARGETING_FLAGS)


def gh_is_carved_out(command, verb, tokens):
    """Report whether a writing invocation is one the user has decided not to be asked about.

    Every carve-out is a step ~/.claude/CLAUDE.md mandates at the start of issue work, so gating
    them would only train the user to click through prompts. See `require-gh-approval.py`.

    :param command: resolved top-level gh command
    :param verb: resolved verb
    :param tokens: gh arguments, excluding `gh`
    :return: True when the invocation writes but needs no approval
    """
    if (command, verb) in GH_ALLOWED_PAIRS:
        return True

    if (command, verb) in GH_PROJECT_FIELD_PAIRS:
        return only_edits_board_fields(tokens)

    return (command, verb) in GH_ASSIGNABLE_PAIRS and only_reassigns_to_self(tokens)


def gh_shows_help(tokens):
    """Report whether an invocation only asks gh to print usage.

    :param tokens: gh arguments, excluding `gh`
    :return: True when the first flag-like token is `--help`
    """
    for token in tokens:
        if token.startswith("-"):
            return token.partition("=")[0] == GH_HELP_FLAG

    return False


def gh_writes_to_github(tokens):
    """Report whether a gh invocation would change anything the user should approve first.

    :param tokens: gh arguments, excluding `gh`
    :return: True when the invocation writes and is not carved out
    """
    if not tokens or gh_shows_help(tokens):
        return False

    command, verb = gh_subcommand(tokens)
    if not command:
        return True

    if command == "api":
        return gh_api_writes(tokens)

    if gh_is_carved_out(command, verb, tokens) or command in GH_READ_ONLY_COMMANDS:
        return False

    return verb not in GH_READ_ONLY_VERBS


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
            timeout=GIT_TIMEOUT_SECONDS,
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


def command_directory(cmd, cwd):
    """Resolve the directory a command's git or gh invocation would act on.

    A command that changes directory first, or names a repository with `git -C`, acts on THAT
    repository rather than on the session's. Summarising the session's instead describes a tree
    the user is not being asked about, which is the one thing an approval prompt must never do.

    Only the forms a command can be read from are honoured. A destination behind a shell variable
    or a subshell is not resolvable here, so it falls back to the session directory: the summary
    is then wrong in the safe direction, naming a tree with nothing pending rather than a
    different tree's changes.

    :param cmd: full shell command, heredoc bodies already stripped
    :param cwd: the session's working directory
    :return: Path to the directory the command acts in
    """
    base = Path(cwd).expanduser() if cwd else Path(".")

    match = GIT_C_TARGET.search(cmd) or CD_TARGET.search(cmd)
    if not match:
        return base

    target = Path(match.group(1).strip("'\"")).expanduser()
    return target if target.is_absolute() else base / target
