#!/usr/bin/env python3
"""Tests for the nvim-lint wiring in nvim/config/lua/user/plugins/init.lua.

These drive a real headless nvim against this repo's config, so unlike the hook
suites they need nvim, an installed plugin set and pylint on PATH. That is why
they are not part of script/test's early block, which deliberately depends on
nothing but python3 and git.

The regression they exist for: nvim-lint is lazy-loaded on BufReadPost, so by the
time its config registers the autocmd, that event has already fired for the buffer
you opened. lazy.nvim does replay the event for newly created augroups, but it
replays it before filetype detection, so try_lint() finds no linters for the buffer
and silently does nothing. Without the scheduled initial try_lint() the file you
open is never linted until you write it.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "nvim" / "config"

PROBE = """
local deadline = vim.uv.now() + {timeout}
local function poll()
  local n = 0
  for _, d in ipairs(vim.diagnostic.get(0)) do
    if (d.source or ""):match("pylint") then
      n = n + 1
    end
  end
  if (n > 0 and {stop_early}) or vim.uv.now() > deadline then
    io.stdout:write("RESULT=" .. n .. "\\n")
    vim.cmd("qa!")
  else
    vim.defer_fn(poll, 200)
  end
end
vim.defer_fn(poll, 200)
"""


def nvim_missing():
    """True when this environment cannot run the suite at all."""
    return not (shutil.which("nvim") and shutil.which("pylint") and CONFIG.is_dir())


@unittest.skipIf(nvim_missing(), "nvim, pylint or the repo config is unavailable")
class NvimLintCase(unittest.TestCase):
    """Base case that opens a file in headless nvim and counts diagnostics."""

    def diagnostics(self, name, content, *, timeout=15000, expect_findings=True):
        """Open a file in headless nvim and return the count of pylint diagnostics.

        Polling stops as soon as a finding appears when one is expected; when none is,
        it waits out the timeout, since absence can only be established by waiting.
        """
        work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)

        # Point XDG_CONFIG_HOME at the in-repo config so the test covers this repo
        # rather than whatever dotbot happens to have linked into ~/.config.
        xdg = work / "xdg"
        (xdg).mkdir()
        (xdg / "nvim").symlink_to(CONFIG)

        target = work / name
        target.write_text(content, encoding="utf-8")
        probe = work / "probe.lua"
        probe.write_text(
            PROBE.format(
                timeout=timeout,
                stop_early="true" if expect_findings else "false",
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            ["nvim", "--headless", str(target), "-S", str(probe)],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout / 1000 + 30,
            env={**os.environ, "XDG_CONFIG_HOME": str(xdg)},
        )
        out = result.stdout + result.stderr
        for line in out.splitlines():
            if "RESULT=" in line:
                return int(line.split("RESULT=")[1].split()[0])
        return self.fail(f"probe never reported a result:\n{out[-2000:]}")


class LintsTheBufferItLoadedWith(NvimLintCase):
    """The regression: opening a file must lint it, with no write."""

    def test_opened_file_is_linted_without_a_write(self):
        """A pylint finding surfaces from the buffer nvim was started on."""
        n = self.diagnostics("bad.py", "def f():\n    return undefined_name_here\n")
        self.assertGreater(n, 0, "the opened buffer was never linted")


class NoFalsePositives(NvimLintCase):
    """Linting must stay quiet where there is nothing to report."""

    def test_clean_python_reports_nothing(self):
        """Valid python produces no pylint diagnostics."""
        n = self.diagnostics(
            "ok.py",
            '"""Module."""\n\n\ndef f():\n    """Return one."""\n    return 1\n',
            timeout=6000,
            expect_findings=False,
        )
        self.assertEqual(n, 0)

    def test_unconfigured_filetype_is_not_linted(self):
        """nvim-lint only runs for the filetypes it is wired to."""
        n = self.diagnostics(
            "notes.txt",
            "undefined_name_here\n",
            timeout=6000,
            expect_findings=False,
        )
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
