local ms = require("vim.lsp.protocol").Methods
local cmp_capabilities = require("cmp_nvim_lsp").default_capabilities()
local keymaps = require("lsp_keymaps")
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

---@param client vim.lsp.Client
---@param bufnr number
local on_attach = function(client, bufnr)
  keymaps.on_attach(bufnr)
end

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
  on_attach = on_attach,
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
  on_attach = on_attach,
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
  "pylsp",
  "dockerls",
  "jedi_language_server",
  "clangd",
  "zls",
  "rust_analyzer",
  "taplo",
  "csharp_ls",
}) do
  vim.lsp.config(server, {
    capabilities = capabilities,
    on_attach = on_attach,
  })
end

vim.lsp.config("html", {
  capabilities = capabilities,
  on_attach = on_attach,
  cmd = { "html-languageserver", "--stdio" },
})

vim.lsp.config("jsonls", {
  capabilities = capabilities,
  on_attach = on_attach,
  cmd = { "json-languageserver", "--stdio" },
})

-- Angular
local function get_npm_global_root()
  local handle = io.popen("npm root -g")
  if not handle then
    return ""
  end
  local result = handle:read("*a")
  handle:close()
  return result:gsub("%s+$", "")
end

local project_library_path = get_npm_global_root()
local angular_cmd = {
  "ngserver",
  "--stdio",
  "--tsProbeLocations",
  project_library_path,
  "--ngProbeLocations",
  project_library_path,
}

vim.lsp.config("angularls", {
  capabilities = capabilities,
  on_attach = on_attach,
  cmd = angular_cmd,
  on_new_config = function(new_config)
    new_config.cmd = angular_cmd
  end,
})

-- Lua
vim.lsp.config("lua_ls", {
  capabilities = capabilities,
  on_attach = on_attach,
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
  "jsonls",
  "bashls",
  "pylsp",
  "dockerls",
  "jedi_language_server",
  "clangd",
  "zls",
  "angularls",
  "lua_ls",
  "rust_analyzer",
  "taplo",
  "csharp_ls",
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

vim.highlight.priorities.semantic_tokens = 95

-- diagnostic signs
for name, icon in pairs(require("user.icons").diagnostics) do
  local sign = "DiagnosticSign" .. name
  vim.fn.sign_define(sign, { text = icon, texthl = sign, numhl = "" })
end
