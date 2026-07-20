-- must be in package.loaded before neotest's client initializes, so its
-- ts filetype mapping reaches the parse subprocess (see the module docs)
require("neotest-filetype-fix")

local neotest = require("neotest")

neotest.setup({
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

--- Add a normal-mode test keymap.
---@param lhs string Keymap
---@param rhs function Action
---@param desc string which-key description
local function map(lhs, rhs, desc)
  vim.keymap.set("n", lhs, rhs, { noremap = true, silent = true, desc = desc })
end

map("<leader>tt", function()
  neotest.run.run()
end, "Run nearest test")
map("<leader>tf", function()
  neotest.run.run(vim.fn.expand("%"))
end, "Run file tests")
map("<leader>td", function()
  neotest.run.run({ strategy = "dap" })
end, "Debug nearest test")
map("<leader>tl", function()
  neotest.run.run_last()
end, "Run last test")
map("<leader>ts", function()
  neotest.summary.toggle()
end, "Toggle test summary")
map("<leader>to", function()
  neotest.output.open({ enter = true, auto_close = true })
end, "Show test output")
map("<leader>tw", function()
  neotest.watch.toggle(vim.fn.expand("%"))
end, "Toggle test watch")
map("[T", function()
  neotest.jump.prev({ status = "failed" })
end, "Previous failed test")
map("]T", function()
  neotest.jump.next({ status = "failed" })
end, "Next failed test")
