#!/usr/bin/env python3
"""Tests for the block-artifact-publish PreToolUse hook.

Run: python3 claude/hooks/tests/test_block_artifact_publish.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "block-artifact-publish.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("block_artifact_publish", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

BLOCK = 2
ALLOW = 0


def run_payload(payload):
    """Invoke the hook with a raw stdin string and return its exit code.

    :param payload: the exact text fed to the hook on stdin
    :return: hook exit code (2 blocks, 0 allows)
    """
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    return result.returncode


def run_hook(tool_input, tool="Artifact"):
    """Invoke the hook with an Artifact tool payload and return its exit code.

    :param tool_input: the tool_input dict the model would send
    :param tool: tool name to report
    :return: hook exit code (2 blocks, 0 allows)
    """
    return run_payload(json.dumps({"tool_name": tool, "tool_input": tool_input}))


class TestPublishingIsBlocked(unittest.TestCase):
    """Anything that would put local content on claude.ai must be refused."""

    def test_explicit_publish(self):
        """A named publish action is blocked."""
        self.assertEqual(run_hook({"action": "publish", "file_path": "/tmp/p.html"}), BLOCK)

    def test_omitted_action_is_a_publish(self):
        """The common call shape omits `action` entirely and still publishes."""
        self.assertEqual(run_hook({"file_path": "/tmp/p.html", "favicon": "\U0001f5c4"}), BLOCK)

    def test_null_action_is_a_publish(self):
        """An explicit null action falls back to publish rather than sneaking through."""
        self.assertEqual(run_hook({"action": None, "file_path": "/tmp/p.html"}), BLOCK)

    def test_empty_action_is_a_publish(self):
        """A blank action string falls back to publish."""
        self.assertEqual(run_hook({"action": "", "file_path": "/tmp/p.html"}), BLOCK)

    def test_whitespace_padded_action_is_normalised(self):
        """Surrounding whitespace cannot disguise a publish."""
        self.assertEqual(run_hook({"action": "  publish  "}), BLOCK)

    def test_republish_to_existing_url(self):
        """Updating an existing hosted page is still publishing."""
        self.assertEqual(
            run_hook({"action": "publish", "url": "https://claude.ai/code/artifact/abc"}),
            BLOCK,
        )

    def test_upload_asset_sends_a_local_file(self):
        """Pushing a local file into a hosted artifact is blocked."""
        self.assertEqual(
            run_hook({"action": "upload_asset", "url": "https://x", "file_path": "/tmp/a.png"}),
            BLOCK,
        )

    def test_missing_tool_input_fails_closed(self):
        """A payload with no tool_input reads as a publish and is blocked, not waved through."""
        self.assertEqual(run_payload(json.dumps({"tool_name": "Artifact"})), BLOCK)


class TestUnknownActionsFailClosed(unittest.TestCase):
    """An action this guard does not recognise must not sail through."""

    def test_unrecognised_action(self):
        """A future or misspelled action is blocked rather than allowed."""
        self.assertEqual(run_hook({"action": "share_publicly"}), BLOCK)

    def test_case_variant_is_not_an_allowlist_match(self):
        """The allowlist is exact, so a case variant does not slip past it."""
        self.assertEqual(run_hook({"action": "READ"}), BLOCK)


class TestReadingIsAllowed(unittest.TestCase):
    """Actions that send no local content stay available."""

    def test_read(self):
        """Reading an artifact the user was shared is allowed."""
        self.assertEqual(run_hook({"action": "read", "url": "https://x"}), ALLOW)

    def test_list(self):
        """Listing the user's artifacts is allowed."""
        self.assertEqual(run_hook({"action": "list", "limit": 10}), ALLOW)

    def test_comments(self):
        """Reading comment threads is allowed."""
        self.assertEqual(run_hook({"action": "comments", "url": "https://x"}), ALLOW)

    def test_watch_and_unwatch(self):
        """Managing a live-update subscription is allowed."""
        self.assertEqual(run_hook({"action": "watch", "url": "https://x"}), ALLOW)
        self.assertEqual(run_hook({"action": "unwatch", "url": "https://x"}), ALLOW)

    def test_status(self):
        """Checking watch status is allowed."""
        self.assertEqual(run_hook({"action": "status"}), ALLOW)

    def test_asset_reads(self):
        """Listing and downloading assets pulls content in, not out."""
        self.assertEqual(run_hook({"action": "list_assets", "url": "https://x"}), ALLOW)
        self.assertEqual(
            run_hook({"action": "read_asset", "url": "https://x", "asset_id": "a" * 32}),
            ALLOW,
        )

    def test_other_tools_are_untouched(self):
        """A non-Artifact tool call is ignored."""
        self.assertEqual(run_hook({"file_path": "/tmp/p.html"}, tool="Write"), ALLOW)
        self.assertEqual(run_hook({"command": "ls"}, tool="Bash"), ALLOW)


class TestMalformedInput(unittest.TestCase):
    """The hook must never take a tool call down on input it cannot parse."""

    def test_invalid_json_allows(self):
        """Unparseable stdin allows rather than blocks."""
        self.assertEqual(run_payload("not json"), ALLOW)

    def test_empty_stdin_allows(self):
        """Empty stdin allows rather than blocks."""
        self.assertEqual(run_payload(""), ALLOW)


class TestMessage(unittest.TestCase):
    """A blocked call has to tell the model what to do instead."""

    def test_reason_names_the_local_route(self):
        """The refusal points at writing a local file and at asking where."""
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            input=json.dumps({"tool_name": "Artifact", "tool_input": {"action": "publish"}}),
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(result.returncode, BLOCK)
        self.assertIn("local .html file", result.stderr)
        self.assertIn("specs/", result.stderr)
        self.assertIn("ask the user where", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
