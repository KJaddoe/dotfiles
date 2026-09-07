#!/usr/bin/env python3
"""Tests for the require-outgoing-approval PreToolUse hook.

Run: python3 claude/hooks/tests/test_require_outgoing_approval.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

Two halves carry this file. Nothing may leave the machine unapproved, and ordinary work must not
be walled off: in `auto` mode a false positive is a DENY, not a prompt, so a sloppy pattern costs
a dead end rather than a click. TestReadsPassThrough is where downloads and local work are held,
and it is as load-bearing as the gating half.
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "require-outgoing-approval.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("require_outgoing_approval", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

# Measured: a hook's "ask" renders a dialog in all four of these. See ADR 0005.
PROMPTING_MODES = ["default", "plan", "auto", "acceptEdits"]
NON_PROMPTING_MODES = ["dontAsk", "bypassPermissions"]
ALL_MODES = PROMPTING_MODES + NON_PROMPTING_MODES


def run_hook(command, mode="default", tool="Bash"):
    """Invoke the hook with a payload and return its parsed decision.

    :param command: the shell command the model would run
    :param mode: permission mode reported by the session
    :param tool: tool name to report
    :return: the hookSpecificOutput dict, or None when the hook stayed silent
    """
    payload = json.dumps(
        {
            "tool_name": tool,
            "tool_input": {"command": command},
            "permission_mode": mode,
            "cwd": str(Path.cwd()),
        }
    )
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"]


def gated(command):
    """Report whether a command would be put to the user.

    :param command: the shell command the model would run
    :return: True when the hook returns a decision
    """
    return run_hook(command) is not None


class TestFileTransferIsGated(unittest.TestCase):
    """Copying files to a machine that is not this one publishes them."""

    def test_scp_to_a_host(self):
        """The plain upload form is gated."""
        self.assertTrue(gated("scp report.pdf user@server:/srv/"))

    def test_scp_with_flags_carrying_values(self):
        """A port flag and its value must not hide the destination."""
        self.assertTrue(gated("scp -P 2222 -r dist user@server:/srv/"))

    def test_rsync_to_a_host(self):
        """rsync's host:path destination is read the same way."""
        self.assertTrue(gated("rsync -av dist/ deploy@host:/var/www/"))

    def test_rsync_with_trailing_flags(self):
        """A flag after the positionals does not move the destination out of view."""
        self.assertTrue(gated("rsync -av dist/ deploy@host:/var/www/ --delete"))

    def test_rsync_with_a_long_flag_value_last(self):
        """A long flag's value sitting last must not be mistaken for the destination."""
        self.assertTrue(gated("rsync -av dist/ host:/var/www --log-file /tmp/rsync.log"))

    def test_rsync_url_form(self):
        """The rsync:// spelling names a remote as plainly as host:path does."""
        self.assertTrue(gated("rsync -av dist/ rsync://host/module"))

    def test_rclone_to_a_remote(self):
        """rclone's remote:path is the same shape as scp's."""
        self.assertTrue(gated("rclone copy ./notes remote:notes"))

    def test_sftp(self):
        """An sftp session can upload, and its direction is not on the command line."""
        self.assertTrue(gated("sftp user@server"))

    def test_unreadable_destination(self):
        """A destination behind a shell variable cannot be checked, so it is gated."""
        self.assertTrue(gated("scp report.pdf $DEPLOY_TARGET"))


class TestHttpWritesAreGated(unittest.TestCase):
    """A request carrying a body to somebody else's host publishes what it carries."""

    def test_explicit_method(self):
        """A non-GET method is a write."""
        self.assertTrue(gated("curl -X POST https://api.example.com/v1/things"))

    def test_clustered_method_flag(self):
        """-XPOST is the same flag written tight."""
        self.assertTrue(gated("curl -XPOST https://api.example.com/x"))

    def test_method_inside_a_flag_cluster(self):
        """A method flag bundled with others is still found."""
        self.assertTrue(gated("curl -sX PUT https://api.example.com/x"))

    def test_body_without_a_method(self):
        """-d implies a POST with no -X anywhere in the command."""
        self.assertTrue(gated("curl -d '{}' https://hooks.example.com/services/xxx"))

    def test_form_upload(self):
        """A multipart form sends a file."""
        self.assertTrue(gated("curl -F file=@dump.sql https://uploads.example.com/"))

    def test_upload_file(self):
        """-T uploads whatever it names."""
        self.assertTrue(gated("curl -T dist.tar.gz https://uploads.example.com/"))

    def test_wget_post(self):
        """wget's own post flags are read."""
        self.assertTrue(gated("wget --post-data 'a=1' https://example.com/x"))

    def test_unreadable_url(self):
        """A URL behind a shell variable cannot be checked against loopback, so it is gated."""
        self.assertTrue(gated('curl -X POST "$WEBHOOK_URL" -d "{}"'))

    def test_scheme_less_remote_url(self):
        """A URL with no scheme still names a host that is not this one."""
        self.assertTrue(gated("curl -X POST api.example.com/things -d '{}'"))

    def test_private_lan_address(self):
        """The carve-out is loopback only: a LAN box is somebody else's machine."""
        self.assertTrue(gated("curl -X POST http://192.168.1.50:8080/api -d x"))

    def test_a_loopback_url_alongside_a_remote_one(self):
        """One remote host among the arguments is enough to gate."""
        self.assertTrue(
            gated('curl -X POST http://localhost:3000/x -H "Origin: https://example.com"')
        )


class TestPackagePublishIsGated(unittest.TestCase):
    """A registry push is public the moment it lands and cannot be taken back."""

    def test_npm_family(self):
        """Every npm-compatible client publishes to the same registry."""
        for command in ("npm publish", "yarn publish", "pnpm publish", "bun publish"):
            with self.subTest(command=command):
                self.assertTrue(gated(command))

    def test_npm_with_flags(self):
        """Flags do not hide the verb."""
        self.assertTrue(gated("npm publish --access public"))

    def test_python_and_rust_and_ruby(self):
        """The other language registries are gated by their own verbs."""
        for command in ("twine upload dist/*", "cargo publish", "gem push pkg.gem"):
            with self.subTest(command=command):
                self.assertTrue(gated(command))

    def test_nuget(self):
        """Both nuget spellings are gated."""
        self.assertTrue(gated("dotnet nuget push pkg.nupkg -s https://feed"))
        self.assertTrue(gated("nuget push pkg.nupkg"))

    def test_container_and_chart_registries(self):
        """An image or a chart leaving the machine is a publication too."""
        for command in (
            "docker push registry.example.com/app:1.0",
            "docker image push registry.example.com/app:1.0",
            "helm push chart.tgz oci://registry/charts",
        ):
            with self.subTest(command=command):
                self.assertTrue(gated(command))


class TestCloudUploadIsGated(unittest.TestCase):
    """An object in a bucket is reachable by everyone the bucket is reachable by."""

    def test_aws_s3(self):
        """cp and sync toward a bucket both upload."""
        self.assertTrue(gated("aws s3 cp report.pdf s3://bucket/report.pdf"))
        self.assertTrue(gated("aws s3 sync ./dist s3://bucket --delete"))

    def test_aws_s3api_put(self):
        """put-object says its direction in the verb."""
        self.assertTrue(gated("aws s3api put-object --bucket b --key k --body f"))

    def test_google_cloud_storage(self):
        """Both the old and the current CLI are gated."""
        self.assertTrue(gated("gsutil cp report.pdf gs://bucket/"))
        self.assertTrue(gated("gcloud storage cp report.pdf gs://bucket/"))

    def test_azure_blob_upload(self):
        """The Azure client takes its target in flags, so the verb decides."""
        self.assertTrue(gated("az storage blob upload -f local.txt -c container -n name"))


class TestReadsPassThrough(unittest.TestCase):
    """The load-bearing half: fetching, inspecting and local work must never be gated.

    In `auto` mode a false positive is a deny, so anything listed here that starts matching would
    silently wall off routine work.
    """

    def test_downloads(self):
        """A transfer whose remote is the source fetches; it publishes nothing."""
        for command in (
            "scp user@server:/srv/report.pdf .",
            "scp -P 2222 host:/srv/a /tmp/",
            "rsync -av host:/var/www/ ./backup/",
            "rclone copy remote:notes ./notes",
            "aws s3 cp s3://bucket/report.pdf .",
            "gsutil cp gs://bucket/x ./x",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_local_to_local_transfers(self):
        """A copy that never names a remote sends nothing anywhere."""
        self.assertFalse(gated("rsync -av src/ dst/"))
        self.assertFalse(gated("scp /tmp/a /tmp/b"))

    def test_http_reads(self):
        """A GET is a read whether or not the method is spelled out."""
        for command in (
            "curl https://api.example.com/things",
            "curl -X GET https://api.example.com/things",
            "curl -fsSL https://example.com/install.sh -o install.sh",
            "wget https://example.com/archive.tar.gz",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_loopback_writes(self):
        """A request to this machine reaches nobody, and gating it would kill the dev loop."""
        for command in (
            "curl -X POST http://localhost:3000/api -d '{}'",
            'curl -X POST -H "Content-Type: application/json" -d "{}" http://127.0.0.1:8080/x',
            "curl -X POST -o /tmp/out.json http://localhost:5000/x -d a=1",
            "curl -X DELETE http://localhost:9200/index",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_dry_runs(self):
        """A dry run publishes nothing, matching the push gate."""
        for command in ("npm publish --dry-run", "cargo publish --dry-run", "rsync -avn src/ h:/w"):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_other_gates_territory(self):
        """git and gh are covered by their own gates and must not be double-prompted here."""
        for command in (
            "git push",
            "git push --force origin main",
            "gh pr create",
            "gh issue list",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_everyday_work(self):
        """Ordinary local commands pass untouched."""
        for command in (
            "npm install",
            "npm run build",
            "docker build -t app .",
            "grep -rn 'npm publish' docs/",
            "ls -la",
            "cat README.md",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))


class TestHeredocBodiesAreData(unittest.TestCase):
    """A script that CONTAINS a publish is not one."""

    def test_deploy_script_being_written(self):
        """Writing a deploy script mentioning scp is not running it."""
        cmd = "cat > deploy.sh <<'SH'\nscp dist/app user@server:/srv/\nSH"
        self.assertFalse(gated(cmd))

    def test_url_in_a_document(self):
        """A URL inside a document body is prose, not a request."""
        cmd = "cat > notes.md <<'MD'\ncurl -X POST https://api.example.com/x\nMD"
        self.assertFalse(gated(cmd))

    def test_command_after_a_heredoc_is_still_seen(self):
        """Stripping a body must not swallow the commands that follow it."""
        cmd = "cat > x.txt <<'EOF'\nhello\nEOF\nnpm publish"
        self.assertTrue(gated(cmd))


class TestPrintedTextIsData(unittest.TestCase):
    """A banner that NAMES an outgoing command is not one, unless a shell then runs it."""

    def test_echo_banner(self):
        """A progress line mentioning a publish is not a publish."""
        self.assertFalse(gated('echo "next step: npm publish"'))

    def test_printf_banner(self):
        """printf is treated the same as echo."""
        self.assertFalse(gated('printf "about to scp the build to prod\\n"'))

    def test_real_command_chained_after_a_banner(self):
        """Only the printing segment is dropped; the rest is still inspected."""
        self.assertTrue(gated('echo "publishing" && npm publish'))

    def test_printed_command_piped_into_a_shell(self):
        """Where the printed string is what executes, it is read as the command it becomes."""
        self.assertTrue(gated('echo "curl -X POST https://api.example.com/x -d 1" | sh'))

    def test_printed_command_with_a_format_string(self):
        """A printf format string sits between the command and its text."""
        self.assertTrue(gated('printf "%s\\n" "npm publish" | bash'))


class TestCompoundCommands(unittest.TestCase):
    """An outgoing command hidden in a chain is still found."""

    def test_after_a_safe_command(self):
        """The second half of a chain is inspected."""
        self.assertTrue(gated("npm run build && npm publish"))

    def test_hidden_by_a_newline(self):
        """A command on its own line is a command, not an argument to the previous one."""
        self.assertTrue(gated("gh issue list\ncurl -X POST https://api.example.com/x -d 1"))

    def test_behind_sudo(self):
        """A wrapper does not change what is being invoked."""
        self.assertTrue(gated("sudo scp /etc/hosts user@server:/tmp/"))


class TestModes(unittest.TestCase):
    """Mode handling matches the commit, push, gh and destructive gates."""

    def test_every_non_prompting_mode_denies(self):
        """Where a prompt cannot render, the command is denied."""
        for mode in NON_PROMPTING_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(run_hook("npm publish", mode=mode)["permissionDecision"], "deny")

    def test_prompting_modes_ask(self):
        """default, plan, auto and acceptEdits all raise the prompt."""
        for mode in PROMPTING_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(run_hook("npm publish", mode=mode)["permissionDecision"], "ask")

    def test_never_allows(self):
        """No mode produces an allow decision."""
        decisions = [run_hook("npm publish", mode=m)["permissionDecision"] for m in ALL_MODES]
        self.assertNotIn("allow", decisions)

    def test_non_bash_tool(self):
        """Non-Bash tools are ignored."""
        self.assertIsNone(run_hook("npm publish", tool="Read"))


class TestSummary(unittest.TestCase):
    """The prompt must say what would leave, and by what command."""

    def test_action_is_named(self):
        """The detected action reaches the user in words."""
        reason = run_hook("npm publish")["permissionDecisionReason"]
        self.assertIn("publish a package to the npm registry", reason)

    def test_full_command_is_shown(self):
        """The destination is visible, not just the verb."""
        reason = run_hook("scp secrets.env user@prod:/srv/")["permissionDecisionReason"]
        self.assertIn("user@prod:/srv/", reason)

    def test_every_matching_action_is_listed(self):
        """A chain that sends two different things says so."""
        reason = run_hook("npm publish && scp dist.tgz host:/srv/")["permissionDecisionReason"]
        self.assertIn("publish a package to the npm registry", reason)
        self.assertIn("copy files to a remote host", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
