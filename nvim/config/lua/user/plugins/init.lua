local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable", -- latest stable release
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
  -- UI --
  {
    "folke/tokyonight.nvim",
    lazy = false,
    priority = 1000,
    opts = {},
  },
  {
    "kyazdani42/nvim-web-devicons",
    config = function()
      require("nvim-web-devicons").setup()
    end,
  },
  {
    "rcarriga/nvim-notify",
    config = function()
      require("notify").setup({
        render = "compact",
        stages = "static",
        timeout = 2000,
        max_height = function()
          return math.floor(vim.o.lines * 0.75)
        end,
        max_width = function()
          return math.floor(vim.o.columns * 0.75)
        end,
        on_open = function(win)
          vim.api.nvim_win_set_config(win, { focusable = false })
        end,
      })
    end,
  },
  {
    'nvim-lualine/lualine.nvim',
    dependencies = { 'nvim-tree/nvim-web-devicons' },
    config = function()
      require("lualine").setup({
        options = {
          theme = "tokyonight",
          component_separators = "",
          section_separators = "",
        },
        sections = {
          lualine_c = {
            "%=",
            {
              "filename",
              file_status = false,
              path = 1,
            },
          },
        },
        inactive_sections = {
          lualine_c = {
            "%=",
            {
              "filename",
              file_status = false,
              path = 1,
            },
          },
          lualine_x = { "location" },
        },
      })
    end,
  },
  {
    "stevearc/dressing.nvim",
    config = function()
      require("dressing").setup(
        {
          input = {
            -- When true, <Esc> will close the modal
            insert_only = true,
          }
        }
      )
    end
  },

  -- Basics
  { "lukas-reineke/indent-blankline.nvim", main = "ibl", opts = {} },
  {
    "lewis6991/gitsigns.nvim",
    config = function()
      require("gitsigns").setup({
        preview_config = {
          border = "rounded",
        },
      })
    end
  },
  {
    "folke/todo-comments.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    opts = {
      -- your configuration comes here
      -- or leave it empty to use the default settings
      -- refer to the configuration section below
    }
  },
  {
    "ThePrimeagen/harpoon",
    branch = "harpoon2",
    dependencies = { "nvim-lua/plenary.nvim" }
  },
  { "tpope/vim-fugitive" },
  { "tpope/vim-rhubarb" },
  { "tpope/vim-abolish" },
  { "tpope/vim-repeat" },
  { "tpope/vim-eunuch" },
  { "tpope/vim-sleuth" },
  { "tpope/vim-speeddating" },
  {
    "nvim-telescope/telescope.nvim",
    dependencies = {
      { "nvim-lua/plenary.nvim" },
      { "nvim-telescope/telescope-github.nvim" },
      { "nvim-telescope/telescope-file-browser.nvim" },
    },
    config = function()
      require('telescope').setup({
        defaults = {
          mappings = {
            i = {
              ["<CR>"] = select_one_or_multi,
            },
          },
          prompt_prefix = "   ",
          selection_caret = " ❯ ",
          entry_prefix = "   ",
          multi_icon = "+ ",
          path_display = { "filename_first" },
          vimgrep_arguments = {
            "rg",
            "--color=never",
            "--no-heading",
            "--with-filename",
            "--line-number",
            "--column",
            "--smart-case",
            "--hidden",
            "--glob=!.git",
          },
        },
      })
    end,
  },
  {
    "asiryk/auto-hlsearch.nvim",
    tag = "1.1.0",
    config = function()
      require('auto-hlsearch').setup()
    end,
  },
  {
    'alexghergh/nvim-tmux-navigation',
    config = function()
      local nvim_tmux_nav = require('nvim-tmux-navigation')
      nvim_tmux_nav.setup {
        disable_when_zoomed = true -- defaults to false
      }
      vim.keymap.set('n', "<C-h>", nvim_tmux_nav.NvimTmuxNavigateLeft)
      vim.keymap.set('n', "<C-j>", nvim_tmux_nav.NvimTmuxNavigateDown)
      vim.keymap.set('n', "<C-k>", nvim_tmux_nav.NvimTmuxNavigateUp)
      vim.keymap.set('n', "<C-l>", nvim_tmux_nav.NvimTmuxNavigateRight)
      vim.keymap.set('n', "<C-\\>", nvim_tmux_nav.NvimTmuxNavigateLastActive)
      vim.keymap.set('n', "<C-Space>", nvim_tmux_nav.NvimTmuxNavigateNext)
    end
  },
  {
    "max397574/better-escape.nvim",
    config = function()
      require("better_escape").setup({
        mapping = { "jk", "kj" },
        timeout = 100,
      })
    end,
  },
  { "famiu/bufdelete.nvim" },
  {
    'laytan/cloak.nvim',
    config = function()
      require('cloak').setup({ --[[ your config ]] })
    end,
  },

  -- Coding --
  { "neovim/nvim-lspconfig" },
  {
    'stevearc/conform.nvim',
    opts = {},
    config = function()
      require("conform").setup({
        formatters_by_ft = {
          css = { "prettier" },
          fish = { "fish_indent" },
          html = { "prettier" },
          javascript = { "prettier" },
          typescript = { "prettier" },
          javascriptreact = { "prettier" },
          typescriptreact = { "prettier" },
          json = { "jq" },
          lua = { "stylua" },
          markdown = { "prettier" },
          nix = { "nixpkgs_fmt" },
          rust = { "rustfmt" },
          sh = { "shfmt" },
          sql = { "pg_format", "sql_formatter" },
          tf = { "terraform_fmt" },
          yaml = { "prettier" },
          zig = { "zigfmt" },
          python = { "isort", "black" },
          ["_"] = { "trim_whitespace", "trim_newlines" },
        },
        format_on_save = {
          lsp_fallback = true,
          timeout_ms = 500,
        },
      })
      vim.api.nvim_create_autocmd("BufWritePre", {
        pattern = "*",
        callback = function(args)
          require("conform").format({ bufnr = args.buf })
        end,
      })
    end,
  },
  {
    "hrsh7th/nvim-cmp",
    dependencies = {
      "hrsh7th/cmp-buffer",
      "hrsh7th/cmp-path",
      "hrsh7th/cmp-cmdline",
      "hrsh7th/cmp-emoji",
      "hrsh7th/cmp-calc",
      "hrsh7th/cmp-nvim-lsp",
      "hrsh7th/cmp-nvim-lsp-signature-help",
      "L3MON4D3/LuaSnip",
      "saadparwaiz1/cmp_luasnip",
      "f3fora/cmp-spell",
    }
  },
  {
    'windwp/nvim-autopairs',
    event = "InsertEnter",
    config = true,
    check_ts = true,
  },
  {
    'windwp/nvim-ts-autotag',
    config = function()
      require("nvim-ts-autotag").setup({ enable = true })
    end,
  },
  {
    "zbirenbaum/copilot.lua",
    cmd = "Copilot",
    event = "InsertEnter",
    config = function()
      require("copilot").setup()
    end,
  },
  {
    "zbirenbaum/copilot-cmp",
    config = function()
      require("copilot_cmp").setup()
    end
  },
  {
    "L3MON4D3/LuaSnip",
    config = function()
      require("luasnip").setup({
        -- see: https://github.com/L3MON4D3/LuaSnip/issues/525
        region_check_events = "InsertEnter",
        delete_check_events = "InsertLeave",
      })
      require("luasnip.loaders.from_vscode").lazy_load()
    end
  },
  { "rafamadriz/friendly-snippets" },
  { "folke/neodev.nvim",           opts = {} },
  {
    "kylechui/nvim-surround",
    version = "*", -- Use for stability; omit to use `main` branch for the latest features
    event = "VeryLazy",
    config = function()
      require("nvim-surround").setup({
        -- Configuration here, or leave empty to use defaults
      })
    end
  },
  {
    'Wansmer/treesj',
    keys = { '<space>m', '<space>j', '<space>s' },
    dependencies = { 'nvim-treesitter/nvim-treesitter' }, -- if you install parsers with `nvim-treesitter`
    config = function()
      require('treesj').setup({ --[[ your config ]] })
    end,
  },
  { "nvim-treesitter/nvim-treesitter",            build = ':TSUpdate' },
  { "nvim-treesitter/nvim-treesitter-angular" },
  { "nvim-treesitter/nvim-treesitter-textobjects" },
  { "nvim-treesitter/nvim-treesitter-context" },
  { "RRethy/nvim-treesitter-endwise" },
  {
    "numToStr/Comment.nvim",
    config = function()
      require("Comment").setup()
    end
  },
  { "mhartington/formatter.nvim" },
  {
    "folke/trouble.nvim",
    config = function()
      require("trouble").setup {}
    end
  },
  {
    'akinsho/bufferline.nvim',
    version = "*",
    dependencies = 'nvim-tree/nvim-web-devicons',
    config = function()
      require("bufferline").setup()
    end
  },
  { "dhruvasagar/vim-table-mode" },
  {
    "iamcco/markdown-preview.nvim",
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    ft = { "markdown" },
    build = function() vim.fn["mkdp#util#install"]() end,
  },
  { "psf/black" },
  {
    "norcalli/nvim-colorizer.lua",
    config = function()
      require "colorizer".setup()
    end
  },
  {
    'nvimdev/lspsaga.nvim',
    config = function()
      require('lspsaga').setup({})
    end,
    dependencies = {
      'nvim-treesitter/nvim-treesitter', -- optional
      'nvim-tree/nvim-web-devicons',     -- optional
    },
  },
  { "OmniSharp/omnisharp-vim", build = ':OmniSharpInstall' },
  {
    "folke/lazydev.nvim",
    ft = "lua", -- only load on lua files
  },
})
