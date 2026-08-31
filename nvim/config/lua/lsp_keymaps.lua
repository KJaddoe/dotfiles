local M = {}

--- Add a buffer-local keymap.
---@param lhs string Keymap
---@param rhs function Action
---@param bufnr number Buffer number
---@param desc string which-key description
---@param mode? string|string[] Mode(s) to map in, normal by default
local keymap = function(lhs, rhs, bufnr, desc, mode)
  vim.keymap.set(mode or "n", lhs, rhs, {
    noremap = true,
    silent = true,
    buffer = bufnr,
    desc = desc,
  })
end

--- Whether any attached client advertises a code action kind. Source kinds are
--- server-specific, so the maps that request them only exist where they work.
---@param bufnr number Buffer number
---@param kind string Code action kind
---@return boolean
local advertises = function(bufnr, kind)
  for _, client in ipairs(vim.lsp.get_clients({ bufnr = bufnr })) do
    local provider = (client.server_capabilities or {}).codeActionProvider
    local kinds = type(provider) == "table" and provider.codeActionKinds or nil
    if kinds and vim.tbl_contains(kinds, kind) then
      return true
    end
  end
  return false
end

--- Request one source-kind code action and apply it. A plain code-action
--- request only offers what the cursor or selection resolves to, so source
--- actions such as fix-all never appear in that list.
---@param kind string Code action kind
---@return function
local source_action = function(kind)
  return function()
    vim.lsp.buf.code_action({
      context = { only = { kind }, diagnostics = {} },
      apply = true,
    })
  end
end

--- On attach for key maps.
---@param bufnr number Buffer number
M.on_attach = function(bufnr)
  local builtin = require("telescope.builtin")
  keymap("gd", builtin.lsp_definitions, bufnr, "Go to definition")
  -- Neovim 0.11 owns the gr* family globally, so a bare `gr` would be a prefix
  -- of grr/gri/grn/gra and stall for timeoutlen before firing. Use the built-in
  -- names and point them at telescope, which previews each result.
  keymap("grr", builtin.lsp_references, bufnr, "References")
  keymap("gri", builtin.lsp_implementations, bufnr, "Implementations")
  keymap("gy", builtin.lsp_type_definitions, bufnr, "Type definition")
  keymap("gD", vim.lsp.buf.declaration, bufnr, "Go to declaration")
  keymap("gs", vim.lsp.buf.signature_help, bufnr, "Signature help")
  keymap("K", vim.lsp.buf.hover, bufnr, "Hover docs")
  keymap("<leader>ls", builtin.lsp_document_symbols, bufnr, "Document symbols")
  keymap(
    "<leader>lS",
    builtin.lsp_dynamic_workspace_symbols,
    bufnr,
    "Workspace symbols"
  )
  keymap("<leader>li", builtin.lsp_incoming_calls, bufnr, "Incoming calls")
  keymap("<leader>lo", builtin.lsp_outgoing_calls, bufnr, "Outgoing calls")
  keymap("<leader>cl", vim.lsp.codelens.run, bufnr, "Run code lens")
  -- Rename and code action are Neovim's own grn and gra, which already cover
  -- normal and visual mode; the source-kind actions below have no built-in.

  for _, action in ipairs({
    { "<leader>cf", "source.fixAll.eslint", "Fix all (eslint)" },
    { "<leader>cm", "source.addMissingImports.ts", "Add missing imports" },
    { "<leader>cu", "source.removeUnusedImports.ts", "Remove unused imports" },
  }) do
    local lhs, kind, desc = action[1], action[2], action[3]
    if advertises(bufnr, kind) then
      keymap(lhs, source_action(kind), bufnr, desc)
    end
  end
  keymap("<leader>gl", vim.diagnostic.open_float, bufnr, "Line diagnostics")
  -- goto_prev/goto_next are deprecated and go away in nvim 0.13. The float is
  -- what shows the message: virtual_lines is off, see user.lsp.
  keymap("[d", function()
    vim.diagnostic.jump({ count = -1, float = true })
    vim.cmd("norm zz")
  end, bufnr, "Previous diagnostic")
  keymap("]d", function()
    vim.diagnostic.jump({ count = 1, float = true })
    vim.cmd("norm zz")
  end, bufnr, "Next diagnostic")

  keymap("<leader>v", function()
    vim.cmd("vsplit | lua vim.lsp.buf.definition()")
    vim.cmd("norm zz")
  end, bufnr, "Definition in vsplit")

  -- which-key does not surface the `g` prefix from its automatic trigger
  -- detection here, so name the group explicitly for this buffer.
  local ok, wk = pcall(require, "which-key")
  if ok then
    wk.add({ { "g", group = "Goto / LSP", buffer = bufnr } })
  end
end

return M
