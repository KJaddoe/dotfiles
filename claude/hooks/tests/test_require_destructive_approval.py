#!/usr/bin/env python3
"""Tests for the require-destructive-approval PreToolUse hook.

Run: python3 claude/hooks/tests/test_require_destructive_approval.py
Uses stdlib unittest only, no third-party dependencies, identical on macOS and Linux.

The false-positive class matters more here than in the other gates. This hook fires on ordinary
shell text rather than on one named subcommand, and in `auto` mode a false positive is a DENY, so
a sloppy pattern does not cost a prompt, it costs a dead end. TestSafeCommandsPassThrough is
therefore the load-bearing half of this file, not the courtesy half.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "require-destructive-approval.py"

# Loading by file path does not put the hooks directory on sys.path, so the hook's
# own `from _hookutil import ...` would fail without this.
sys.path.insert(0, str(HOOK_PATH.parent))

spec = importlib.util.spec_from_file_location("require_destructive_approval", HOOK_PATH)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

# Measured: a hook's "ask" renders a dialog in all four of these. See ADR 0005.
PROMPTING_MODES = ["default", "plan", "auto", "acceptEdits"]
NON_PROMPTING_MODES = ["dontAsk", "bypassPermissions"]
ALL_MODES = PROMPTING_MODES + NON_PROMPTING_MODES


def run_hook(command, mode="default", tool="Bash", cwd=None):
    """Invoke the hook with a payload and return its parsed decision.

    :param command: the shell command the model would run
    :param mode: permission mode reported by the session
    :param tool: tool name to report
    :param cwd: working directory to report, which relative destinations resolve against
    :return: the hookSpecificOutput dict, or None when the hook stayed silent
    """
    payload = json.dumps(
        {
            "tool_name": tool,
            "tool_input": {"command": command},
            "permission_mode": mode,
            "cwd": cwd or str(Path.cwd()),
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


def gated(command, cwd=None):
    """Report whether a command would be put to the user.

    :param command: the shell command the model would run
    :param cwd: working directory to report
    :return: True when the hook returns a decision
    """
    return run_hook(command, cwd=cwd) is not None


class TestFileDeletionIsGated(unittest.TestCase):
    """Bulk file deletion is one of the four cases the rule names."""

    def test_recursive_delete(self):
        """rm -rf is gated."""
        self.assertTrue(gated("rm -rf build/"))

    def test_forced_delete(self):
        """rm -f is gated."""
        self.assertTrue(gated("rm -f .env"))

    def test_long_form_flags(self):
        """The spelled-out flags are gated too."""
        self.assertTrue(gated("rm --recursive --force dist"))

    def test_find_delete(self):
        """find -delete removes in bulk without ever naming rm."""
        self.assertTrue(gated("find . -name '*.pyc' -delete"))

    def test_find_exec_rm(self):
        """The -exec rm spelling is gated."""
        self.assertTrue(gated(r"find . -type f -exec rm {} \;"))

    def test_overwriting_a_device(self):
        """dd writing to a target is gated."""
        self.assertTrue(gated("dd if=/dev/zero of=/dev/disk2"))

    def test_shred(self):
        """shred is unrecoverable by design."""
        self.assertTrue(gated("shred -u secret.key"))


class TestGitHistoryRewriteIsGated(unittest.TestCase):
    """A git history rewrite is named in the rule, as is discarding local work."""

    def test_reset_hard(self):
        """Discarding every uncommitted change is gated."""
        self.assertTrue(gated("git reset --hard origin/main"))

    def test_clean_force(self):
        """Deleting untracked files is gated."""
        self.assertTrue(gated("git clean -fd"))

    def test_clean_with_c_flag(self):
        """`git -C dir clean -fdx` is still seen."""
        self.assertTrue(gated("git -C /tmp clean -fdx"))

    def test_checkout_discarding_paths(self):
        """`git checkout -- .` throws away working-tree changes."""
        self.assertTrue(gated("git checkout -- ."))

    def test_checkout_from_a_ref_discarding_paths(self):
        """A ref between checkout and -- discards just as much.

        `git checkout HEAD -- file` overwrites the working copy from a commit, so the pattern
        cannot require `--` to follow `checkout` immediately.
        """
        self.assertTrue(gated("git checkout HEAD -- docs/configuration.md"))
        self.assertTrue(gated("git checkout origin/main -- src/"))

    def test_restore_worktree(self):
        """git restore without --staged discards changes."""
        self.assertTrue(gated("git restore src/"))

    def test_rebase(self):
        """A rebase rewrites history."""
        self.assertTrue(gated("git rebase main"))

    def test_filter_repo(self):
        """filter-repo rewrites every commit."""
        self.assertTrue(gated("git filter-repo --path x"))

    def test_reflog_expire(self):
        """Expiring the reflog removes the recovery path itself."""
        self.assertTrue(gated("git reflog expire --expire=now --all"))

    def test_gc_prune(self):
        """Pruning unreachable objects is gated for the same reason."""
        self.assertTrue(gated("git gc --prune=now"))

    def test_force_delete_branch(self):
        """-D discards unmerged commits; -d does not."""
        self.assertTrue(gated("git branch -D feature"))

    def test_stash_drop(self):
        """Stashed work is not in any commit."""
        self.assertTrue(gated("git stash drop"))
        self.assertTrue(gated("git stash clear"))


class TestDatabaseIsGated(unittest.TestCase):
    """DB restore/overwrite and a migration against a shared DB are both named in the rule."""

    def test_drop(self):
        """DROP is gated whatever the client."""
        self.assertTrue(gated("psql -c 'DROP TABLE users'"))

    def test_truncate(self):
        """TRUNCATE empties a table with no undo."""
        self.assertTrue(gated("mysql -e 'TRUNCATE TABLE logs'"))

    def test_delete_from(self):
        """DELETE FROM is gated without trying to parse for a WHERE clause."""
        self.assertTrue(gated("psql -c 'DELETE FROM sessions'"))

    def test_lowercase_sql(self):
        """SQL keywords are matched case-insensitively."""
        self.assertTrue(gated("psql -c 'drop database staging'"))

    def test_restore(self):
        """Restoring over a database overwrites what is there."""
        self.assertTrue(gated("pg_restore -d prod dump.sql"))

    def test_redis_flush(self):
        """FLUSHALL empties the whole store."""
        self.assertTrue(gated("redis-cli FLUSHALL"))

    def test_migrations(self):
        """The migration runners the workspace actually uses are gated."""
        for command in (
            "dotnet ef database update",
            "alembic upgrade head",
            "npx prisma migrate deploy",
            "rails db:migrate",
        ):
            with self.subTest(command=command):
                self.assertTrue(gated(command))


class TestInfrastructureIsGated(unittest.TestCase):
    """Not named in the rule, but outward-facing and hard to reverse."""

    def test_terraform(self):
        """apply and destroy both change real infrastructure."""
        self.assertTrue(gated("terraform destroy"))
        self.assertTrue(gated("terraform apply -auto-approve"))

    def test_kubectl_delete(self):
        """Deleting a cluster resource is gated."""
        self.assertTrue(gated("kubectl delete pod api-7f9"))

    def test_helm_uninstall(self):
        """Removing a release takes its resources with it."""
        self.assertTrue(gated("helm uninstall myapp"))

    def test_docker_data_loss(self):
        """Only the docker commands that destroy data are gated."""
        self.assertTrue(gated("docker volume rm data"))
        self.assertTrue(gated("docker system prune -af"))
        self.assertTrue(gated("docker compose down -v"))


class TestInPlaceRewritesAreGated(unittest.TestCase):
    """Rewriting a file in place leaves no copy of what was there a moment earlier."""

    def test_sed_in_place(self):
        """Every spelling of sed's in-place flag is gated, including the BSD empty suffix."""
        for command in (
            "sed -i 's/a/b/' config.yml",
            "sed -i '' 's/a/b/' config.yml",
            "sed -i.bak 's/a/b/' config.yml",
            "sed -E -i 's/a/b/' config.yml",
            "sed --in-place 's/a/b/' config.yml",
        ):
            with self.subTest(command=command):
                self.assertTrue(gated(command))

    def test_perl_in_place(self):
        """The perl -pi -e idiom rewrites just as silently as sed does."""
        self.assertTrue(gated("perl -pi -e 's/a/b/' config.yml"))

    def test_truncate(self):
        """Truncating discards everything past the size given."""
        self.assertTrue(gated("truncate -s 0 app.log"))
        self.assertTrue(gated("truncate --size=0 app.log"))

    def test_recursive_permission_changes(self):
        """A recursive chmod or chown can lock a whole tree out in one command."""
        for command in ("chmod -R 777 .", "chown -R me:staff /srv", "chmod --recursive 700 dir"):
            with self.subTest(command=command):
                self.assertTrue(gated(command))


class TestOverwritingAnExistingFileIsGated(unittest.TestCase):
    """A `>` or a `cp` destroys nothing when the destination is new, and everything when it is not.

    Only the filesystem separates the two, so these are the one group of cases in this suite that
    needs real files on disk. The tree is built outside every scratch root, since scratch paths
    are carved out of the check on purpose.
    """

    def setUp(self):
        """Lay down a file, and a directory already holding a file of the same name."""
        self.work = Path(tempfile.mkdtemp(dir=Path.home()))
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        (self.work / "config.yml").write_text("live\n")
        (self.work / "sub").mkdir()
        (self.work / "sub" / "config.yml").write_text("live\n")

    def gate(self, command):
        """Run a command against the temporary tree.

        :param command: the shell command the model would run
        :return: True when the hook returns a decision
        """
        return gated(command, cwd=str(self.work))

    def test_redirect_over_an_existing_file(self):
        """A `>` empties the file before the left-hand command produces a byte."""
        self.assertTrue(self.gate("./build.sh > config.yml"))

    def test_redirect_from_an_echo(self):
        """The printed-text carve-out must not carry an echo's redirect away with it."""
        self.assertTrue(self.gate('echo "" > config.yml'))

    def test_deliberate_truncation_idioms(self):
        """The forms that exist only to empty a file are gated."""
        self.assertTrue(self.gate("cat /dev/null > config.yml"))
        self.assertTrue(self.gate(": > config.yml"))

    def test_heredoc_written_over_an_existing_file(self):
        """Stripping a heredoc body leaves the redirect that decides the file's fate."""
        self.assertTrue(self.gate("cat > config.yml <<'EOF'\nnew\nEOF"))

    def test_stderr_redirect(self):
        """A stream number in front of the `>` does not stop it truncating."""
        self.assertTrue(self.gate("./build.sh 2> config.yml"))

    def test_copy_onto_an_existing_file(self):
        """cp overwrites without a word."""
        self.assertTrue(self.gate("cp template.yml config.yml"))

    def test_copy_into_a_directory_already_holding_that_name(self):
        """A destination directory is not overwritten; what the source lands on inside it is."""
        self.assertTrue(self.gate("cp config.yml sub/"))

    def test_unresolvable_destination(self):
        """A destination behind a variable cannot be checked, so it is gated."""
        self.assertTrue(self.gate("./build.sh > $OUTPUT"))
        self.assertTrue(self.gate("cp config.yml $DEST"))

    def test_new_destinations_pass(self):
        """Writing somewhere nothing lives destroys nothing."""
        for command in (
            "./build.sh > report.txt",
            "cat > notes.md <<'EOF'\nhi\nEOF",
            "cp config.yml backup.yml",
            "cp template.yml sub/",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.gate(command))

    def test_appending_passes(self):
        """`>>` adds to a file rather than replacing it."""
        self.assertFalse(self.gate("./build.sh >> config.yml"))

    def test_devices_pass(self):
        """Writing to a stream device destroys nothing."""
        self.assertFalse(self.gate("./build.sh > /dev/null"))
        self.assertFalse(self.gate("./build.sh 2>/dev/null"))

    def test_scratch_destinations_pass(self):
        """Nothing under a temporary tree is worth an approval prompt."""
        self.assertFalse(self.gate("./build.sh > /tmp/out.txt"))
        self.assertFalse(self.gate("cp config.yml /tmp/backup.yml"))

    def test_a_quoted_redirect_is_not_one(self):
        """Reading redirects from the lexer is what keeps a `>` inside an argument out of this."""
        self.assertFalse(self.gate("grep 'a > config.yml' notes.md"))
        self.assertFalse(self.gate('echo "writes > config.yml when run"'))


class TestSafeCommandsPassThrough(unittest.TestCase):
    """The load-bearing half: ordinary work must never be gated.

    In `auto` mode a false positive is a deny, not a prompt, so anything listed here that starts
    matching would silently wall off a routine command.
    """

    def test_read_only_git(self):
        """Inspecting a repository changes nothing."""
        for command in (
            "git diff --stat",
            "git log --oneline -10",
            "git status --short",
            "git show HEAD",
            "git stash list",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_ordinary_git_writes(self):
        """Committing and branching are gated by their own hooks, not this one."""
        for command in (
            "git commit -m 'fix: x'",
            "git checkout -b feature/x",
            "git checkout main",
            "git branch -d merged",
            "git add -A",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_restore_staged_is_not_a_discard(self):
        """--staged unstages; it does not touch the working tree."""
        self.assertFalse(gated("git restore --staged file.txt"))

    def test_clean_dry_run(self):
        """`git clean -n` only reports what it would remove."""
        self.assertFalse(gated("git clean -n"))

    def test_sed_and_perl_without_in_place(self):
        """A flag that merely CONTAINS an i is not the in-place flag."""
        for command in (
            "sed -n '1,5p' config.yml",
            "sed -e 's/i/x/' config.yml",
            "sed --expression='s/a/i/' config.yml",
            "perl -Mstrict -e 'print 1'",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_growing_a_file_is_not_truncating_it(self):
        """A `+` size extends the file rather than cutting it back."""
        self.assertFalse(gated("truncate -s +1M sparse.img"))

    def test_non_recursive_permission_changes(self):
        """Only the recursive forms are gated; a single file is not the disaster case."""
        for command in ("chmod 644 config.yml", "chmod +x script.sh", "chmod --reference=a b"):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_interactive_rm_is_not_bulk(self):
        """rm -i prompts per file and is not the bulk delete the rule names."""
        self.assertFalse(gated("rm -i notes.txt"))

    def test_read_only_shell(self):
        """Everyday inspection commands pass."""
        for command in (
            "ls -la",
            "cat README.md",
            "grep -rn foo .",
            "rg --files",
            "mkdir -p build",
            "find . -name '*.py'",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_tooling(self):
        """Formatters, linters and test runners pass."""
        for command in (
            "black --check claude/hooks/",
            "pylint _hookutil.py",
            "python3 tests/test_hookutil.py",
            "npm install",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))

    def test_read_only_infrastructure(self):
        """Planning and inspecting are not applying."""
        for command in (
            "terraform plan",
            "kubectl get pods",
            "kubectl delete pod x --dry-run=client",
            "docker ps",
            "docker compose up -d",
        ):
            with self.subTest(command=command):
                self.assertFalse(gated(command))


class TestHeredocBodiesAreData(unittest.TestCase):
    """Writing a script or a .sql file that CONTAINS a destructive command is not running one."""

    def test_sql_file_being_written(self):
        """A migration file mentioning DROP TABLE is data, not an invocation."""
        cmd = "cat > migration.sql <<'SQL'\nDROP TABLE legacy_users;\nSQL"
        self.assertFalse(gated(cmd))

    def test_script_body_mentioning_rm(self):
        """A script body describing a cleanup is not a cleanup."""
        cmd = "cat > clean.sh <<'SH'\nrm -rf ./build\nSH"
        self.assertFalse(gated(cmd))

    def test_command_after_heredoc_still_gated(self):
        """Stripping a body must not swallow the commands that follow it."""
        cmd = "cat > x.txt <<'EOF'\nhello\nEOF\nrm -rf build"
        self.assertTrue(gated(cmd))


class TestPrintedTextIsData(unittest.TestCase):
    """A banner that NAMES a destructive command is not one.

    Regression: the first live run of this hook denied its own verification script, whose only
    offence was an `echo` header naming the command it was about to test.
    """

    def test_echo_banner(self):
        """A progress line mentioning rm -rf is not a delete."""
        self.assertFalse(gated('echo "=== testing rm -rf handling ==="'))

    def test_printf_banner(self):
        """printf is treated the same as echo."""
        self.assertFalse(gated('printf "about to run git reset --hard\\n"'))

    def test_real_command_chained_after_a_banner(self):
        """Only the printing segment is dropped; the rest is still inspected."""
        self.assertTrue(gated('echo "cleaning up" && rm -rf build'))

    def test_banner_naming_the_command_that_follows(self):
        """The exact shape that misfired: a banner plus the real command."""
        self.assertTrue(gated('echo "=== rm -rf ===" && rm -rf /tmp/x'))

    def test_printed_command_piped_into_a_shell(self):
        """The carve-out is withheld when the printed string is what executes."""
        self.assertTrue(gated('echo "rm -rf build" | sh'))

    def test_echo_is_not_a_general_escape_hatch(self):
        """A destructive command before a banner is still caught."""
        self.assertTrue(gated('rm -rf build && echo "done"'))


class TestCompoundCommands(unittest.TestCase):
    """A destructive command hidden in a chain is still found."""

    def test_after_a_safe_command(self):
        """The second half of a chain is inspected."""
        self.assertTrue(gated("cd /tmp && rm -rf build"))

    def test_flags_do_not_leak_across_commands(self):
        """A flag belonging to the next command must not arm the previous one.

        Without the same-command bound, `git clean -n && ls -f` would read the `-f` from `ls`
        as the force flag on `clean`.
        """
        self.assertFalse(gated("git clean -n && ls -f"))


class TestModes(unittest.TestCase):
    """Mode handling matches the commit, push and gh gates."""

    def test_every_non_prompting_mode_denies(self):
        """Where a prompt cannot render, the command is denied."""
        for mode in NON_PROMPTING_MODES:
            with self.subTest(mode=mode):
                out = run_hook("rm -rf build", mode=mode)
                self.assertEqual(out["permissionDecision"], "deny")

    def test_prompting_modes_ask(self):
        """default, plan, auto and acceptEdits all raise the prompt."""
        for mode in PROMPTING_MODES:
            with self.subTest(mode=mode):
                self.assertEqual(run_hook("rm -rf build", mode=mode)["permissionDecision"], "ask")

    def test_never_allows(self):
        """No mode produces an allow decision."""
        modes = ALL_MODES
        decisions = [run_hook("rm -rf build", mode=m)["permissionDecision"] for m in modes]
        self.assertNotIn("allow", decisions)

    def test_non_bash_tool(self):
        """Non-Bash tools are ignored."""
        self.assertIsNone(run_hook("rm -rf build", tool="Read"))


class TestSummary(unittest.TestCase):
    """The prompt must say what would be destroyed, and by what command."""

    def test_action_is_named(self):
        """The detected action reaches the user in words."""
        reason = run_hook("git reset --hard")["permissionDecisionReason"]
        self.assertIn("discard every uncommitted change", reason)

    def test_full_command_is_shown(self):
        """The target is visible, not just the verb."""
        reason = run_hook("rm -rf /var/data/prod")["permissionDecisionReason"]
        self.assertIn("/var/data/prod", reason)

    def test_every_matching_action_is_listed(self):
        """A chain that destroys two different things says so."""
        reason = run_hook("git reset --hard && rm -rf build")["permissionDecisionReason"]
        self.assertIn("discard every uncommitted change", reason)
        self.assertIn("delete files recursively", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
