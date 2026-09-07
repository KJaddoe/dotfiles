#!/usr/bin/env python3
"""PreToolUse(Bash) gate: sending data off this machine needs explicit approval.

Enforces the binding rule in ~/.claude/CLAUDE.md ("Working Preferences" -> Acting as the user):
a PUBLIC, identity-attributed action is drafted and signed off before it happens. The push and
`gh` gates cover the git-shaped half of that rule; everything else that leaves the machine had no
gate at all. A file copied to a server, a POST to somebody's API, a package pushed to a registry,
an object uploaded to a bucket: all of them flowed. In `default` mode the permission prompt was
doing that job silently, so moving to `auto` turned those prompts into silence.

Like `require-destructive-approval` this is a DENYLIST, and a safety net rather than a boundary:
there is no enumerable set of commands that cannot reach the network. It errs toward gating,
because a false positive costs one approval and a false negative costs a publication that cannot
be recalled.

Classification is token-based (`command_segments`) rather than regex, because DIRECTION decides
the answer for half of these commands and direction cannot be read without positional arguments.
`scp host:file .` and `aws s3 cp s3://bucket/x .` are reads, and gating a download would be
friction with no protection. A transfer counts as a download only when the remote is the FIRST
positional and nothing after it is remote; every other shape gates, an unreadable argument
included. A long flag's separate value reads as a positional, which pushes toward gating rather
than away from it.

`curl` and `wget` are the noisy ones, so a request is judged by the hosts it NAMES: a write to
loopback reaches nobody and is not gated, every other host is, and a request whose URL cannot be
read (behind a shell variable, or with no host to find) fails closed. The carve-out is loopback
only, on purpose: a private LAN address is still a machine colleagues can see.

`--dry-run` is not gated where a tool offers one, matching the push gate: a dry run publishes
nothing.

Heredoc bodies and printed text are stripped before matching, so a script that CONTAINS a publish
is not one and a progress line naming an upload is not one. A command that pipes into a shell
keeps its printed text, because there the string is what executes.

Mode handling matches the commit, push, gh and destructive gates. See `approval_decision` in
`_hookutil`: prompt where a prompt renders, deny where it cannot, never allow.

Deliberately unconfigurable, with no env switch. An off-switch is the failure it exists to prevent.
"""

import re
import sys

from _hookutil import (
    approval_decision,
    clip_summary,
    command_segments,
    emit_decision,
    flag_values,
    read_bash_payload,
    strip_heredocs,
    strip_printed_text,
)

# Publishing verbs: the command itself says data is leaving, so no direction test applies.
PUBLISH_COMMANDS = {
    ("npm", "publish"): "publish a package to the npm registry",
    ("yarn", "publish"): "publish a package to the npm registry",
    ("pnpm", "publish"): "publish a package to the npm registry",
    ("bun", "publish"): "publish a package to the npm registry",
    ("twine", "upload"): "upload a package to a Python index",
    ("cargo", "publish"): "publish a crate to a registry",
    ("gem", "push"): "publish a gem to a registry",
    ("dotnet", "nuget", "push"): "push a package to a NuGet feed",
    ("nuget", "push"): "push a package to a NuGet feed",
    ("docker", "push"): "push an image to a registry",
    ("docker", "image", "push"): "push an image to a registry",
    ("podman", "push"): "push an image to a registry",
    ("helm", "push"): "push a chart to a registry",
    ("aws", "s3api", "put-object"): "upload an object to S3",
    ("az", "storage", "blob", "upload"): "upload a blob to Azure Storage",
    ("az", "storage", "blob", "upload-batch"): "upload blobs to Azure Storage",
}

# Transfers that read in one direction and write in the other, so the positionals decide.
DIRECTED_TRANSFERS = {
    ("scp",): "copy files to a remote host (scp)",
    ("rsync",): "sync files to a remote host (rsync)",
    ("rclone", "copy"): "upload to a cloud remote (rclone)",
    ("rclone", "copyto"): "upload to a cloud remote (rclone)",
    ("rclone", "sync"): "upload to a cloud remote (rclone)",
    ("rclone", "move"): "upload to a cloud remote (rclone)",
    ("rclone", "moveto"): "upload to a cloud remote (rclone)",
    ("aws", "s3", "cp"): "upload to S3 (aws s3)",
    ("aws", "s3", "sync"): "upload to S3 (aws s3)",
    ("aws", "s3", "mv"): "upload to S3 (aws s3)",
    ("gsutil", "cp"): "upload to Cloud Storage (gsutil)",
    ("gsutil", "rsync"): "upload to Cloud Storage (gsutil)",
    ("gsutil", "mv"): "upload to Cloud Storage (gsutil)",
    ("gcloud", "storage", "cp"): "upload to Cloud Storage (gcloud)",
    ("gcloud", "storage", "rsync"): "upload to Cloud Storage (gcloud)",
}

SFTP_LABEL = "open a file-transfer session with a remote host (sftp)"

# Only the short flags that take a value, and only for the tools whose positionals are read
# above. A long flag's value is left looking positional, which gates rather than slips through.
SHORT_VALUE_FLAGS = {
    "scp": "PiocFJlSo",
    "sftp": "PiobFJlSo",
    "rsync": "efMTB",
}

HTTP_COMMANDS = ("curl", "wget")

METHOD_FLAGS = {"-X", "--request", "--method"}

BODY_FLAGS = {
    "-d",
    "--data",
    "--data-raw",
    "--data-binary",
    "--data-ascii",
    "--data-urlencode",
    "-F",
    "--form",
    "--form-string",
    "-T",
    "--upload-file",
    "--json",
    "--post-data",
    "--post-file",
    "--body-data",
    "--body-file",
}

# Clustered short flags (`-sd`, `-fT`) carry the same meaning as their bare forms. Read for curl
# only: wget's `-T` is a timeout, not an upload.
CURL_BODY_LETTERS = "dFT"

READ_METHODS = {"GET", "HEAD", "OPTIONS"}

# A URL written with a scheme, and one written without. The scheme-less form must carry a port or
# a path, so an output filename (`-o out.json`) is not mistaken for a host.
SCHEME_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://(?:[^@/\s]*@)?(\[[^\]]+\]|[^/:\s]+)")
SCHEMELESS_URL = re.compile(r"^(\[[^\]]+\]|[A-Za-z0-9][A-Za-z0-9_.-]*)(?::\d+/?|/)")

LOOPBACK_HOST = re.compile(r"^(localhost|127(\.\d{1,3}){3}|0\.0\.0\.0|\[?::1\]?)$", re.IGNORECASE)

REMOTE_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
LOCAL_SCHEME = re.compile(r"^file://", re.IGNORECASE)
HOST_SPEC = re.compile(r"^[A-Za-z0-9_.@-]+:")

# A shell expansion cannot be resolved from the command text, so the target it names is unknown.
UNREADABLE = re.compile(r"[$`]")

DRY_RUN_FLAGS = {"--dry-run", "--dryrun"}

PRINTING_COMMANDS = ("echo", "printf")


def matched_prefix(tokens, table):
    """Find the table key whose words open this command.

    Flags are skipped rather than counted, so `aws --profile x s3 cp` still reads as `aws s3 cp`.
    Longer keys are tried first, so `docker image push` is not shadowed by a shorter neighbour.

    :param tokens: one command's tokens, starting at its command word
    :param table: mapping of leading-word tuples to labels
    :return: the matching key, or None
    """
    words = [token for token in tokens if not token.startswith("-")]
    for key in sorted(table, key=len, reverse=True):
        if tuple(words[: len(key)]) == key:
            return key
    return None


def positional_arguments(tokens):
    """List the command's positional arguments in order.

    Only the short flags in SHORT_VALUE_FLAGS consume a value. Anything else that takes a separate
    value leaves it looking positional, which can only make a transfer look less like a download.

    :param tokens: one command's tokens, starting at its command word
    :return: the positional tokens, command word included
    """
    letters = SHORT_VALUE_FLAGS.get(tokens[0], "")
    positionals, index = [], 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--") or not token.startswith("-") or token == "-":
            if not token.startswith("-"):
                positionals.append(token)
            index += 1
            continue

        cluster = token[1:]
        value = next((position for position, char in enumerate(cluster) if char in letters), None)
        index += 2 if value is not None and value == len(cluster) - 1 else 1
    return positionals


def is_remote(token):
    """Report whether an argument names something off this machine.

    :param token: one positional argument
    :return: True for a `scheme://` target other than `file://`, or a `host:path` spec
    """
    if REMOTE_SCHEME.match(token):
        return not LOCAL_SCHEME.match(token)
    return bool(HOST_SPEC.match(token))


def uploads_to_remote(arguments):
    """Report whether a transfer's arguments would send data rather than fetch it.

    A download names its remote source first and nothing remote after it. Every other arrangement,
    including one whose target cannot be read, is treated as an upload.

    :param arguments: the transfer's positional arguments, command and subcommand words removed
    :return: True when the transfer would publish
    """
    if any(UNREADABLE.search(argument) for argument in arguments):
        return True

    remote = [argument for argument in arguments if is_remote(argument)]
    if not remote:
        return False
    return not (len(remote) == 1 and is_remote(arguments[0]))


def requested_method(tokens):
    """Read the HTTP method the invocation asks for.

    :param tokens: one command's tokens
    :return: the method as written, "" when the flag carries no value, or None when unset
    """
    named = flag_values(tokens, METHOD_FLAGS)
    if named:
        return named[0]

    for index, token in enumerate(tokens):
        if not token.startswith("--") and re.match(r"^-[A-Za-z]*X", token):
            inline = token.split("X", 1)[1]
            return inline or (tokens[index + 1] if index + 1 < len(tokens) else "")
    return None


def sends_body(tokens):
    """Report whether the invocation carries a request body or an upload.

    :param tokens: one command's tokens, starting at its command word
    :return: True when a body or upload flag is present
    """
    for token in tokens[1:]:
        if token.partition("=")[0] in BODY_FLAGS:
            return True
        if tokens[0] == "curl" and not token.startswith("--") and token.startswith("-"):
            if any(char in CURL_BODY_LETTERS for char in token[1:]):
                return True
    return False


def request_hosts(tokens):
    """List the hosts an invocation would contact.

    :param tokens: one command's tokens, starting at its command word
    :return: the host of every argument readable as a URL
    """
    hosts = []
    for token in tokens[1:]:
        with_scheme = SCHEME_URL.search(token)
        if with_scheme:
            hosts.append(with_scheme.group(1))
            continue

        without_scheme = SCHEMELESS_URL.match(token)
        if without_scheme:
            hosts.append(without_scheme.group(1))
    return hosts


def only_targets_loopback(tokens):
    """Report whether every host the invocation names is this machine.

    An invocation naming no readable host answers False: an unresolvable target is not a local one.

    :param tokens: one command's tokens, starting at its command word
    :return: True when at least one host is named and all of them are loopback
    """
    hosts = request_hosts(tokens)
    return bool(hosts) and all(LOOPBACK_HOST.match(host) for host in hosts)


def http_label(tokens):
    """Label a curl or wget invocation that would write to a host other than this one.

    :param tokens: one command's tokens, starting at its command word
    :return: the label, or None when the invocation reads or targets only loopback
    """
    if tokens[0] not in HTTP_COMMANDS:
        return None

    method = requested_method(tokens)
    writes = sends_body(tokens) or (method is not None and method.upper() not in READ_METHODS)
    if not writes or only_targets_loopback(tokens):
        return None

    return f"send a request with a body to a remote host ({tokens[0]})"


def publishes_nothing(tokens):
    """Report whether the invocation only says what it would do.

    :param tokens: one command's tokens, starting at its command word
    :return: True when a dry-run flag is present
    """
    if tokens[0] == "rsync" and any(
        token.startswith("-") and not token.startswith("--") and "n" in token[1:]
        for token in tokens[1:]
    ):
        return True
    return any(token.partition("=")[0] in DRY_RUN_FLAGS for token in tokens[1:])


def segment_label(tokens):
    """Say what a single command would send off this machine.

    :param tokens: one command's tokens, starting at its command word
    :return: a label for what would leave, or None
    """
    if publishes_nothing(tokens):
        return None

    published = matched_prefix(tokens, PUBLISH_COMMANDS)
    if published:
        return PUBLISH_COMMANDS[published]

    transferred = matched_prefix(tokens, DIRECTED_TRANSFERS)
    if transferred:
        arguments = positional_arguments(tokens)[len(transferred) :]
        return DIRECTED_TRANSFERS[transferred] if uploads_to_remote(arguments) else None

    if tokens[0] == "sftp" and len(tokens) > 1:
        return SFTP_LABEL

    return http_label(tokens)


def executed_segments(cmd):
    """Split a command into the tokens of each command it runs, printed text included.

    `strip_printed_text` leaves a printing command in place when the command pipes into a shell,
    because there the printed string is what executes. A regex gate matches that string where it
    stands; a token-based one has to lex it as the command it becomes. Both the joined arguments
    and each argument alone are read, since a format string sits between `printf` and its text.

    :param cmd: full shell command, heredoc bodies and printed text already stripped
    :return: list of token lists, one per command
    """
    segments = []
    for tokens in command_segments(cmd):
        segments.append(tokens)
        if tokens[0] in PRINTING_COMMANDS:
            arguments = tokens[1:]
            for printed in [" ".join(arguments), *arguments]:
                segments.extend(command_segments(printed))
    return segments


def outgoing_matches(cmd):
    """List what a shell command would send off this machine, by label.

    :param cmd: full shell command, heredoc bodies and printed text already stripped
    :return: list of labels, in the order the commands run, without repeats
    """
    labels = []
    for tokens in executed_segments(cmd):
        label = segment_label(tokens)
        if label and label not in labels:
            labels.append(label)
    return labels


def outgoing_summary(labels, cmd):
    """Summarise what would leave the machine, for the approval prompt.

    :param labels: the outgoing actions detected
    :param cmd: full shell command, as the user would see it run
    :return: human-readable summary
    """
    actions = "\n".join(f"  - {label}" for label in labels)
    return clip_summary(
        f"This command would send data off this machine:\n{actions}\n\n"
        f"Full:   {cmd.strip()}\n\n"
        "Check the destination and what is being sent before approving. Anything that leaves "
        "carries your name, and it cannot be recalled once it has landed."
    )


def main():
    """Turn an outgoing invocation into an approval decision the user controls."""
    data, cmd = read_bash_payload()
    if data is None:
        sys.exit(0)

    labels = outgoing_matches(strip_printed_text(strip_heredocs(cmd)))
    if not labels:
        sys.exit(0)

    mode = data.get("permission_mode") or "default"
    emit_decision(*approval_decision(mode, "outgoing action", outgoing_summary(labels, cmd)))
    sys.exit(0)


if __name__ == "__main__":
    main()
