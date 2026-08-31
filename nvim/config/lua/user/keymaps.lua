local opts = { noremap = true, silent = true }

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
keymap("", "<Space>", "<Nop>", opts)
vim.g.mapleader = " "
vim.g.maplocalleader = " "

-- Quick command mode
keymap("n", ";", ":", { noremap = true, nowait = true, silent = false })

-- Normal --
-- create and edit new buffer
nmap("<leader>n", ":enew<CR>", "New buffer")

-- quicklists. trouble renders the quickfix list and the diagnostics it reads
-- from; required inside the callbacks so pressing the key loads it, not startup.
nmap("<leader>co", function()
  require("trouble").open({ mode = "qflist", focus = true })
end, "Open quickfix")
nmap("<leader>cc", function()
  require("trouble").close()
  vim.cmd("cclose")
end, "Close quickfix")
nmap("<leader>cd", function()
  require("trouble").open({ mode = "diagnostics", focus = true })
end, "Diagnostics list")
keymap("n", "[q", ":cprevious<CR>zz", opts)
keymap("n", "]q", ":cnext<CR>zz", opts)

-- Resize with arrows
keymap("n", "<A-Up>", ":resize +2<CR>", opts)
keymap("n", "<A-Down>", ":resize -2<CR>", opts)
keymap("n", "<A-Left>", ":vertical resize -2<CR>", opts)
keymap("n", "<A-Right>", ":vertical resize +2<CR>", opts)

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
    '<C-\\><C-n>:lua require"bufferline".go_to_buffer(' .. i .. ")<CR>"
  )
end

-- save and quit
nmap("<leader>w", ":write<CR>", "Write file")

-- paste over without replacing default register
nmap("<leader>p", '"_dP', "Paste (keep register)")

-- keep more or less in the same place when going next
keymap("n", "n", "nzzzv", opts)
keymap("n", "N", "Nzzzv", opts)

-- keep more or less in the same place when going up/down
keymap("n", "<C-u>", "<C-u>zz", opts)
keymap("n", "<C-d>", "<C-d>zz", opts)
keymap("n", "<C-o>", "<C-o>zz", opts)
keymap("n", "<C-i>", "<C-i>zz", opts)

-- move record macro to Q instead of q, which also keeps Ex mode out of reach
keymap("n", "Q", "q", opts)
keymap("n", "q", "<Nop>", opts)

-- Insert empty blank line above/bellow
keymap("n", "]<Space>", "m`o<Esc>``", opts)
keymap("n", "[<Space>", "m`O<Esc>``", opts)

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
keymap("i", "-", "-<c-g>u", opts)
keymap("i", "_", "_<c-g>u", opts)
keymap("i", ",", ",<c-g>u", opts)
keymap("i", ".", ".<c-g>u", opts)
keymap("i", "!", "!<c-g>u", opts)
keymap("i", "?", "?<c-g>u", opts)

-- alias quick jk/kj to esc
keymap("i", "jk", "<ESC>", opts)
keymap("i", "kj", "<ESC>", opts)

-- Visual --
-- Stay in indent mode
keymap("v", "<", "<gv", opts)
keymap("v", ">", ">gv", opts)

-- Move text up and down
keymap("v", "<A-j>", ":m .+1<CR>==", opts)
keymap("v", "<A-k>", ":m .-2<CR>==", opts)

-- If I visually select words and paste from clipboard, don't replace my
-- clipboard with the selected word, instead keep my old word in the
-- clipboard
keymap("v", "p", '"_dP', opts)

-- system clipboard integration
vmap("<leader>y", '"+y', "Yank to system clipboard")
vmap("<leader>Y", '"+Y', "Yank to system clipboard")

-- delete to blackhole
vmap("<leader>d", '"_d', "Delete to blackhole")
vmap("<leader>D", '"_D', "Delete to blackhole")

-- Visual Block --
-- Move text up and down
keymap("x", "J", ":move '>+1<CR>gv-gv", opts)
keymap("x", "K", ":move '<-2<CR>gv-gv", opts)
keymap("x", "<A-j>", ":move '>+1<CR>gv-gv", opts)
keymap("x", "<A-k>", ":move '<-2<CR>gv-gv", opts)

-- Oil file explorer
keymap("n", "-", "<CMD>Oil --float<CR>", opts)
