-- Automatically generated packer.nvim plugin loader code

if vim.api.nvim_call_function('has', {'nvim-0.5'}) ~= 1 then
  vim.api.nvim_command('echohl WarningMsg | echom "Invalid Neovim version for packer.nvim! | echohl None"')
  return
end

vim.api.nvim_command('packadd packer.nvim')

local no_errors, error_msg = pcall(function()

  local time
  local profile_info
  local should_profile = false
  if should_profile then
    local hrtime = vim.loop.hrtime
    profile_info = {}
    time = function(chunk, start)
      if start then
        profile_info[chunk] = hrtime()
      else
        profile_info[chunk] = (hrtime() - profile_info[chunk]) / 1e6
      end
    end
  else
    time = function(chunk, start) end
  end
  
local function save_profiles(threshold)
  local sorted_times = {}
  for chunk_name, time_taken in pairs(profile_info) do
    sorted_times[#sorted_times + 1] = {chunk_name, time_taken}
  end
  table.sort(sorted_times, function(a, b) return a[2] > b[2] end)
  local results = {}
  for i, elem in ipairs(sorted_times) do
    if not threshold or threshold and elem[2] > threshold then
      results[i] = elem[1] .. ' took ' .. elem[2] .. 'ms'
    end
  end

  _G._packer = _G._packer or {}
  _G._packer.profile_output = results
end

time([[Luarocks path setup]], true)
local package_path_str = "/home/anirvan/.cache/nvim/packer_hererocks/2.1.0-beta3/share/lua/5.1/?.lua;/home/anirvan/.cache/nvim/packer_hererocks/2.1.0-beta3/share/lua/5.1/?/init.lua;/home/anirvan/.cache/nvim/packer_hererocks/2.1.0-beta3/lib/luarocks/rocks-5.1/?.lua;/home/anirvan/.cache/nvim/packer_hererocks/2.1.0-beta3/lib/luarocks/rocks-5.1/?/init.lua"
local install_cpath_pattern = "/home/anirvan/.cache/nvim/packer_hererocks/2.1.0-beta3/lib/lua/5.1/?.so"
if not string.find(package.path, package_path_str, 1, true) then
  package.path = package.path .. ';' .. package_path_str
end

if not string.find(package.cpath, install_cpath_pattern, 1, true) then
  package.cpath = package.cpath .. ';' .. install_cpath_pattern
end

time([[Luarocks path setup]], false)
time([[try_loadstring definition]], true)
local function try_loadstring(s, component, name)
  local success, result = pcall(loadstring(s))
  if not success then
    vim.schedule(function()
      vim.api.nvim_notify('packer.nvim: Error running ' .. component .. ' for ' .. name .. ': ' .. result, vim.log.levels.ERROR, {})
    end)
  end
  return result
end

time([[try_loadstring definition]], false)
time([[Defining packer_plugins]], true)
_G.packer_plugins = {
  SimpylFold = {
    loaded = false,
    needs_bufread = true,
    only_cond = false,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/opt/SimpylFold",
    url = "https://github.com/tmhedberg/SimpylFold"
  },
  delimitMate = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/delimitMate",
    url = "https://github.com/Raimondi/delimitMate"
  },
  ["editorconfig-vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/editorconfig-vim",
    url = "https://github.com/editorconfig/editorconfig-vim"
  },
  ["emmet-vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/emmet-vim",
    url = "https://github.com/mattn/emmet-vim"
  },
  ["github-light.vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/github-light.vim",
    url = "https://github.com/romgrk/github-light.vim"
  },
  ["gitsigns.nvim"] = {
    config = { "\27LJ\2\2�\2\0\0\4\0\16\0\0196\0\0\0'\1\1\0B\0\2\0029\0\2\0005\1\3\0005\2\5\0005\3\4\0=\3\6\0025\3\a\0=\3\b\0025\3\t\0=\3\n\0025\3\v\0=\3\f\0025\3\r\0=\3\14\2=\2\15\1B\0\2\1K\0\1\0\nsigns\17changedelete\1\0\2\ttext\6~\ahl\26GitGutterChangeDelete\14topdelete\1\0\2\ttext\b‾\ahl\20GitGutterDelete\vdelete\1\0\2\ttext\6_\ahl\20GitGutterDelete\vchange\1\0\2\ttext\b│\ahl\20GitGutterChange\badd\1\0\0\1\0\2\ttext\b│\ahl\17GitGutterAdd\1\0\1\15debug_mode\1\nsetup\rgitsigns\frequire\0" },
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/gitsigns.nvim",
    url = "https://github.com/lewis6991/gitsigns.nvim"
  },
  ["glow-in-the-dark-gucci-shark-bites-vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/glow-in-the-dark-gucci-shark-bites-vim",
    url = "https://github.com/kenwheeler/glow-in-the-dark-gucci-shark-bites-vim"
  },
  gruvbox = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/gruvbox",
    url = "https://github.com/morhetz/gruvbox"
  },
  ["html5.vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/html5.vim",
    url = "https://github.com/othree/html5.vim"
  },
  ["indent-blankline.nvim"] = {
    config = { "\27LJ\2\2�\2\0\0\2\0\v\0\0256\0\0\0009\0\1\0005\1\3\0=\1\2\0006\0\0\0009\0\1\0005\1\5\0=\1\4\0006\0\0\0009\0\1\0'\1\a\0=\1\6\0006\0\0\0009\0\1\0+\1\1\0=\1\b\0006\0\0\0009\0\1\0+\1\1\0=\1\t\0006\0\0\0009\0\1\0+\1\1\0=\1\n\0K\0\1\0004indent_blankline_show_trailing_blankline_indent*indent_blankline_show_current_context$indent_blankline_use_treesitter\a¦\26indent_blankline_char\1\6\0\0\thelp\rstartify\14dashboard\vpacker\nYanil&indent_blankline_filetype_exclude\1\2\0\0\rterminal%indent_blankline_buftype_exclude\6g\bvim\0" },
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/indent-blankline.nvim",
    url = "https://github.com/lukas-reineke/indent-blankline.nvim"
  },
  ["jsonc.vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/jsonc.vim",
    url = "https://github.com/neoclide/jsonc.vim"
  },
  ["lspsaga.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/lspsaga.nvim",
    url = "https://github.com/glepnir/lspsaga.nvim"
  },
  ["lualine.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/lualine.nvim",
    url = "https://github.com/hoob3rt/lualine.nvim"
  },
  ["markdown-preview.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/markdown-preview.nvim",
    url = "https://github.com/iamcco/markdown-preview.nvim"
  },
  ["neovim-ui"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/neovim-ui",
    url = "https://github.com/mjlbach/neovim-ui"
  },
  ["night-owl-vim-theme"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/night-owl-vim-theme",
    url = "https://github.com/Khaledgarbaya/night-owl-vim-theme"
  },
  ["nvim-bufdel"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-bufdel",
    url = "https://github.com/ojroques/nvim-bufdel"
  },
  ["nvim-bufferline.lua"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-bufferline.lua",
    url = "https://github.com/akinsho/nvim-bufferline.lua"
  },
  ["nvim-colorizer.lua"] = {
    config = { "\27LJ\2\0027\0\0\2\0\3\0\0066\0\0\0'\1\1\0B\0\2\0029\0\2\0B\0\1\1K\0\1\0\nsetup\14colorizer\frequire\0" },
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-colorizer.lua",
    url = "https://github.com/norcalli/nvim-colorizer.lua"
  },
  ["nvim-comment"] = {
    config = { "\27LJ\2\2^\0\0\2\0\3\0\0066\0\0\0'\1\1\0B\0\2\0029\0\2\0B\0\1\1K\0\1\0\25update_commentstring&ts_context_commentstring.internal\frequireO\1\0\3\0\6\0\t6\0\0\0'\1\1\0B\0\2\0029\0\2\0005\1\4\0003\2\3\0=\2\5\1B\0\2\1K\0\1\0\thook\1\0\0\0\nsetup\17nvim_comment\frequire\0" },
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-comment",
    url = "https://github.com/terrortylor/nvim-comment"
  },
  ["nvim-compe"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-compe",
    url = "https://github.com/hrsh7th/nvim-compe"
  },
  ["nvim-lspconfig"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-lspconfig",
    url = "https://github.com/neovim/nvim-lspconfig"
  },
  ["nvim-treesitter"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-treesitter",
    url = "https://github.com/nvim-treesitter/nvim-treesitter"
  },
  ["nvim-treesitter-angular"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-treesitter-angular",
    url = "https://github.com/nvim-treesitter/nvim-treesitter-angular"
  },
  ["nvim-ts-context-commentstring"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-ts-context-commentstring",
    url = "https://github.com/JoosepAlviste/nvim-ts-context-commentstring"
  },
  ["nvim-web-devicons"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/nvim-web-devicons",
    url = "https://github.com/kyazdani42/nvim-web-devicons"
  },
  ["packer.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/packer.nvim",
    url = "https://github.com/wbthomason/packer.nvim"
  },
  playground = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/playground",
    url = "https://github.com/nvim-treesitter/playground"
  },
  ["plenary.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/plenary.nvim",
    url = "https://github.com/nvim-lua/plenary.nvim"
  },
  ["popup.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/popup.nvim",
    url = "https://github.com/nvim-lua/popup.nvim"
  },
  ["rust.vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/rust.vim",
    url = "https://github.com/rust-lang/rust.vim"
  },
  ["telescope-fzy-native.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/telescope-fzy-native.nvim",
    url = "https://github.com/nvim-telescope/telescope-fzy-native.nvim"
  },
  ["telescope-github.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/telescope-github.nvim",
    url = "https://github.com/nvim-telescope/telescope-github.nvim"
  },
  ["telescope-node-modules.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/telescope-node-modules.nvim",
    url = "https://github.com/nvim-telescope/telescope-node-modules.nvim"
  },
  ["telescope-packer.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/telescope-packer.nvim",
    url = "https://github.com/nvim-telescope/telescope-packer.nvim"
  },
  ["telescope.nvim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/telescope.nvim",
    url = "https://github.com/nvim-telescope/telescope.nvim"
  },
  ["vim-colors-synthwave"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-colors-synthwave",
    url = "https://github.com/TroyFletcher/vim-colors-synthwave"
  },
  ["vim-colors-xcode"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-colors-xcode",
    url = "https://github.com/arzg/vim-colors-xcode"
  },
  ["vim-css3-syntax"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-css3-syntax",
    url = "https://github.com/hail2u/vim-css3-syntax"
  },
  ["vim-diff-fold"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-diff-fold",
    url = "https://github.com/sgeb/vim-diff-fold"
  },
  ["vim-easy-align"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-easy-align",
    url = "https://github.com/junegunn/vim-easy-align"
  },
  ["vim-equinusocio-material"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-equinusocio-material",
    url = "https://github.com/chuling/vim-equinusocio-material"
  },
  ["vim-fugitive"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-fugitive",
    url = "https://github.com/tpope/vim-fugitive"
  },
  ["vim-grammarous"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-grammarous",
    url = "https://github.com/rhysd/vim-grammarous"
  },
  ["vim-html-escape"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-html-escape",
    url = "https://github.com/skwp/vim-html-escape"
  },
  ["vim-jsdoc"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-jsdoc",
    url = "https://github.com/heavenshell/vim-jsdoc"
  },
  ["vim-json"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-json",
    url = "https://github.com/elzr/vim-json"
  },
  ["vim-jsx-pretty"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-jsx-pretty",
    url = "https://github.com/MaxMEllon/vim-jsx-pretty"
  },
  ["vim-lua"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-lua",
    url = "https://github.com/tbastos/vim-lua"
  },
  ["vim-markdown"] = {
    loaded = false,
    needs_bufread = true,
    only_cond = false,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/opt/vim-markdown",
    url = "https://github.com/tpope/vim-markdown"
  },
  ["vim-markdown-folding"] = {
    loaded = false,
    needs_bufread = true,
    only_cond = false,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/opt/vim-markdown-folding",
    url = "https://github.com/nelstrom/vim-markdown-folding"
  },
  ["vim-mdx-js"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-mdx-js",
    url = "https://github.com/jxnblk/vim-mdx-js"
  },
  ["vim-monokai-tasty"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-monokai-tasty",
    url = "https://github.com/patstockwell/vim-monokai-tasty"
  },
  ["vim-nightfly-guicolors"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-nightfly-guicolors",
    url = "https://github.com/bluz71/vim-nightfly-guicolors"
  },
  ["vim-racer"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-racer",
    url = "https://github.com/racer-rust/vim-racer"
  },
  ["vim-repeat"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-repeat",
    url = "https://github.com/tpope/vim-repeat"
  },
  ["vim-rhubarb"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-rhubarb",
    url = "https://github.com/tpope/vim-rhubarb"
  },
  ["vim-sayonara"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-sayonara",
    url = "https://github.com/mhinz/vim-sayonara"
  },
  ["vim-startuptime"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-startuptime",
    url = "https://github.com/dstein64/vim-startuptime"
  },
  ["vim-surround"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-surround",
    url = "https://github.com/tpope/vim-surround"
  },
  ["vim-svelte-plugin"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-svelte-plugin",
    url = "https://github.com/leafOfTree/vim-svelte-plugin"
  },
  ["vim-table-mode"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-table-mode",
    url = "https://github.com/dhruvasagar/vim-table-mode"
  },
  ["vim-textobj-user"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-textobj-user",
    url = "https://github.com/kana/vim-textobj-user"
  },
  ["vim-textobj-xmlattr"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-textobj-xmlattr",
    url = "https://github.com/whatyouhide/vim-textobj-xmlattr"
  },
  ["vim-tmux"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-tmux",
    url = "https://github.com/tmux-plugins/vim-tmux"
  },
  ["vim-tmux-navigator"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-tmux-navigator",
    url = "https://github.com/christoomey/vim-tmux-navigator"
  },
  ["vim-unimpaired"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-unimpaired",
    url = "https://github.com/tpope/vim-unimpaired"
  },
  ["vim-vue"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-vue",
    url = "https://github.com/posva/vim-vue"
  },
  ["vim-yaml-folds"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vim-yaml-folds",
    url = "https://github.com/pedrohdz/vim-yaml-folds"
  },
  vison = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/vison",
    url = "https://github.com/Quramy/vison"
  },
  ["yajs.vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/yajs.vim",
    url = "https://github.com/othree/yajs.vim"
  },
  yanil = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/yanil",
    url = "https://github.com/Xuyuanp/yanil"
  },
  ["yats.vim"] = {
    loaded = true,
    path = "/home/anirvan/.local/share/nvim/site/pack/packer/start/yats.vim",
    url = "https://github.com/HerringtonDarkholme/yats.vim"
  }
}

time([[Defining packer_plugins]], false)
-- Config for: nvim-comment
time([[Config for nvim-comment]], true)
try_loadstring("\27LJ\2\2^\0\0\2\0\3\0\0066\0\0\0'\1\1\0B\0\2\0029\0\2\0B\0\1\1K\0\1\0\25update_commentstring&ts_context_commentstring.internal\frequireO\1\0\3\0\6\0\t6\0\0\0'\1\1\0B\0\2\0029\0\2\0005\1\4\0003\2\3\0=\2\5\1B\0\2\1K\0\1\0\thook\1\0\0\0\nsetup\17nvim_comment\frequire\0", "config", "nvim-comment")
time([[Config for nvim-comment]], false)
-- Config for: indent-blankline.nvim
time([[Config for indent-blankline.nvim]], true)
try_loadstring("\27LJ\2\2�\2\0\0\2\0\v\0\0256\0\0\0009\0\1\0005\1\3\0=\1\2\0006\0\0\0009\0\1\0005\1\5\0=\1\4\0006\0\0\0009\0\1\0'\1\a\0=\1\6\0006\0\0\0009\0\1\0+\1\1\0=\1\b\0006\0\0\0009\0\1\0+\1\1\0=\1\t\0006\0\0\0009\0\1\0+\1\1\0=\1\n\0K\0\1\0004indent_blankline_show_trailing_blankline_indent*indent_blankline_show_current_context$indent_blankline_use_treesitter\a¦\26indent_blankline_char\1\6\0\0\thelp\rstartify\14dashboard\vpacker\nYanil&indent_blankline_filetype_exclude\1\2\0\0\rterminal%indent_blankline_buftype_exclude\6g\bvim\0", "config", "indent-blankline.nvim")
time([[Config for indent-blankline.nvim]], false)
-- Config for: gitsigns.nvim
time([[Config for gitsigns.nvim]], true)
try_loadstring("\27LJ\2\2�\2\0\0\4\0\16\0\0196\0\0\0'\1\1\0B\0\2\0029\0\2\0005\1\3\0005\2\5\0005\3\4\0=\3\6\0025\3\a\0=\3\b\0025\3\t\0=\3\n\0025\3\v\0=\3\f\0025\3\r\0=\3\14\2=\2\15\1B\0\2\1K\0\1\0\nsigns\17changedelete\1\0\2\ttext\6~\ahl\26GitGutterChangeDelete\14topdelete\1\0\2\ttext\b‾\ahl\20GitGutterDelete\vdelete\1\0\2\ttext\6_\ahl\20GitGutterDelete\vchange\1\0\2\ttext\b│\ahl\20GitGutterChange\badd\1\0\0\1\0\2\ttext\b│\ahl\17GitGutterAdd\1\0\1\15debug_mode\1\nsetup\rgitsigns\frequire\0", "config", "gitsigns.nvim")
time([[Config for gitsigns.nvim]], false)
-- Config for: nvim-colorizer.lua
time([[Config for nvim-colorizer.lua]], true)
try_loadstring("\27LJ\2\0027\0\0\2\0\3\0\0066\0\0\0'\1\1\0B\0\2\0029\0\2\0B\0\1\1K\0\1\0\nsetup\14colorizer\frequire\0", "config", "nvim-colorizer.lua")
time([[Config for nvim-colorizer.lua]], false)
vim.cmd [[augroup packer_load_aucmds]]
vim.cmd [[au!]]
  -- Filetype lazy-loads
time([[Defining lazy-load filetype autocommands]], true)
vim.cmd [[au FileType python ++once lua require("packer.load")({'SimpylFold'}, { ft = "python" }, _G.packer_plugins)]]
vim.cmd [[au FileType markdown ++once lua require("packer.load")({'vim-markdown-folding', 'vim-markdown'}, { ft = "markdown" }, _G.packer_plugins)]]
time([[Defining lazy-load filetype autocommands]], false)
vim.cmd("augroup END")
vim.cmd [[augroup filetypedetect]]
time([[Sourcing ftdetect script at: /home/anirvan/.local/share/nvim/site/pack/packer/opt/vim-markdown/ftdetect/markdown.vim]], true)
vim.cmd [[source /home/anirvan/.local/share/nvim/site/pack/packer/opt/vim-markdown/ftdetect/markdown.vim]]
time([[Sourcing ftdetect script at: /home/anirvan/.local/share/nvim/site/pack/packer/opt/vim-markdown/ftdetect/markdown.vim]], false)
vim.cmd("augroup END")
if should_profile then save_profiles() end

end)

if not no_errors then
  vim.api.nvim_command('echohl ErrorMsg | echom "Error in packer_compiled: '..error_msg..'" | echom "Please check your config for correctness" | echohl None')
end
