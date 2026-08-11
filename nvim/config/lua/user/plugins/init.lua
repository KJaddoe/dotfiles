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
    "nvim-lualine/lualine.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
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
      require("dressing").setup({
        input = {
          -- When true, <Esc> will close the modal
          insert_only = true,
        },
      })
    end,
  },
  {
    "folke/which-key.nvim",
    event = "VeryLazy",
    config = function()
      local wk = require("which-key")
      wk.setup({})
      wk.add({
        -- Prefix group names shown in the popup.
        { "<leader>b", group = "Buffer" },
        { "<leader>c", group = "Code / Quickfix" },
        { "<leader>f", group = "Find" },
        { "<leader>g", group = "Git" },
        { "<leader>k", group = "HTTP" },
        { "<leader>l", group = "Symbols / Grep" },
        { "<leader>o", group = "Open / Angular" },
        { "<leader>s", group = "Swap" },
        { "<leader>t", group = "Test" },
        { "<leader>x", group = "Debug" },
        -- treesitter swap mappings can't carry a native desc.
        { "<leader>sa", desc = "Swap param with next" },
        { "<leader>sA", desc = "Swap param with previous" },
      })
    end,
  },
  {
    "j-hui/fidget.nvim",
    opts = {},
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
    end,
  },
  {
    "folke/todo-comments.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    opts = {
      -- your configuration comes here
      -- or leave it empty to use the default settings
      -- refer to the configuration section below
    },
  },
  {
    "ThePrimeagen/harpoon",
    branch = "harpoon2",
    dependencies = { "nvim-lua/plenary.nvim" },
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
    },
    config = function()
      require("telescope").setup({
        defaults = {
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
      require("auto-hlsearch").setup()
    end,
  },
  {
    "alexghergh/nvim-tmux-navigation",
    config = function()
      local nvim_tmux_nav = require("nvim-tmux-navigation")
      nvim_tmux_nav.setup({
        disable_when_zoomed = true, -- defaults to false
      })
      vim.keymap.set("n", "<C-h>", nvim_tmux_nav.NvimTmuxNavigateLeft)
      vim.keymap.set("n", "<C-j>", nvim_tmux_nav.NvimTmuxNavigateDown)
      vim.keymap.set("n", "<C-k>", nvim_tmux_nav.NvimTmuxNavigateUp)
      vim.keymap.set("n", "<C-l>", nvim_tmux_nav.NvimTmuxNavigateRight)
      vim.keymap.set("n", "<C-\\>", nvim_tmux_nav.NvimTmuxNavigateLastActive)
      vim.keymap.set("n", "<C-Space>", nvim_tmux_nav.NvimTmuxNavigateNext)
    end,
  },
  {
    "max397574/better-escape.nvim",
    config = function()
      require("better_escape").setup({
        timeout = 100,
        default_mappings = false,
        mappings = {
          i = {
            j = { k = "<Esc>" },
            k = { j = "<Esc>" },
          },
        },
      })
    end,
  },
  {
    "laytan/cloak.nvim",
    config = function()
      require("cloak").setup({ --[[ your config ]]
      })
    end,
  },

  -- Coding --
  { "neovim/nvim-lspconfig" },
  { "b0o/schemastore.nvim", lazy = true },
  {
    dir = vim.fn.stdpath("config") .. "/neotest-filetype-fix",
    name = "neotest-filetype-fix",
    lazy = false,
  },
  {
    "nvim-neotest/neotest",
    dependencies = {
      "nvim-neotest/nvim-nio",
      "nvim-lua/plenary.nvim",
      "antoinemadec/FixCursorHold.nvim",
      "nvim-treesitter/nvim-treesitter",
      "nvim-neotest/neotest-jest",
    },
  },
  {
    "joeveiga/ng.nvim",
    config = function()
      local ng = require("ng")
      local function map(lhs, rhs, desc)
        vim.keymap.set(
          "n",
          lhs,
          rhs,
          { noremap = true, silent = true, desc = desc }
        )
      end
      map(
        "<leader>ot",
        ng.goto_template_for_component,
        "Angular: goto template"
      )
      map(
        "<leader>oc",
        ng.goto_component_with_template_file,
        "Angular: goto component"
      )
      map("<leader>oT", ng.get_template_tcb, "Angular: template type-check")
    end,
  },
  { "mfussenegger/nvim-dap" },
  {
    "rcarriga/nvim-dap-ui",
    dependencies = { "mfussenegger/nvim-dap", "nvim-neotest/nvim-nio" },
  },
  { "tpope/vim-dadbod" },
  {
    "kristijanhusak/vim-dadbod-ui",
    dependencies = { "tpope/vim-dadbod" },
    config = function()
      vim.g.db_ui_use_nerd_fonts = 1
      vim.keymap.set("n", "<leader>od", "<cmd>DBUIToggle<CR>", {
        noremap = true,
        silent = true,
        desc = "Toggle DB UI",
      })
    end,
  },
  {
    "kristijanhusak/vim-dadbod-completion",
    dependencies = { "tpope/vim-dadbod" },
    ft = { "sql", "mysql", "plsql" },
  },
  {
    "mistweaverco/kulala.nvim",
    ft = { "http", "rest" },
    opts = {
      global_keymaps = false,
    },
    config = function(_, opts)
      require("kulala").setup(opts)
      vim.api.nvim_create_autocmd("FileType", {
        pattern = "http",
        callback = function(args)
          local kulala = require("kulala")
          local function kmap(lhs, rhs, desc)
            vim.keymap.set("n", lhs, rhs, {
              noremap = true,
              silent = true,
              buffer = args.buf,
              desc = desc,
            })
          end
          kmap("<CR>", kulala.run, "Run request")
          kmap("[r", kulala.jump_prev, "Previous request")
          kmap("]r", kulala.jump_next, "Next request")
          kmap("<leader>ki", kulala.inspect, "Inspect request")
          kmap("<leader>kc", kulala.copy, "Copy as cURL")
        end,
      })
    end,
  },
  {
    "stevearc/conform.nvim",
    opts = {},
    config = function()
      require("conform").setup({
        formatters_by_ft = {
          css = { "prettier" },
          scss = { "prettier" },
          less = { "prettier" },
          html = { "prettier" },
          htmlangular = { "prettier" },
          javascript = { "prettier" },
          typescript = { "prettier" },
          javascriptreact = { "prettier" },
          typescriptreact = { "prettier" },
          json = { "prettier" },
          jsonc = { "prettier" },
          markdown = { "prettier" },
          yaml = { "prettier" },
          lua = { "stylua" },
          sh = { "shfmt" },
          bash = { "shfmt" },
          cs = { "csharpier" },
          sql = { "sql_formatter" },
          toml = { "taplo" },
          zig = { "zigfmt" },
          python = { "isort", "black" },
          ["_"] = { "trim_whitespace", "trim_newlines" },
        },
        format_after_save = {
          lsp_format = "fallback",
        },
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
    },
  },
  {
    "windwp/nvim-autopairs",
    event = "InsertEnter",
    config = true,
    check_ts = true,
  },
  {
    "windwp/nvim-ts-autotag",
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
    end,
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
    end,
  },
  { "rafamadriz/friendly-snippets" },
  { "folke/neodev.nvim", opts = {} },
  {
    "kylechui/nvim-surround",
    version = "*", -- Use for stability; omit to use `main` branch for the latest features
    event = "VeryLazy",
    config = function()
      require("nvim-surround").setup({
        -- Configuration here, or leave empty to use defaults
      })
    end,
  },
  {
    "Wansmer/treesj",
    keys = { "<space>m", "<space>j", "<space>s" },
    dependencies = { "nvim-treesitter/nvim-treesitter" }, -- if you install parsers with `nvim-treesitter`
    config = function()
      require("treesj").setup({ --[[ your config ]]
      })
    end,
  },
  { "nvim-treesitter/nvim-treesitter", build = ":TSUpdate" },
  { "nvim-treesitter/nvim-treesitter-textobjects" },
  { "nvim-treesitter/nvim-treesitter-context" },
  { "RRethy/nvim-treesitter-endwise" },
  {
    "numToStr/Comment.nvim",
    config = function()
      require("Comment").setup()
    end,
  },
  {
    "folke/trouble.nvim",
    config = function()
      require("trouble").setup({})
    end,
  },
  {
    "akinsho/bufferline.nvim",
    version = "*",
    dependencies = "nvim-tree/nvim-web-devicons",
    config = function()
      require("bufferline").setup()
    end,
  },
  { "dhruvasagar/vim-table-mode" },
  {
    "iamcco/markdown-preview.nvim",
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    ft = { "markdown" },
    build = ":call mkdp#util#install()",
  },
  { "psf/black" },
  {
    "catgoose/nvim-colorizer.lua",
    config = function()
      require("colorizer").setup()
    end,
  },
  {
    "nvimdev/lspsaga.nvim",
    config = function()
      require("lspsaga").setup({
        -- Show the code-action lightbulb as virtual text only; its gutter sign
        -- (priority 40) otherwise hides lower-priority signs like dap
        -- breakpoints in a single-width signcolumn.
        lightbulb = { sign = false },
      })
    end,
    dependencies = {
      "nvim-treesitter/nvim-treesitter", -- optional
      "nvim-tree/nvim-web-devicons", -- optional
    },
  },
  {
    "folke/lazydev.nvim",
    ft = "lua", -- only load on lua files
  },
  {
    "stevearc/oil.nvim",
    dependencies = { { "echasnovski/mini.icons", opts = {} } },
    -- Lazy loading is tricky to get right with oil; keep it eager.
    lazy = false,
    ---@module 'oil'
    ---@type oil.SetupOpts
    opts = {
      default_file_explorer = true,
      skip_confirm_for_simple_edits = true,
      watch_for_changes = true,
      view_options = {
        show_hidden = true,
        natural_order = true,
        is_always_hidden = function(name, _)
          return name == ".." or name == ".git"
        end,
      },
      float = {
        padding = 2,
        max_width = 100,
        max_height = 0,
      },
      win_options = {
        wrap = true,
        winblend = 0,
      },
      keymaps = {
        ["<C-c>"] = false,
        ["q"] = "actions.close",
      },
    },
  },
  {
    "pearofducks/ansible-vim",
  },
})
