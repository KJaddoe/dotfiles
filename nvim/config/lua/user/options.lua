vim.opt.compatible = false
vim.opt.termsync = true
vim.opt.clipboard = "unnamedplus"
vim.opt.hidden = true
vim.opt.updatetime = 1000 -- faster update times, default 4000
vim.opt.mouse = "a"
vim.opt.inccommand = "split"
vim.opt.splitbelow = true
vim.opt.splitright = true
vim.opt.wrap = false
vim.opt.textwidth = 0
vim.opt.expandtab = true
vim.opt.smartindent = true
vim.opt.shiftwidth = 2
vim.opt.softtabstop = 4
vim.opt.tabstop = 4
vim.opt.signcolumn = "yes"
vim.opt.scrolloff = 10
vim.opt.sidescrolloff = 10
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.smoothscroll = true
vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.undofile = true
vim.opt.undodir = vim.fn.stdpath("data") .. "undodir"
vim.opt.hlsearch = false
vim.opt.ignorecase = true
vim.opt.incsearch = true
vim.opt.ruler = true
vim.opt.wildmenu = true
vim.opt.autoread = true
vim.opt.completeopt = { "menu", "menuone", "noselect" }
vim.opt.colorcolumn = "80"
vim.opt.backspace = { "indent", "eol", "start" }
vim.opt.spell = true
vim.opt.spelllang = { "en_us" }
vim.opt.spellfile = vim.uv.os_homedir() .. "/.spell.add"
vim.opt.laststatus = 2
vim.opt.cursorline = true
vim.opt.list = true
vim.opt.showbreak="↪"
vim.opt.listchars = "eol:↲,tab:» ,trail:·,extends:<,precedes:>,conceal:┊,nbsp:␣"
vim.opt.grepprg = "rg --vimgrep --smart-case --follow"
vim.opt.background = "dark"
vim.opt.termguicolors = true
vim.opt.shortmess:append("c")

vim.filetype.add({
  extension = {
    tape = "vhs",
  },
})

-- vim.cmd([[
-- iabbrev emtpy empty
-- ]])
