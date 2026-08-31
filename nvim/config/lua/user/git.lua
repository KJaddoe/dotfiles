local gitsigns = require("gitsigns")
local builtin = require("telescope.builtin")

vim.g.fugitive_legacy_commands = 0

--- Add a normal-mode git keymap.
---@param lhs string Keymap
---@param rhs string|function Action
---@param desc string which-key description
local function map(lhs, rhs, desc)
  vim.keymap.set("n", lhs, rhs, { noremap = true, silent = true, desc = desc })
end

map("<leader>gs", vim.cmd.Git, "Open Git")
map("<leader>gms", function()
  vim.cmd.Git("sync")
end, "Git sync")

-- Hunks. nav_hunk wraps, so the keys keep working at the end of a file.
map("]h", function()
  gitsigns.nav_hunk("next")
end, "Next hunk")
map("[h", function()
  gitsigns.nav_hunk("prev")
end, "Previous hunk")
map("<leader>gp", gitsigns.preview_hunk, "Preview hunk")
map("<leader>ga", gitsigns.stage_hunk, "Stage hunk")
map("<leader>gr", gitsigns.reset_hunk, "Reset hunk")
map("<leader>gu", gitsigns.undo_stage_hunk, "Undo stage hunk")
map("<leader>gb", function()
  gitsigns.blame_line({ full = true })
end, "Blame line")

-- Browsing. Read-only views with a diff preview; the work itself happens in a
-- terminal pane.
map("<leader>gf", builtin.git_status, "Changed files")
map("<leader>gc", builtin.git_commits, "Commits (repo)")
map("<leader>gC", builtin.git_bcommits, "Commits (this file)")
map("<leader>gB", builtin.git_branches, "Branches")
