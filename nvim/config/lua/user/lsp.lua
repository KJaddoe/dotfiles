local ms = require("vim.lsp.protocol").Methods
local cmp_capabilities = require("cmp_nvim_lsp").default_capabilities()
local keymaps = require("lsp_keymaps")
require("lsp_autocommands").setup()

local capabilities = vim.lsp.protocol.make_client_capabilities()
capabilities = vim.tbl_deep_extend("force", capabilities, cmp_capabilities)
capabilities = vim.tbl_deep_extend("force", capabilities, {
  workspace = {
    didChangeWatchedFiles = {
      dynamicRegistration = true, -- needs fswatch on linux
      relativePatternSupport = true,
    },
  },
})

---@param client vim.lsp.Client LSP client
---@param bufnr number Buffer number
---@diagnostic disable: unused-local
local on_attach = function(client, bufnr)
  keymaps.on_attach(bufnr)
end

local lspconfig = require("lspconfig")
require("lspconfig.ui.windows").default_options.border = "rounded"

lspconfig.tsserver.setup({
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

lspconfig.yamlls.setup({
  capabilities = capabilities,
  on_attach = on_attach,
  settings = {
    yaml = {
      schemaStore = {
        url = "https://www.schemastore.org/api/json/catalog.json",
        enable = true,
      },
    },
  },
})

lspconfig.cssls.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.vimls.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.html.setup({
  capabilities = capabilities,
  on_attach = on_attach,
  cmd = { "html-languageserver", "--stdio" },
})

lspconfig.jsonls.setup({
  capabilities = capabilities,
  on_attach = on_attach,
  cmd = { "json-languageserver", "--stdio" },
})

lspconfig.bashls.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.pylsp.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.dockerls.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.jedi_language_server.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.clangd.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.zls.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.angularls.setup {
  on_attach = on_attach,
  capabilities = capabilities,
}

-- Make runtime files discoverable to the server
local runtime_path = vim.split(package.path, ";", {})
table.insert(runtime_path, "lua/?.lua")
table.insert(runtime_path, "lua/?/init.lua")
lspconfig.lua_ls.setup({
  capabilities = capabilities,
  on_attach = on_attach,
  settings = {
    Lua = {
      completion = {
        callSnippet = "Replace",
      },
      telemetry = { enable = false },
      hint = {
        enable = true,
      },
    },
  },
})

lspconfig.rust_analyzer.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

lspconfig.taplo.setup({
  capabilities = capabilities,
  on_attach = on_attach,
})

local float_config = {
  focusable = false,
  style = "minimal",
  border = "rounded",
  source = "always",
  header = "",
  prefix = "",
}

-- setup diagnostics
vim.diagnostic.config({
  underline = true,
  update_in_insert = false,
  virtual_text = false, --{ spacing = 4, prefix = "●" },
  severity_sort = true,
  float = float_config,
})

vim.lsp.handlers[ms.textDocument_hover] = vim.lsp.with(vim.lsp.handlers.hover, float_config)
vim.lsp.handlers[ms.textDocument_signatureHelp] = vim.lsp.with(vim.lsp.handlers.signature_help, float_config)
vim.highlight.priorities.semantic_tokens = 95

-- set up diagnostic signs
for name, icon in pairs(require("user.icons").diagnostics) do
  name = "DiagnosticSign" .. name
  vim.fn.sign_define(name, { text = icon, texthl = name, numhl = "" })
end
