local M = {}

--- Add a buffer-local normal keymap.
---@param lhs string Keymap
---@param rhs function Action
---@param bufnr number Buffer number
---@param desc string which-key description
local keymap = function(lhs, rhs, bufnr, desc)
  vim.keymap.set("n", lhs, rhs, {
    noremap = true,
    silent = true,
    buffer = bufnr,
    desc = desc,
  })
end

--- On attach for key maps.
---@param bufnr number Buffer number
M.on_attach = function(bufnr)
  local builtin = require("telescope.builtin")
  keymap("gd", builtin.lsp_definitions, bufnr, "Go to definition")
  keymap("gr", builtin.lsp_references, bufnr, "References")
  keymap("<leader>ls", builtin.lsp_document_symbols, bufnr, "Document symbols")
  keymap(
    "<leader>lS",
    builtin.lsp_dynamic_workspace_symbols,
    bufnr,
    "Workspace symbols"
  )
  keymap("gs", vim.lsp.buf.signature_help, bufnr, "Signature help")
  keymap("gi", builtin.lsp_implementations, bufnr, "Implementations")
  keymap("gD", vim.lsp.buf.declaration, bufnr, "Go to declaration")
  keymap("K", vim.lsp.buf.hover, bufnr, "Hover docs")
  keymap("<leader>D", builtin.lsp_type_definitions, bufnr, "Type definition")
  keymap("<leader>cl", vim.lsp.codelens.run, bufnr, "Run code lens")
  keymap("<leader>rn", vim.lsp.buf.rename, bufnr, "Rename symbol")
  keymap("<leader>ca", vim.lsp.buf.code_action, bufnr, "Code action")
  keymap("<leader>gl", vim.diagnostic.open_float, bufnr, "Line diagnostics")
  keymap("[d", function()
    vim.diagnostic.goto_prev()
    vim.cmd("norm zz")
  end, bufnr, "Previous diagnostic")
  keymap("]d", function()
    vim.diagnostic.goto_next()
    vim.cmd("norm zz")
  end, bufnr, "Next diagnostic")

  keymap("<leader>v", function()
    vim.cmd("vsplit | lua vim.lsp.buf.definition()")
    vim.cmd("norm zz")
  end, bufnr, "Definition in vsplit")
end

return M
