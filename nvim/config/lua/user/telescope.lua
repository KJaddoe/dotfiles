--- Telescope actions that open every entry in a multi-selection, rather than
--- only the entry under the cursor.
---
--- A pure helper module in the shape of user.search: it is required on demand
--- from the Telescope keymaps instead of at startup, so lazy.nvim can keep
--- telescope itself unloaded until a picker is actually opened.
local M = {}

--- Open every selected entry, falling back to the entry under the cursor when
--- nothing is multi-selected.
---@param prompt_bufnr integer Telescope prompt buffer
---@param open_cmd string Command opening the entries ("edit", "split", "vsplit" or "tabedit")
local function open_selection(prompt_bufnr, open_cmd)
  local actions = require("telescope.actions")
  local action_state = require("telescope.actions.state")
  local picker = action_state.get_current_picker(prompt_bufnr)
  local multi = picker:get_multi_selection()
  local current = action_state.get_selected_entry()

  actions.close(prompt_bufnr)

  if vim.tbl_isempty(multi) then
    multi = { current }
  else
    table.insert(multi, current)
  end

  for i, entry in ipairs(multi) do
    if entry.path then
      if i == 1 then
        vim.cmd((open_cmd or "edit") .. " " .. entry.path)
      else
        if open_cmd == "split" then
          vim.cmd("split " .. entry.path)
        elseif open_cmd == "vsplit" then
          vim.cmd("vsplit " .. entry.path)
        elseif open_cmd == "tabedit" then
          vim.cmd("tabedit " .. entry.path)
        else
          vim.cmd("edit " .. entry.path)
        end
      end
    end
  end
end

--- Open the selection in the current window.
---@param prompt_bufnr integer Telescope prompt buffer
function M.edit(prompt_bufnr)
  open_selection(prompt_bufnr, "edit")
end

--- Open the selection in horizontal splits.
---@param prompt_bufnr integer Telescope prompt buffer
function M.split(prompt_bufnr)
  open_selection(prompt_bufnr, "split")
end

--- Open the selection in vertical splits.
---@param prompt_bufnr integer Telescope prompt buffer
function M.vsplit(prompt_bufnr)
  open_selection(prompt_bufnr, "vsplit")
end

--- Open the selection in new tabs.
---@param prompt_bufnr integer Telescope prompt buffer
function M.tabedit(prompt_bufnr)
  open_selection(prompt_bufnr, "tabedit")
end

return M
