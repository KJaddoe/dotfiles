-- Shorten function name
local keymap = vim.keymap.set

--- Normal-mode leader map carrying a which-key description.
---@param lhs string Keymap
---@param rhs string|function Action
---@param desc string which-key description
local function nmap(lhs, rhs, desc)
  keymap("n", lhs, rhs, { noremap = true, silent = true, desc = desc })
end

--- Visual-mode leader map carrying a which-key description.
---@param lhs string Keymap
---@param rhs string|function Action
---@param desc string which-key description
local function vmap(lhs, rhs, desc)
  keymap("v", lhs, rhs, { noremap = true, silent = true, desc = desc })
end

--Remap space as leader key
keymap("", "<Space>", "<Nop>", {
  noremap = true,
  silent = true,
  desc = "Leader",
})
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Quick command mode
keymap("n", ";", ":", {
  noremap = true,
  nowait = true,
  silent = false,
  desc = "Command mode",
})

-- Normal --
-- create and edit new buffer
nmap("<leader>n", ":enew<CR>", "New buffer")

-- quickfix. The list itself is browsed with <leader>fq (telescope).
nmap("<leader>co", "<cmd>copen<CR>", "Open quickfix")
nmap("<leader>cc", "<cmd>cclose<CR>", "Close quickfix")
nmap("[q", ":cprevious<CR>zz", "Previous quickfix item")
nmap("]q", ":cnext<CR>zz", "Next quickfix item")

-- Resize with arrows
nmap("<A-Up>", ":resize +2<CR>", "Grow window")
nmap("<A-Down>", ":resize -2<CR>", "Shrink window")
nmap("<A-Left>", ":vertical resize -2<CR>", "Narrow window")
nmap("<A-Right>", ":vertical resize +2<CR>", "Widen window")

-- buffer killing
nmap("<leader>q", "<cmd>bp|bd #<CR>", "Delete current buffer")
nmap("<leader>bad", ":%bd!<cr>:intro<cr>", "Delete all buffers")
nmap("<leader>bsd", function()
  local cursor = vim.api.nvim_win_get_cursor(0)
  local current = vim.fn.expand("%:p")
  vim.cmd("%bd")
  vim.cmd("e " .. current)
  vim.api.nvim_win_set_cursor(0, cursor)
  vim.cmd("zz")
end, "Delete surrounding buffers")
-- quickly move through buffers
for i = 1, 9 do
  nmap(
    "<leader>" .. i,
    ':lua require"bufferline".go_to_buffer(' .. i .. ")<CR>",
    "Go to buffer " .. i
  )
  keymap(
    "t",
    "<leader>" .. i,
    '<C-\\><C-n>:lua require"bufferline".go_to_buffer(' .. i .. ")<CR>",
    { noremap = true, silent = true, desc = "Go to buffer " .. i }
  )
end

-- save and quit
nmap("<leader>w", ":write<CR>", "Write file")

-- paste over without replacing default register
nmap("<leader>p", '"_dP', "Paste (keep register)")

-- keep more or less in the same place when going up/down
nmap("<C-u>", "<C-u>zz", "Half page up (centred)")
nmap("<C-d>", "<C-d>zz", "Half page down (centred)")
nmap("<C-o>", "<C-o>zz", "Jump back (centred)")
nmap("<C-i>", "<C-i>zz", "Jump forward (centred)")

-- move record macro to Q instead of q, which also keeps Ex mode out of reach
nmap("Q", "q", "Record macro")
nmap("q", "<Nop>", "Disabled (macros are on Q)")

-- Insert empty blank line above/bellow
nmap("]<Space>", "m`o<Esc>``", "Blank line below")
nmap("[<Space>", "m`O<Esc>``", "Blank line above")

-- system clipboard integration
nmap("<leader>y", '"+y', "Yank to system clipboard")
nmap("<leader>Y", '"+Y', "Yank line to system clipboard")

-- copy the current file path
nmap("<leader>py", ':let @" = expand("%:p")<CR>', "Copy file path")

-- delete to blackhole
nmap("<leader>d", '"_d', "Delete to blackhole")
nmap("<leader>D", '"_D', "Delete to EOL (blackhole)")

-- Insert --
-- in insert mode, adds new undo points after , . ! and ?.
for _, char in ipairs({ "-", "_", ",", ".", "!", "?" }) do
  keymap("i", char, char .. "<c-g>u", {
    noremap = true,
    silent = true,
    desc = "Insert " .. char .. " and start a new undo point",
  })
end

-- Visual --
-- Stay in indent mode
vmap("<", "<gv", "Outdent, keep selection")
vmap(">", ">gv", "Indent, keep selection")

-- Move text up and down
vmap("<A-j>", ":m .+1<CR>==", "Move line down")
vmap("<A-k>", ":m .-2<CR>==", "Move line up")

-- If I visually select words and paste from clipboard, don't replace my
-- clipboard with the selected word, instead keep my old word in the
-- clipboard
vmap("p", '"_dP', "Paste over (keep register)")

-- system clipboard integration
vmap("<leader>y", '"+y', "Yank to system clipboard")
vmap("<leader>Y", '"+Y', "Yank to system clipboard")

-- delete to blackhole
vmap("<leader>d", '"_d', "Delete to blackhole")
vmap("<leader>D", '"_D', "Delete to blackhole")

-- Visual Block --
-- Move text up and down
for _, lhs in ipairs({ "J", "<A-j>" }) do
  keymap("x", lhs, ":move '>+1<CR>gv-gv", {
    noremap = true,
    silent = true,
    desc = "Move selection down",
  })
end
for _, lhs in ipairs({ "K", "<A-k>" }) do
  keymap("x", lhs, ":move '<-2<CR>gv-gv", {
    noremap = true,
    silent = true,
    desc = "Move selection up",
  })
end

-- Oil file explorer
nmap("-", "<CMD>Oil --float<CR>", "File explorer (oil)")
