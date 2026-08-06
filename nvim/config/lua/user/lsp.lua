local ms = require("vim.lsp.protocol").Methods
local cmp_capabilities = require("cmp_nvim_lsp").default_capabilities()
require("lsp_autocommands").setup()

-- capabilities
local capabilities = vim.lsp.protocol.make_client_capabilities()
capabilities = vim.tbl_deep_extend("force", capabilities, cmp_capabilities)
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

vim.diagnostic.config({
  underline = true,
  update_in_insert = false,
  virtual_text = false,
  severity_sort = true,
  float = float_config,
})

vim.lsp.handlers[ms.textDocument_hover] =
  vim.lsp.with(vim.lsp.handlers.hover, float_config)
vim.lsp.handlers[ms.textDocument_signatureHelp] =
  vim.lsp.with(vim.lsp.handlers.signature_help, float_config)

vim.hl.priorities.semantic_tokens = 95

-- diagnostic signs
for name, icon in pairs(require("user.icons").diagnostics) do
  local sign = "DiagnosticSign" .. name
  vim.fn.sign_define(sign, { text = icon, texthl = sign, numhl = "" })
end
