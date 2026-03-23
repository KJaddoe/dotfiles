local telescope = require("telescope")

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

local select_one_or_multi = function(prompt_bufnr)
  open_selection(prompt_bufnr, "edit")
end
local select_one_or_multi_split = function(prompt_bufnr)
  open_selection(prompt_bufnr, "split")
end
local select_one_or_multi_vsplit = function(prompt_bufnr)
  open_selection(prompt_bufnr, "vsplit")
end
local select_one_or_multi_tabedit = function(prompt_bufnr)
  open_selection(prompt_bufnr, "tabedit")
end

telescope.load_extension("gh")
telescope.load_extension("harpoon")

local opts = { noremap = true, silent = true }
local builtin = require("telescope.builtin")

vim.keymap.set("n", "<c-p>", function()
  builtin.find_files({
    find_command = {
      "rg",
      "--hidden",
      "--files",
      "--smart-case",
      "--glob=!.git",
    },
    attach_mappings = function(_, map)
      map("i", "<cr>", select_one_or_multi)
      map("i", "<c-x>", select_one_or_multi_split)
      map("i", "<c-v>", select_one_or_multi_vsplit)
      map("i", "<c-t>", select_one_or_multi_tabedit)
      return true
    end,
  })
end, opts)

vim.keymap.set("n", "<leader>fb", function()
  builtin.buffers({
    attach_mappings = function(_, map)
      map("i", "<cr>", select_one_or_multi)
      map("i", "<c-x>", select_one_or_multi_split)
      map("i", "<c-v>", select_one_or_multi_vsplit)
      map("i", "<c-t>", select_one_or_multi_tabedit)
      map("i", "<c-d>", "delete_buffer")
      return true
    end,
  })
end, opts)

vim.keymap.set("n", "<leader>of", function()
  builtin.oldfiles({
    only_cwd = true,
    attach_mappings = function(_, map)
      map("i", "<cr>", select_one_or_multi)
      map("i", "<c-x>", select_one_or_multi_split)
      map("i", "<c-v>", select_one_or_multi_vsplit)
      map("i", "<c-t>", select_one_or_multi_tabedit)
      return true
    end,
  })
end, opts)

vim.keymap.set("n", "<leader>lg", builtin.live_grep, opts)
vim.keymap.set("n", "<leader>fh", builtin.help_tags, opts)
vim.keymap.set("n", "<leader>fc", builtin.commands, opts)
vim.keymap.set("n", "<leader>fr", builtin.resume, opts)
vim.keymap.set("n", "<leader>fq", builtin.quickfix, opts)
vim.keymap.set("n", "<leader>/", builtin.current_buffer_fuzzy_find, opts)
vim.keymap.set("n", "<leader>xx", builtin.diagnostics, opts)
vim.keymap.set("n", "<leader>ghi", telescope.extensions.gh.issues, opts)
vim.keymap.set("n", "<leader>fj", telescope.extensions.harpoon.marks, opts)
