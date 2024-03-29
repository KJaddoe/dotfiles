-- Options
local parsers = require "nvim-treesitter.parsers"
local Type = {GLOBAL_OPTION = "o", WINDOW_OPTION = "wo", BUFFER_OPTION = "bo"}
local add_options = function(option_type, options)
  if type(options) ~= "table" then
    error 'options should be a type of "table"'
    return
  end
  local vim_option = vim[option_type]
  for key, value in pairs(options) do
    vim_option[key] = value
  end
end
local Option = {}
Option.g = function(options)
  add_options(Type.GLOBAL_OPTION, options)
end
Option.w = function(options)
  add_options(Type.WINDOW_OPTION, options)
end
Option.b = function(options)
  add_options(Type.BUFFER_OPTION, options)
end

Option.g {
  scrolloff = 999,
  cmdheight = 1,
  termguicolors = true,
  mouse = "a",
  clipboard = "unnamedplus",
  hidden = true,
  showmode = false,
  timeoutlen = 3e3,
  tabstop = 2,
  shiftwidth = 2,
  expandtab = true,
  conceallevel = 0,
  laststatus = 2,
  wrap = true,
  linebreak = true,
  list = true,
  splitright = true,
  confirm = true,
  listchars = "tab:▸ ,trail:·",
  wildmenu = true,
  wildmode = "longest:full,full",
  wrap = false,
  autoread = true,
  updatetime = 500,
  redrawtime = 500,
  fillchars = vim.o.fillchars .. "vert:│,fold: ",
  undofile = true,
  virtualedit = "onemore",
  guicursor = "n-v-c-sm:block,i-ci-ve:ver25,r-cr-o:hor20",
  complete = ".,w,b,u,t,k",
  completeopt = "menu,menuone,noinsert,noselect",
  formatoptions = "jtcroql",
  inccommand = "nosplit",
  shortmess = "atIcF",
  isfname = table.concat(
    vim.tbl_filter(
      function(entry)
        if entry == "=" then
          return false
        else
          return true
        end
      end,
      vim.split(vim.o.isfname, ",")
    ),
    ","
  ),
  swapfile = false,
  diffopt = "internal,filler,closeoff,algorithm:patience,iwhiteall",
  emoji = false,
  indentexpr="nvim_treesitter#indent()",
  showmatch = false,
  ignorecase = true,
  smartcase = true
}
Option.b {
  swapfile = false,
  shiftwidth = 2,
  indentexpr="nvim_treesitter#indent()"
}
Option.w {
  number = true,
  relativenumber = true,
  numberwidth = 1,
  signcolumn = "yes:2",
  spell = false,
  foldlevel = 99,
  foldmethod = "syntax",
  -- foldmethod = "expr",
  foldexpr = "nvim_treesitter#foldexpr()",
  foldtext = "v:lua.foldText()",
  linebreak = true
}

vim.cmd('let &t_8f = "\\<Esc>[38;2;%lu;%lu;%lum"')
vim.cmd('let &t_8b = "\\<Esc>[48;2;%lu;%lu;%lum"')

vim.g.mapleader = ","
vim.g.one_allow_italics = true
vim.g.oceanic_next_terminal_bold = true
vim.g.oceanic_next_terminal_italic = true
vim.g.vim_monokai_tasty_italic = true
vim.g.table_mode_corner = "|"
vim.g.markdown_fold_override_foldtext = false
vim.g.markdown_syntax_conceal = false
vim.g.mkdp_auto_start = false
vim.g.vim_json_syntax_conceal = false
vim.g.override_nvim_web_devicons = true
local configs = parsers.get_parser_configs()
local ft_str =
  table.concat(
  vim.tbl_map(
    function(ft)
      return configs[ft].filetype or ft
    end,
    parsers.available_parsers()
  ),
  ","
)
vim.cmd("autocmd Filetype " .. ft_str .. " setlocal foldmethod=expr foldexpr=nvim_treesitter#foldexpr()")

return Option
