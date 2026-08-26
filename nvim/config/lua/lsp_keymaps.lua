local ms = require("vim.lsp.protocol").Methods

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

--- Build position params for a client, honouring that client's offset encoding.
---@param client vim.lsp.Client
---@return table
local position_params = function(client)
  return vim.lsp.util.make_position_params(
    0,
    client.offset_encoding or "utf-16"
  )
end

--- Report whether any client attached to the buffer serves the method.
---@param bufnr number Buffer number
---@param method string LSP method
---@param label string Human name of the request, used in the warning
---@return boolean
local serves = function(bufnr, method, label)
  if #vim.lsp.get_clients({ bufnr = bufnr, method = method }) > 0 then
    return true
  end
  vim.notify(
    ("No attached language server provides %s."):format(label),
    vim.log.levels.WARN
  )
  return false
end

--- Open a trouble panel once a server is known to serve the request.
---@param mode string trouble mode name
---@param method string LSP method probed for support
---@param label string Human name of the request, used in messages
---@return function
local panel = function(mode, method, label)
  return function()
    local bufnr = vim.api.nvim_get_current_buf()
    if not serves(bufnr, method, label) then
      return
    end
    require("trouble").open({ mode = mode, focus = true })
  end
end

--- Count results that point somewhere other than the cursor itself. Servers
--- answer a location request on a concrete symbol with that symbol's own
--- position, which is not somewhere to navigate to.
---@param results table<integer, { result: any }>
---@param bufnr number Buffer number
---@return number
local elsewhere = function(results, bufnr)
  local here = vim.uri_from_bufnr(bufnr)
  local row = vim.api.nvim_win_get_cursor(0)[1] - 1
  local count = 0

  ---@param item table
  local visit = function(item)
    local uri = item.uri or item.targetUri
    local range = item.range or item.targetSelectionRange or item.targetRange
    if not uri then
      return
    end
    if uri == here and range and range.start.line == row then
      return
    end
    count = count + 1
  end

  for _, response in pairs(results or {}) do
    local result = response.result
    if type(result) == "table" then
      if result.uri or result.targetUri then
        visit(result)
      else
        for _, item in ipairs(result) do
          visit(item)
        end
      end
    end
  end

  return count
end

--- Open a trouble panel for a location request, but first check it returns
--- somewhere to go. Only for methods that answer with destinations:
--- `prepareCallHierarchy` answers with the symbol itself, which `elsewhere`
--- would discard, so call hierarchy uses `panel` instead.
--- LSP reports "nothing found" both when no server serves the method and when
--- the symbol genuinely has no results, which reads as a broken keymap; this
--- separates the two and explains the empty case instead of showing a bare panel.
---@param mode string trouble mode name
---@param method string LSP method probed for support and emptiness
---@param label string Human name of the request, used in messages
---@param hint string Explanation shown when the request returns no results
---@return function
local checked_panel = function(mode, method, label, hint)
  return function()
    local bufnr = vim.api.nvim_get_current_buf()
    if not serves(bufnr, method, label) then
      return
    end
    vim.lsp.buf_request_all(bufnr, method, position_params, function(results)
      if elsewhere(results, bufnr) == 0 then
        vim.notify(hint, vim.log.levels.INFO)
        return
      end
      require("trouble").open({ mode = mode, focus = true })
    end)
  end
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
  keymap(
    "gr",
    panel("lsp_references", ms.textDocument_references, "references"),
    bufnr,
    "References"
  )
  keymap(
    "gi",
    checked_panel(
      "lsp_implementations",
      ms.textDocument_implementation,
      "implementations",
      "No implementations: only interfaces and abstract or virtual members have them."
    ),
    bufnr,
    "Implementations"
  )
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
  keymap(
    "<leader>li",
    panel(
      "lsp_incoming_calls",
      ms.textDocument_prepareCallHierarchy,
      "call hierarchy"
    ),
    bufnr,
    "Incoming calls"
  )
  keymap(
    "<leader>lo",
    panel(
      "lsp_outgoing_calls",
      ms.textDocument_prepareCallHierarchy,
      "call hierarchy"
    ),
    bufnr,
    "Outgoing calls"
  )
  keymap("<leader>lf", function()
    require("trouble").open({ mode = "lsp", focus = true })
  end, bufnr, "LSP finder (all)")
  keymap("<leader>cl", vim.lsp.codelens.run, bufnr, "Run code lens")
  keymap("<leader>rn", vim.lsp.buf.rename, bufnr, "Rename symbol")
  -- Visual mode too: TypeScript's extract refactors are only offered for a
  -- selected range, so a normal-mode-only map cannot reach them at all.
  keymap(
    "<leader>ca",
    vim.lsp.buf.code_action,
    bufnr,
    "Code action",
    { "n", "v" }
  )

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
  -- goto_prev/goto_next are deprecated and go away in nvim 0.13. No float: the
  -- current-line virtual_lines already shows the message on arrival.
  keymap("[d", function()
    vim.diagnostic.jump({ count = -1, float = false })
    vim.cmd("norm zz")
  end, bufnr, "Previous diagnostic")
  keymap("]d", function()
    vim.diagnostic.jump({ count = 1, float = false })
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
