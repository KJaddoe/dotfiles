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

--- Build a lazy.nvim `keys` entry, carrying the same mapping options the
--- keymaps used before they moved into their plugin specs.
---@param lhs string Keymap
---@param rhs function Action
---@param desc string which-key description
---@return table entry lazy.nvim keys spec
local function lazy_key(lhs, rhs, desc)
  return { lhs, rhs, desc = desc, silent = true, noremap = true }
end

require("lazy").setup({
  -- UI --
  {
    "rebelot/kanagawa.nvim",
    lazy = false,
    priority = 1000,
    opts = {
      overrides = function(colors)
        local theme = colors.theme
        local panel = theme.ui.bg_m1
        local prompt = theme.ui.bg_p1
        return {
          DapStoppedLine = {
            bg = colors.palette.winterYellow,
          },
          TelescopeNormal = {
            bg = panel,
            fg = theme.ui.fg_dim,
          },
          TelescopeBorder = {
            bg = panel,
            fg = panel,
          },
          TelescopePromptNormal = {
            bg = prompt,
          },
          TelescopePromptBorder = {
            bg = prompt,
            fg = prompt,
          },
          TelescopePromptTitle = {
            bg = prompt,
            fg = prompt,
          },
          TelescopePreviewTitle = {
            bg = panel,
            fg = panel,
          },
          TelescopeResultsTitle = {
            bg = panel,
            fg = panel,
          },
        }
      end,
    },
    config = function(_, opts)
      require("kanagawa").setup(opts)
      vim.cmd.colorscheme("kanagawa-wave")
    end,
  },
  {
    "kyazdani42/nvim-web-devicons",
    config = function()
      require("nvim-web-devicons").setup()
    end,
  },
  {
    -- Eager on purpose: a lazy trigger would leave vim.notify pointing at the
    -- built-in handler until the trigger fired, silently swallowing every
    -- notification raised before that.
    "rcarriga/nvim-notify",
    opts = {
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
    },
    config = function(_, opts)
      local notify = require("notify")
      notify.setup(opts)
      vim.notify = notify

      vim.keymap.set("n", "<leader>un", function()
        notify.dismiss({ silent = true, pending = true })
      end, {
        noremap = true,
        silent = true,
        desc = "Delete all Notifications",
      })
    end,
  },
  {
    "nvim-lualine/lualine.nvim",
    dependencies = { "nvim-tree/nvim-web-devicons" },
    config = function()
      require("lualine").setup({
        options = {
          theme = "kanagawa",
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
        { "<leader>t", group = "Test" },
        { "<leader>x", group = "Debug" },
        -- treesitter swap mappings can't carry a native desc.
        { "<leader>a", desc = "Swap param with next" },
        { "<leader>A", desc = "Swap param with previous" },
      })
    end,
  },
  {
    "j-hui/fidget.nvim",
    opts = {},
  },

  -- Basics
  {
    "lukas-reineke/indent-blankline.nvim",
    main = "ibl",
    opts = {
      indent = { char = "│" },
      exclude = { filetypes = { "help" } },
      scope = { enabled = false },
    },
  },
  {
    -- Eager: the sign column is drawn without any user action, so a keys
    -- trigger would leave hunks unmarked until a hunk key was first pressed.
    "lewis6991/gitsigns.nvim",
    opts = {
      preview_config = {
        border = "rounded",
      },
    },
    config = function(_, opts)
      local gitsigns = require("gitsigns")
      gitsigns.setup(opts)

      --- Add a normal-mode gitsigns keymap.
      ---@param lhs string Keymap
      ---@param rhs string|function Action
      ---@param desc string which-key description
      local function map(lhs, rhs, desc)
        vim.keymap.set(
          "n",
          lhs,
          rhs,
          { noremap = true, silent = true, desc = desc }
        )
      end

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
    end,
  },
  {
    -- Eager, because the highlighting is the plugin's whole job: a keys trigger
    -- would leave TODO comments unhighlighted until a jump key was first
    -- pressed. Creating those highlight groups forces a redraw that would steal
    -- the :intro screen, but todo-comments already defers its own setup when
    -- called before VimEnter, so no deferral is needed here.
    "folke/todo-comments.nvim",
    dependencies = { "nvim-lua/plenary.nvim" },
    opts = {
      highlight = {
        keyword = "bg",
      },
    },
    config = function(_, opts)
      local todo = require("todo-comments")
      todo.setup(opts)

      vim.keymap.set("n", "]t", todo.jump_next, { desc = "Next todo comment" })
      vim.keymap.set(
        "n",
        "[t",
        todo.jump_prev,
        { desc = "Previous todo comment" }
      )
    end,
  },
  {
    -- Eager: fugitive does not appear in the startup profile at all, so a lazy
    -- trigger would buy nothing and risk the fugitive:// buffer handling.
    "tpope/vim-fugitive",
    init = function()
      vim.g.fugitive_legacy_commands = 0
    end,
    config = function()
      vim.keymap.set("n", "<leader>gs", vim.cmd.Git, {
        noremap = true,
        silent = true,
        desc = "Open Git",
      })
      vim.keymap.set("n", "<leader>gms", function()
        vim.cmd.Git("sync")
      end, { noremap = true, silent = true, desc = "Git sync" })
    end,
  },
  { "tpope/vim-rhubarb" },
  { "tpope/vim-repeat" },
  { "tpope/vim-sleuth" },
  {
    -- Lazy on its keymaps: telescope does nothing until a picker is opened,
    -- and it dominated the startup profile. Every keymap therefore lives in
    -- `keys` rather than in `config`, which now only runs on first use.
    "nvim-telescope/telescope.nvim",
    dependencies = { { "nvim-lua/plenary.nvim" } },
    keys = {
      lazy_key("<c-p>", function()
        local select = require("user.telescope")
        require("telescope.builtin").find_files({
          find_command = require("user.search").find_command(),
          attach_mappings = function(_, map)
            map("i", "<cr>", select.edit)
            map("i", "<c-x>", select.split)
            map("i", "<c-v>", select.vsplit)
            map("i", "<c-t>", select.tabedit)
            return true
          end,
        })
      end, "Find files"),
      lazy_key("<leader>fb", function()
        local select = require("user.telescope")
        require("telescope.builtin").buffers({
          attach_mappings = function(_, map)
            map("i", "<cr>", select.edit)
            map("i", "<c-x>", select.split)
            map("i", "<c-v>", select.vsplit)
            map("i", "<c-t>", select.tabedit)
            map("i", "<c-d>", "delete_buffer")
            return true
          end,
        })
      end, "Buffers"),
      lazy_key("<leader>of", function()
        local select = require("user.telescope")
        require("telescope.builtin").oldfiles({
          only_cwd = true,
          attach_mappings = function(_, map)
            map("i", "<cr>", select.edit)
            map("i", "<c-x>", select.split)
            map("i", "<c-v>", select.vsplit)
            map("i", "<c-t>", select.tabedit)
            return true
          end,
        })
      end, "Recent files (cwd)"),
      lazy_key("<leader>lg", function()
        require("telescope.builtin").live_grep()
      end, "Live grep"),
      lazy_key("<leader>fh", function()
        require("telescope.builtin").help_tags()
      end, "Help tags"),
      lazy_key("<leader>fc", function()
        require("telescope.builtin").commands()
      end, "Commands"),
      lazy_key("<leader>fk", function()
        require("telescope.builtin").keymaps()
      end, "Keymaps"),
      lazy_key("<leader>fr", function()
        require("telescope.builtin").resume()
      end, "Resume last picker"),
      lazy_key("<leader>fq", function()
        require("telescope.builtin").quickfix()
      end, "Quickfix list"),
      lazy_key("<leader>/", function()
        require("telescope.builtin").current_buffer_fuzzy_find()
      end, "Fuzzy find in buffer"),
      lazy_key("<leader>xx", function()
        require("telescope.builtin").diagnostics()
      end, "Diagnostics list"),

      -- Git browsing. Read-only views with a diff preview; the work itself
      -- happens in a terminal pane.
      lazy_key("<leader>gf", function()
        require("telescope.builtin").git_status()
      end, "Changed files"),
      lazy_key("<leader>gc", function()
        require("telescope.builtin").git_commits()
      end, "Commits (repo)"),
      lazy_key("<leader>gC", function()
        require("telescope.builtin").git_bcommits()
      end, "Commits (this file)"),
      lazy_key("<leader>gB", function()
        require("telescope.builtin").git_branches()
      end, "Branches"),
    },
    config = function()
      require("telescope").setup({
        defaults = {
          prompt_prefix = "   ",
          selection_caret = " ❯ ",
          entry_prefix = "   ",
          multi_icon = "+ ",
          path_display = { "filename_first" },
          vimgrep_arguments = require("user.search").vimgrep_arguments(),
        },
      })

      -- nvim-notify registers this itself, but only if telescope is already
      -- loaded when notify sets up, which no longer happens now telescope is
      -- lazy. Registering it here keeps :Telescope notify (a searchable history
      -- of past notifications) working, with its cost off the startup path.
      require("telescope").load_extension("notify")
    end,
  },
  {
    "asiryk/auto-hlsearch.nvim",
    tag = "1.1.0",
    config = function()
      require("auto-hlsearch").setup()
      -- setup() rebinds n/N itself, so the centring has to be layered on top of
      -- its mappings here rather than in user.keymaps, which runs earlier and
      -- would simply be overwritten. Its mappings are `expr`, returning the key
      -- to run rather than running it, so this appends to that return value;
      -- noremap keeps the returned `n` the built-in one, not this mapping.
      for _, lhs in ipairs({ "n", "N" }) do
        local hlsearch = vim.fn.maparg(lhs, "n", false, true)
        vim.keymap.set("n", lhs, function()
          local keys = hlsearch.callback and hlsearch.callback() or lhs
          return keys .. "zzzv"
        end, {
          expr = true,
          desc = "Search match "
            .. (lhs == "n" and "next" or "previous")
            .. " (centred)",
        })
      end
    end,
  },
  {
    "alexghergh/nvim-tmux-navigation",
    config = function()
      local nvim_tmux_nav = require("nvim-tmux-navigation")
      nvim_tmux_nav.setup({
        disable_when_zoomed = true, -- defaults to false
      })
      -- Window and pane navigation in every mode, never anything else. Insert
      -- mode matters most: <C-h> is a backspace by default, which stranded the
      -- cursor in a gitcommit buffer, since those open straight into insert.
      -- Leaving insert first keeps the target window in normal mode.
      for lhs, spec in pairs({
        ["<C-h>"] = { nvim_tmux_nav.NvimTmuxNavigateLeft, "left" },
        ["<C-j>"] = { nvim_tmux_nav.NvimTmuxNavigateDown, "down" },
        ["<C-k>"] = { nvim_tmux_nav.NvimTmuxNavigateUp, "up" },
        ["<C-l>"] = { nvim_tmux_nav.NvimTmuxNavigateRight, "right" },
        ["<C-\\>"] = {
          nvim_tmux_nav.NvimTmuxNavigateLastActive,
          "to last active",
        },
      }) do
        local navigate, label = spec[1], spec[2]
        vim.keymap.set({ "n", "i", "v", "t" }, lhs, function()
          vim.cmd("stopinsert")
          navigate()
        end, { desc = "Navigate " .. label })
      end
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
  {
    -- Lazy on the first real buffer. Nothing here has an effect until a file
    -- is open, and `vim.lsp.enable` re-runs its own FileType handler across
    -- buffers that already exist, so loading late still attaches. Takes
    -- cmp-nvim-lsp and schemastore off the startup path with it: both are
    -- required from this config and nowhere else that runs earlier.
    "neovim/nvim-lspconfig",
    event = { "BufReadPre", "BufNewFile" },
    config = function()
      local ms = require("vim.lsp.protocol").Methods
      local cmp_capabilities = require("cmp_nvim_lsp").default_capabilities()
      require("lsp_autocommands").setup()

      -- capabilities
      local capabilities = vim.lsp.protocol.make_client_capabilities()
      capabilities =
        vim.tbl_deep_extend("force", capabilities, cmp_capabilities)
      capabilities = vim.tbl_deep_extend("force", capabilities, {
        workspace = {
          didChangeWatchedFiles = {
            dynamicRegistration = true,
            relativePatternSupport = true,
          },
        },
      })

      -- global floating window borders
      vim.lsp.util.open_floating_preview = (function(orig)
        return function(contents, syntax, opts, ...)
          opts = opts or {}
          opts.border = opts.border or "rounded"
          return orig(contents, syntax, opts, ...)
        end
      end)(vim.lsp.util.open_floating_preview)

      -- ======================
      -- LSP SERVER CONFIGS
      -- ======================

      vim.lsp.config("ts_ls", {
        capabilities = capabilities,
        settings = {
          javascript = {
            inlayHints = {
              includeInlayEnumMemberValueHints = true,
              includeInlayFunctionLikeReturnTypeHints = true,
              includeInlayFunctionParameterTypeHints = true,
              includeInlayParameterNameHints = "all",
              includeInlayParameterNameHintsWhenArgumentMatchesName = true,
              includeInlayPropertyDeclarationTypeHints = true,
              includeInlayVariableTypeHints = true,
            },
          },
          typescript = {
            inlayHints = {
              includeInlayEnumMemberValueHints = true,
              includeInlayFunctionLikeReturnTypeHints = true,
              includeInlayFunctionParameterTypeHints = true,
              includeInlayParameterNameHints = "all",
              includeInlayParameterNameHintsWhenArgumentMatchesName = true,
              includeInlayPropertyDeclarationTypeHints = true,
              includeInlayVariableTypeHints = true,
            },
          },
        },
      })

      vim.lsp.config("yamlls", {
        capabilities = capabilities,
        settings = {
          yaml = {
            schemaStore = {
              enable = true,
              url = "https://www.schemastore.org/api/json/catalog.json",
            },
          },
        },
      })

      for _, server in ipairs({
        "cssls",
        "vimls",
        "bashls",
        "dockerls",
        "jedi_language_server",
        "clangd",
        "zls",
        "rust_analyzer",
        "taplo",
        "eslint",
      }) do
        vim.lsp.config(server, {
          capabilities = capabilities,
        })
      end

      -- Roslyn (.NET). Overrides the diagnostics-refresh paths shipped by
      -- nvim-lspconfig's lsp/roslyn_ls.lua: roslyn 5.10 does not dynamically register
      -- a `diagnosticProvider`, so upstream's `vim.iter(...diagnosticProvider)` runs on
      -- nil and crashes on project init and on every save. These copies guard the nil.
      local roslyn_group =
        vim.api.nvim_create_augroup("user.roslyn_ls", { clear = true })

      --- Ask Roslyn to re-pull diagnostics for every attached buffer, once per
      --- dynamically-registered diagnostic provider. No-op when the server registered
      --- none (roslyn 5.10), which is what the upstream copy fails to handle.
      ---@param client vim.lsp.Client
      local function roslyn_refresh_diagnostics(client)
        local provider = vim.tbl_get(
          client,
          "dynamic_capabilities",
          "capabilities",
          "diagnosticProvider"
        )
        if not provider then
          return
        end

        local identifiers = vim
          .iter(provider)
          :map(function(cap)
            return cap.registerOptions.identifier
          end)
          :totable()

        for buf, _ in pairs(client.attached_buffers) do
          if vim.api.nvim_buf_is_loaded(buf) then
            for _, identifier in pairs(identifiers) do
              client:request(vim.lsp.protocol.Methods.textDocument_diagnostic, {
                identifier = identifier,
                textDocument = vim.lsp.util.make_text_document_params(buf),
              }, nil, buf)
            end
          end
        end
      end

      vim.lsp.config("roslyn_ls", {
        capabilities = capabilities,
        handlers = {
          ["workspace/projectInitializationComplete"] = function(_, _, ctx)
            vim.notify(
              "Roslyn project initialization complete",
              vim.log.levels.INFO,
              { title = "roslyn_ls" }
            )
            local client = assert(vim.lsp.get_client_by_id(ctx.client_id))
            roslyn_refresh_diagnostics(client)
            return vim.NIL
          end,
        },
        on_attach = function(client, bufnr)
          if
            vim.api.nvim_get_autocmds({ buffer = bufnr, group = roslyn_group })[1]
          then
            return
          end
          vim.api.nvim_create_autocmd({ "BufWritePost", "InsertLeave" }, {
            group = roslyn_group,
            buffer = bufnr,
            callback = function()
              roslyn_refresh_diagnostics(client)
            end,
            desc = "roslyn_ls: refresh diagnostics",
          })
        end,
      })

      vim.lsp.config("html", {
        capabilities = capabilities,
        filetypes = { "html", "templ", "htmlangular" },
      })

      vim.lsp.config("emmet_ls", {
        capabilities = capabilities,
        filetypes = { "html", "htmlangular", "css", "scss" },
      })

      vim.lsp.config("jsonls", {
        capabilities = capabilities,
        settings = {
          json = {
            schemas = require("schemastore").json.schemas(),
            validate = { enable = true },
          },
        },
      })

      -- Angular. No custom `cmd`: the shipped nvim-lspconfig angularls config builds
      -- ngserver's --tsProbeLocations/--ngProbeLocations from the project's own
      -- node_modules (and passes --angularCoreVersion), so it uses the workspace's
      -- TypeScript and Angular. Probing the global npm root instead breaks whenever
      -- the global TypeScript has dropped tsserverlibrary (removed in TS 7).
      vim.lsp.config("angularls", {
        capabilities = capabilities,
        --- Only attach inside a real Angular/Nx workspace. Without this, Neovim
        --- starts angularls in single-file mode for every TypeScript buffer (e.g. a
        --- Nest project), where ngserver has no workspace and crash-loops with
        --- exit code 1.
        ---@param bufnr integer
        ---@param on_dir fun(root_dir?: string)
        root_dir = function(bufnr, on_dir)
          local root = vim.fs.root(bufnr, { "angular.json", "nx.json" })
          if root then
            on_dir(root)
          end
        end,
      })

      -- Lua
      vim.lsp.config("lua_ls", {
        capabilities = capabilities,
        settings = {
          Lua = {
            completion = { callSnippet = "Replace" },
            telemetry = { enable = false },
            hint = { enable = true },
          },
        },
      })

      -- ======================
      -- ENABLE SERVERS
      -- ======================

      vim.lsp.enable({
        "ts_ls",
        "yamlls",
        "cssls",
        "vimls",
        "html",
        "emmet_ls",
        "jsonls",
        "bashls",
        "dockerls",
        "jedi_language_server",
        "clangd",
        "zls",
        "angularls",
        "lua_ls",
        "rust_analyzer",
        "taplo",
        "roslyn_ls",
        "ansiblels",
        "eslint",
      })

      -- ======================
      -- DIAGNOSTICS
      -- ======================

      local float_config = {
        focusable = false,
        style = "minimal",
        border = "rounded",
        source = "always",
        header = "",
        prefix = "",
      }

      local diagnostic_icons = require("user.icons").diagnostics

      vim.diagnostic.config({
        underline = true,
        update_in_insert = false,
        -- Neither inline form: the message is shown in the bordered float, which
        -- [d/]d open on arrival and <leader>gl opens on demand.
        virtual_text = false,
        virtual_lines = false,
        severity_sort = true,
        float = float_config,
        signs = {
          text = {
            [vim.diagnostic.severity.ERROR] = diagnostic_icons.Error,
            [vim.diagnostic.severity.WARN] = diagnostic_icons.Warning,
            [vim.diagnostic.severity.INFO] = diagnostic_icons.Information,
            [vim.diagnostic.severity.HINT] = diagnostic_icons.Hint,
          },
        },
      })

      vim.lsp.handlers[ms.textDocument_hover] =
        vim.lsp.with(vim.lsp.handlers.hover, float_config)
      vim.lsp.handlers[ms.textDocument_signatureHelp] =
        vim.lsp.with(vim.lsp.handlers.signature_help, float_config)

      vim.hl.priorities.semantic_tokens = 95
    end,
  },
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
    -- Lazy on its keymaps: neotest runs nothing until a test is run or the
    -- summary is opened, so it owns no passive background work.
    keys = {
      lazy_key("<leader>tt", function()
        require("neotest").run.run()
      end, "Run nearest test"),
      lazy_key("<leader>tf", function()
        require("neotest").run.run(vim.fn.expand("%"))
      end, "Run file tests"),
      lazy_key("<leader>td", function()
        require("neotest").run.run({ strategy = "dap" })
      end, "Debug nearest test"),
      lazy_key("<leader>tl", function()
        require("neotest").run.run_last()
      end, "Run last test"),
      lazy_key("<leader>ts", function()
        require("neotest").summary.toggle()
      end, "Toggle test summary"),
      lazy_key("<leader>to", function()
        require("neotest").output.open({ enter = true, auto_close = true })
      end, "Show test output"),
      lazy_key("<leader>tw", function()
        require("neotest").watch.toggle(vim.fn.expand("%"))
      end, "Toggle test watch"),
      lazy_key("[T", function()
        require("neotest").jump.prev({ status = "failed" })
      end, "Previous failed test"),
      lazy_key("]T", function()
        require("neotest").jump.next({ status = "failed" })
      end, "Next failed test"),
    },
    config = function()
      -- must be in package.loaded before neotest's client initializes, so its
      -- ts filetype mapping reaches the parse subprocess (see the module docs)
      require("neotest-filetype-fix")

      require("neotest").setup({
        adapters = {
          require("neotest-jest")({
            jestCommand = "npm test --",
            env = { CI = true },
            --- Resolve the working directory for a test run.
            ---@return string cwd Project root to run jest from
            cwd = function()
              return vim.fn.getcwd()
            end,
          }),
        },
      })
    end,
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
    -- Only for filetypes no enabled LSP already lints. eslint, bashls (shellcheck),
    -- roslyn_ls, lua_ls and ansiblels (ansible-lint) cover the rest; duplicating them
    -- here would double every diagnostic.
    "mfussenegger/nvim-lint",
    event = { "BufReadPost", "BufWritePost" },
    config = function()
      local lint = require("lint")
      lint.linters_by_ft = {
        python = { "pylint" },
        dockerfile = { "hadolint" },
        markdown = { "markdownlint-cli2" },
        yaml = { "yamllint" },
      }
      vim.api.nvim_create_autocmd({ "BufReadPost", "BufWritePost" }, {
        group = vim.api.nvim_create_augroup("user_nvim_lint", { clear = true }),
        callback = function()
          lint.try_lint()
        end,
      })
      -- The lazy event that loaded this plugin has already fired for the current
      -- buffer, so the autocmd above would not see it until the next write.
      -- Scheduled because filetype is not set yet while that event is in flight.
      vim.schedule(function()
        lint.try_lint()
      end)
    end,
  },
  {
    "hrsh7th/nvim-cmp",
    -- CmdlineEnter as well as InsertEnter: the `:` and `/` completions below are
    -- unreachable if the plugin only wakes up for insert mode.
    event = { "InsertEnter", "CmdlineEnter" },
    dependencies = {
      "hrsh7th/cmp-buffer",
      "hrsh7th/cmp-path",
      "hrsh7th/cmp-cmdline",
      "hrsh7th/cmp-nvim-lsp",
      "hrsh7th/cmp-nvim-lsp-signature-help",
      "L3MON4D3/LuaSnip",
      "saadparwaiz1/cmp_luasnip",
    },
    config = function()
      local cmp = require("cmp")
      local luasnip = require("luasnip")
      local cmp_select_opts = { behavior = cmp.SelectBehavior.Select }

      cmp.setup({
        snippet = {
          expand = function(args)
            luasnip.lsp_expand(args.body)
          end,
        },
        window = {
          documentation = cmp.config.window.bordered(),
          completion = {
            winhighlight = "Normal:Pmenu,FloatBorder:Pmenu,CursorLine:PmenuSel,Search:None",
            col_offset = -3,
            side_padding = 0,
          },
        },
        view = {
          entries = {
            name = "custom",
            selection_order = "top_down",
          },
        },
        completion = {
          keyword_length = 3,
        },
        mapping = cmp.mapping.preset.insert({
          ["<C-u>"] = cmp.mapping.scroll_docs(-4),
          ["<C-d>"] = cmp.mapping.scroll_docs(4),
          ["<C-Space>"] = cmp.mapping.complete({}),
          ["<C-e>"] = cmp.mapping.abort(),
          ["<C-y>"] = cmp.mapping.confirm({
            behavior = cmp.ConfirmBehavior.Replace,
            select = true,
          }, { "i", "c" }),
          ["<Up>"] = cmp.mapping.select_prev_item(cmp_select_opts),
          ["<Down>"] = cmp.mapping.select_next_item(cmp_select_opts),
          ["<C-p>"] = cmp.mapping(function()
            if cmp.visible() then
              cmp.select_prev_item(cmp_select_opts)
            else
              cmp.complete()
            end
          end),
          ["<C-n>"] = cmp.mapping(function()
            if cmp.visible() then
              cmp.select_next_item(cmp_select_opts)
            else
              cmp.complete()
            end
          end),
        }),
        formatting = {
          fields = { "kind", "abbr", "menu" },
          format = function(_, item)
            local icons = require("user.icons").kind
            if icons[item.kind] then
              item.kind = icons[item.kind] .. " " .. item.kind
            end
            local strings = vim.split(item.kind, "%s", {
              trimempty = true,
            })
            item.kind = " " .. strings[1] .. " "
            if #strings > 1 then
              item.menu = "    (" .. strings[2] .. ")"
            end
            return item
          end,
        },
        sources = cmp.config.sources({
          { name = "nvim_lsp_signature_help" },
          { name = "nvim_lsp" },
          {
            name = "luasnip",
            keyword_length = 2,
            priority = 50,
          },
        }, {
          {
            name = "buffer",
            keyword_length = 5,
          },
          { name = "path" },
        }),
        experimental = {
          native_menu = false,
          ghost_text = false,
        },
      })

      cmp.setup.filetype({ "sql" }, {
        sources = {
          { name = "vim-dadbod-completion" },
          { name = "buffer" },
        },
      })

      cmp.setup.cmdline(":", {
        mapping = cmp.mapping.preset.cmdline(),
        sources = cmp.config.sources({
          {
            name = "cmdline",
            option = {
              ignore_cmds = { "Man", "!" },
            },
          },
        }, {
          { name = "path" },
        }),
      })

      cmp.setup.cmdline({ "/", "?" }, {
        mapping = cmp.mapping.preset.cmdline(),
        sources = {
          { name = "buffer" },
        },
      })

      local cmp_autopairs = require("nvim-autopairs.completion.cmp")
      cmp.event:on("confirm_done", cmp_autopairs.on_confirm_done())
    end,
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
    "L3MON4D3/LuaSnip",
    config = function()
      require("luasnip").setup({
        -- Without these, pressing Tab in insert mode after accepting a completion jumps
        -- the caret back into the snippet that was already accepted.
        region_check_events = "InsertEnter",
        delete_check_events = "InsertLeave",
      })
      require("luasnip.loaders.from_vscode").lazy_load()
    end,
  },
  { "rafamadriz/friendly-snippets" },
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
    -- textobjects and endwise register themselves into nvim-treesitter's config, so they are
    -- dependencies rather than siblings: as siblings, `configs.setup` below could run before
    -- either had loaded, silently dropping the textobject maps and the endwise rules.
    "nvim-treesitter/nvim-treesitter",
    build = ":TSUpdate",
    dependencies = {
      "nvim-treesitter/nvim-treesitter-textobjects",
      "RRethy/nvim-treesitter-endwise",
    },
    main = "nvim-treesitter.configs",
    opts = {
      highlight = {
        enable = true,
      },
      indent = {
        enable = true,
      },
      endwise = {
        enable = true,
      },
      autopairs = {
        enable = true,
      },
      context_commentstring = {
        enable = true,
        enable_autocmd = false,
      },
      incremental_selection = {
        enable = true,
        keymaps = {
          init_selection = "<C-space>", -- maps in normal mode to init the node/scope selection with ctrl+space
          node_incremental = "<C-space>", -- increment to the upper named parent
          node_decremental = "<bs>", -- decrement to the previous node
          scope_incremental = "<noop>", -- increment to the upper scope (as defined in locals.scm)
        },
      },
      auto_install = false,
      ensure_installed = {
        "angular",
        "bash",
        "c_sharp",
        "css",
        "dockerfile",
        "graphql",
        "html",
        "http",
        "javascript",
        "jsdoc",
        "json",
        "jsonc",
        "lua",
        "markdown",
        "markdown_inline",
        "python",
        "regex",
        "rust",
        "scss",
        "sql",
        "tsx",
        "typescript",
        "vim",
        "vimdoc",
        "yaml",
        "zig",
      },
      textobjects = {
        enable = true,
        lookahead = true,
        swap = {
          enable = true,
          swap_next = {
            ["<leader>a"] = "@parameter.inner",
          },
          swap_previous = {
            ["<leader>A"] = "@parameter.inner",
          },
        },
        move = {
          enable = true,
          set_jumps = true,
          goto_next_start = {
            ["]f"] = "@function.outer",
            ["]c"] = "@class.outer",
            ["]a"] = "@parameter.outer",
          },
          goto_next_end = {
            ["]F"] = "@function.outer",
            ["]C"] = "@class.outer",
            ["]A"] = "@parameter.outer",
          },
          goto_previous_start = {
            ["[f"] = "@function.outer",
            ["[c"] = "@class.outer",
            ["[a"] = "@parameter.outer",
          },
          goto_previous_end = {
            ["[F"] = "@function.outer",
            ["[C"] = "@class.outer",
            ["[A"] = "@parameter.outer",
          },
        },
        select = {
          enable = true,
          keymaps = {
            ["af"] = "@function.outer",
            ["if"] = "@function.inner",

            ["ac"] = "@conditional.outer",
            ["ic"] = "@conditional.inner",

            ["aa"] = "@parameter.outer",
            ["ia"] = "@parameter.inner",

            ["av"] = "@variable.outer",
            ["iv"] = "@variable.inner",
          },
        },
      },
    },
  },
  {
    "nvim-treesitter/nvim-treesitter-context",
    main = "treesitter-context",
    opts = {
      multiline_threshold = 1,
    },
  },
  {
    "akinsho/bufferline.nvim",
    version = "*",
    dependencies = "nvim-tree/nvim-web-devicons",
    config = function()
      require("bufferline").setup()
    end,
  },
  {
    "iamcco/markdown-preview.nvim",
    cmd = { "MarkdownPreviewToggle", "MarkdownPreview", "MarkdownPreviewStop" },
    ft = { "markdown" },
    build = ":call mkdp#util#install()",
  },
  {
    "catgoose/nvim-colorizer.lua",
    config = function()
      require("colorizer").setup()
    end,
  },
  {
    -- Replaces neodev, which hooked lspconfig's lua_ls.setup() and so never
    -- applied to the native vim.lsp.config wiring this config uses.
    "folke/lazydev.nvim",
    ft = "lua", -- only load on lua files
    opts = {},
  },
  {
    "stevearc/oil.nvim",
    -- oil prefers mini.icons but falls back to nvim-web-devicons, which lualine
    -- and bufferline already load; one icon set, one provider.
    dependencies = { "nvim-tree/nvim-web-devicons" },
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
