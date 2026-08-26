#!/usr/bin/env python3
"""Tests for the LSP navigation keymaps in nvim/config/lua/lsp_keymaps.lua.

Like test_lint.py these drive a real headless nvim against this repo's config,
so they need nvim, an installed plugin set and lua-language-server on PATH.

The regressions they exist for:

- `<leader>D` was bound twice: globally to blackhole delete-to-EOL and
  buffer-locally to type definition. The buffer-local map wins, so delete-to-EOL
  silently stopped working in every LSP buffer. Type definition now lives on `gy`
  and nothing buffer-local may claim `<leader>D` again.
- Call hierarchy was bound nowhere despite the servers supporting it.
- which-key's `<auto>` trigger detection never created a `g` trigger, so the
  popup listed none of the LSP navigation maps.
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
  local maps = {{}}
  for _, mode in ipairs({{ "n", "v" }}) do
    for _, m in ipairs(vim.api.nvim_buf_get_keymap(0, mode)) do
      maps[mode .. ":" .. m.lhs] = m.desc or ""
    end
  end
  if maps["n:gd"] or vim.uv.now() > deadline then
    local pairs_out = {{}}
    for lhs, desc in pairs(maps) do
      table.insert(pairs_out, lhs .. "\\t" .. desc)
    end
    io.stdout:write("RESULT=" .. table.concat(pairs_out, "\\x1f") .. "\\n")
    vim.cmd("qa!")
  else
    vim.defer_fn(poll, 200)
  end
end
vim.defer_fn(poll, 200)
"""


def nvim_missing():
    """True when this environment cannot run the suite at all."""
    return not (shutil.which("nvim") and shutil.which("lua-language-server") and CONFIG.is_dir())


@unittest.skipIf(nvim_missing(), "nvim, lua-language-server or the config is unavailable")
class LspKeymapCase(unittest.TestCase):
    """Base case that opens a Lua file and reads back its buffer-local keymaps."""

    @classmethod
    def setUpClass(cls):
        """Attach lua_ls once and cache the resulting buffer-local keymaps."""
        cls.maps = cls._probe()

    @classmethod
    def _probe(cls, timeout=30000):
        """Open a Lua file in headless nvim and return its normal-mode keymaps."""
        work = Path(tempfile.mkdtemp())
        cls.addClassCleanup(shutil.rmtree, work, ignore_errors=True)

        # Point XDG_CONFIG_HOME at the in-repo config so the test covers this repo
        # rather than whatever dotbot happens to have linked into ~/.config.
        xdg = work / "xdg"
        xdg.mkdir()
        (xdg / "nvim").symlink_to(CONFIG)

        target = work / "probe_target.lua"
        target.write_text("local M = {}\nreturn M\n", encoding="utf-8")
        probe = work / "probe.lua"
        probe.write_text(PROBE.format(timeout=timeout), encoding="utf-8")

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
                body = line.split("RESULT=", 1)[1]
                return dict(entry.split("\t", 1) for entry in body.split("\x1f") if "\t" in entry)
        raise AssertionError(f"probe never reported a result:\n{out[-2000:]}")


class BindsNavigation(LspKeymapCase):
    """Every navigation request an attached server can answer has a keymap."""

    def test_goto_maps_are_bound(self):
        """The g-prefix navigation maps attach with their descriptions."""
        for lhs, desc in (
            ("gd", "Go to definition"),
            ("gr", "References"),
            ("gi", "Implementations"),
            ("gy", "Type definition"),
            ("gD", "Go to declaration"),
        ):
            with self.subTest(lhs=lhs):
                self.assertEqual(self.maps.get("n:" + lhs), desc)

    def test_call_hierarchy_is_bound(self):
        """Call hierarchy is reachable; it used to be bound nowhere."""
        self.assertEqual(self.maps.get("n: li"), "Incoming calls")
        self.assertEqual(self.maps.get("n: lo"), "Outgoing calls")

    def test_combined_finder_is_bound(self):
        """The combined trouble panel is reachable."""
        self.assertEqual(self.maps.get("n: lf"), "LSP finder (all)")


class SurfacesInWhichKey(LspKeymapCase):
    """The g prefix must be discoverable, not just bound."""

    def test_g_prefix_has_a_which_key_trigger(self):
        """which-key's automatic trigger detection misses `g`, so on_attach names
        it explicitly. Without that registration the popup never lists gd/gr/gi."""
        self.assertEqual(self.maps.get("n:g"), "which-key-trigger")


class ReachesRangeCodeActions(LspKeymapCase):
    """Code actions must be reachable from a selection, not just the cursor."""

    def test_code_action_is_bound_in_visual_mode(self):
        """TypeScript's extract refactors are only offered for a selected range,
        so a normal-mode-only map cannot reach them at all."""
        self.assertEqual(self.maps.get("n: ca"), "Code action")
        self.assertEqual(self.maps.get("v: ca"), "Code action")

    def test_source_actions_are_gated_on_the_server(self):
        """Source-kind maps only exist where a client advertises the kind. Lua
        has no eslint or TypeScript source actions, so none of them bind here."""
        for lhs in ("n: cf", "n: cm", "n: cu"):
            with self.subTest(lhs=lhs):
                self.assertNotIn(lhs, self.maps)


class LeavesGlobalMapsAlone(LspKeymapCase):
    """Buffer-local LSP maps must not shadow global editing maps."""

    def test_leader_d_is_not_shadowed(self):
        """`<leader>D` stays the global blackhole delete, not type definition."""
        self.assertNotIn("n: D", self.maps)


class AvoidsDeprecatedApis(unittest.TestCase):
    """Deprecated nvim APIs must not creep back into the config.

    This one needs no nvim: it reads the config files directly, so it still runs
    where the rest of the suite skips.
    """

    def lua_sources(self):
        """Yield every Lua file in the config as (path, text)."""
        for path in sorted((CONFIG / "lua").rglob("*.lua")):
            yield path, path.read_text(encoding="utf-8")

    def test_diagnostic_navigation_uses_jump(self):
        """goto_prev/goto_next are removed in nvim 0.13; jump() replaces them."""
        for path, text in self.lua_sources():
            for banned in ("vim.diagnostic.goto_prev", "vim.diagnostic.goto_next"):
                with self.subTest(path=path.name, api=banned):
                    self.assertNotIn(banned, text)

    def test_diagnostic_signs_go_through_diagnostic_config(self):
        """Defining DiagnosticSign* via sign_define is deprecated, and the names
        it derived from the icon table (Warning, Information) are not the ones
        nvim reads (Warn, Info), so those icons never applied.

        sign_define itself is fine and dap.lua uses it for breakpoints; only
        diagnostic signs are deprecated, so this bans the pairing.
        """
        for path, text in self.lua_sources():
            if "sign_define" in text:
                with self.subTest(path=path.name):
                    self.assertNotIn("DiagnosticSign", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
