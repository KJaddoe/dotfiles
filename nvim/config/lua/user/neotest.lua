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

local opts = { noremap = true, silent = true }
local keymap = vim.keymap.set

keymap("n", "<leader>tt", function()
  neotest.run.run()
end, opts)
keymap("n", "<leader>tf", function()
  neotest.run.run(vim.fn.expand("%"))
end, opts)
keymap("n", "<leader>td", function()
  neotest.run.run({ strategy = "dap" })
end, opts)
keymap("n", "<leader>tl", function()
  neotest.run.run_last()
end, opts)
keymap("n", "<leader>ts", function()
  neotest.summary.toggle()
end, opts)
keymap("n", "<leader>to", function()
  neotest.output.open({ enter = true, auto_close = true })
end, opts)
keymap("n", "<leader>tw", function()
  neotest.watch.toggle(vim.fn.expand("%"))
end, opts)
keymap("n", "[T", function()
  neotest.jump.prev({ status = "failed" })
end, opts)
keymap("n", "]T", function()
  neotest.jump.next({ status = "failed" })
end, opts)
