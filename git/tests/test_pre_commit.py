#!/usr/bin/env python3
"""Tests for git/template/hooks/pre-commit.

The hook ships via init.templateDir into every repo created on this machine, so a
regression here is silent and repo-wide. Each test runs a real commit in a throwaway
repo with the global and system git config neutralised, so the developer's own config
and hooks can never influence a result.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "template" / "hooks" / "pre-commit"


class HookTestCase(unittest.TestCase):
    """Base case providing a throwaway repo with the hook installed."""

    def setUp(self):
        """Create an isolated repo, install the hook, and stage nothing yet."""
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
        }
        self.env.pop("SKIP_HOOKS", None)
        self.git("init", "--template=", "-q", ".")
        self.git("config", "user.name", "test")
        self.git("config", "user.email", "test@example.com")
        hooks = self.repo / ".git" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        target = hooks / "pre-commit"
        target.write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
        target.chmod(0o755)

    def git(self, *args, env=None):
        """Run a git command in the throwaway repo and return its CompletedProcess."""
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env=env or self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def stage(self, path, content="x\n"):
        """Write a file at a repo-relative path and stage it."""
        full = self.repo / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        self.git("add", path)

    def commit(self, env=None):
        """Attempt a commit and return (exit code, stderr)."""
        result = self.git("commit", "-m", "test", env=env)
        return result.returncode, result.stderr


class ManifestNotices(HookTestCase):
    """A staged dependency manifest prompts the matching audit command."""

    def test_package_json_prompts_npm_audit(self):
        """A staged package.json names npm audit."""
        self.stage("package.json", '{"name":"x"}\n')
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("npm audit", err)

    def test_lockfile_prompts_npm_audit(self):
        """A staged package-lock.json also counts as a manifest."""
        self.stage("package-lock.json", "{}\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("npm audit", err)

    def test_requirements_prompts_pip_audit(self):
        """A staged requirements file names pip-audit."""
        self.stage("requirements.txt", "requests\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("pip-audit", err)

    def test_suffixed_requirements_prompts_pip_audit(self):
        """requirements-dev.txt is matched as well as the bare name."""
        self.stage("requirements-dev.txt", "pytest\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("pip-audit", err)

    def test_csproj_prompts_dotnet_audit(self):
        """A staged project file names the dotnet vulnerability listing."""
        self.stage("App.csproj", "<Project/>\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("--vulnerable", err)

    def test_central_package_management_prompts_dotnet_audit(self):
        """Directory.Packages.props is a manifest under central package management."""
        self.stage("Directory.Packages.props", "<Project/>\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("--vulnerable", err)

    def test_nested_manifest_is_matched(self):
        """A manifest below the repo root is matched, not just one at the top."""
        self.stage("services/api/package.json", '{"name":"api"}\n')
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("npm audit", err)


class PyprojectGuard(HookTestCase):
    """pyproject.toml counts only when it actually declares dependencies."""

    def test_config_only_pyproject_is_silent(self):
        """A tool-config-only pyproject.toml raises no notice (this repo's own case)."""
        self.stage("pyproject.toml", "[tool.black]\nline-length = 100\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertNotIn("pip-audit", err)

    def test_pep621_dependencies_prompt_pip_audit(self):
        """A pyproject.toml with a dependencies key is a real manifest."""
        self.stage("pyproject.toml", '[project]\ndependencies = ["requests"]\n')
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("pip-audit", err)

    def test_setuptools_install_requires_prompts_pip_audit(self):
        """The setuptools spelling counts too."""
        self.stage("pyproject.toml", "[options]\ninstall_requires = ['requests']\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("pip-audit", err)


class NoFalsePositives(HookTestCase):
    """Files that merely resemble a manifest must stay silent."""

    def test_unrelated_file_is_silent(self):
        """An ordinary file triggers nothing."""
        self.stage("README.md", "hello\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertNotIn("dependencies changed", err)

    def test_similarly_named_file_is_silent(self):
        """mypackage.json is not package.json — the pattern is anchored."""
        self.stage("mypackage.json", "{}\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertNotIn("npm audit", err)

    def test_deleted_manifest_is_silent(self):
        """Deleting a manifest adds no dependencies, so it raises no notice."""
        self.stage("package.json", '{"name":"x"}\n')
        self.commit()
        self.git("rm", "-q", "package.json")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertNotIn("npm audit", err)


class NoticesNeverBlock(HookTestCase):
    """Notices are advisory: they must not turn into gates."""

    def test_multiple_notices_still_exit_zero(self):
        """Several manifests at once still produce a passing commit."""
        self.stage("package.json", '{"name":"x"}\n')
        self.stage("requirements.txt", "requests\n")
        self.stage("App.csproj", "<Project/>\n")
        code, err = self.commit()
        self.assertEqual(code, 0)
        self.assertIn("npm audit", err)
        self.assertIn("pip-audit", err)
        self.assertIn("--vulnerable", err)

    def test_notice_does_not_print_the_bypass_hint(self):
        """The 'fix, or SKIP_HOOKS=1' line belongs to real failures only."""
        self.stage("package.json", '{"name":"x"}\n')
        _, err = self.commit()
        self.assertNotIn("SKIP_HOOKS=1 git commit", err)


class EnforcementStillBlocks(HookTestCase):
    """What must stay broken: real violations still fail the commit."""

    def test_trailing_whitespace_blocks(self):
        """The whitespace gate still rejects a bad diff."""
        self.stage("bad.py", "x = 1   \n")
        code, err = self.commit()
        self.assertEqual(code, 1)
        self.assertIn("trailing whitespace", err)

    def test_blocked_commit_creates_no_commit(self):
        """A rejected commit leaves no history behind."""
        self.stage("bad.py", "x = 1   \n")
        self.commit()
        self.assertNotEqual(self.git("rev-parse", "HEAD").returncode, 0)

    def test_skip_hooks_bypasses_enforcement(self):
        """SKIP_HOOKS=1 is the documented escape hatch and must keep working."""
        self.stage("bad.py", "x = 1   \n")
        code, err = self.commit(env={**self.env, "SKIP_HOOKS": "1"})
        self.assertEqual(code, 0)
        self.assertNotIn("trailing whitespace", err)

    def test_skip_hooks_also_suppresses_notices(self):
        """A bypassed hook runs nothing at all, notices included."""
        self.stage("package.json", '{"name":"x"}\n')
        _, err = self.commit(env={**self.env, "SKIP_HOOKS": "1"})
        self.assertNotIn("npm audit", err)


@unittest.skipUnless(shutil.which("shellcheck"), "shellcheck not installed")
class ShellcheckReachesExtensionlessScripts(HookTestCase):
    """Scripts named without a .sh suffix are found by shebang, not by extension."""

    BAD = '#!/bin/bash\nif [ $1 = "x" ]; then echo hi; fi\n'
    GOOD = '#!/bin/bash\necho "clean"\n'

    def test_extensionless_bash_script_blocks(self):
        """A bin/-style script with findings fails the commit."""
        self.stage("bin/tool", self.BAD)
        code, err = self.commit()
        self.assertEqual(code, 1)
        self.assertIn("shellcheck", err)

    def test_clean_extensionless_script_passes(self):
        """A script with no findings commits normally."""
        self.stage("bin/tool", self.GOOD)
        code, err = self.commit()
        self.assertEqual(code, 0, err)

    def test_suffixed_script_still_blocks(self):
        """The original .sh path keeps working."""
        self.stage("tool.sh", self.BAD)
        self.assertEqual(self.commit()[0], 1)

    def test_env_shebang_is_matched(self):
        """#!/usr/bin/env bash is as much a shell script as #!/bin/bash."""
        self.stage("bin/tool", self.BAD.replace("#!/bin/bash", "#!/usr/bin/env bash"))
        self.assertEqual(self.commit()[0], 1)


@unittest.skipUnless(shutil.which("shellcheck"), "shellcheck not installed")
class ShellcheckSkipsWhatItCannotParse(HookTestCase):
    """Widening the net must not drag in files shellcheck would choke on."""

    def test_zsh_script_is_skipped(self):
        """shellcheck cannot parse zsh, so a zsh shebang is left alone."""
        self.stage("bin/tool", '#!/bin/zsh\nif [ $1 = "x" ]; then echo hi; fi\n')
        code, err = self.commit()
        self.assertEqual(code, 0, err)

    def test_non_shell_script_is_skipped(self):
        """An extensionless file with a python shebang is not a shell script."""
        self.stage("bin/tool", "#!/usr/bin/env python3\nx = 1\n")
        self.assertEqual(self.commit()[0], 0)

    def test_extensionless_non_script_is_skipped(self):
        """A plain extensionless file has no shebang and is ignored."""
        self.stage("LICENSE", "All rights reserved.\n")
        self.assertEqual(self.commit()[0], 0)

    def test_dotted_path_is_not_treated_as_extensionless(self):
        """A file with a real extension is matched by the glob, not the shebang scan."""
        self.stage("notes.md", "# hi\n")
        self.assertEqual(self.commit()[0], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
