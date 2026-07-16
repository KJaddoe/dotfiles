local dap = require("dap")
local dapui = require("dapui")

-- js-debug (vscode-js-debug) DAP server, installed by the neovim ansible role
local js_debug_path =
  vim.fn.expand("~/.local/share/js-debug/src/dapDebugServer.js")

for _, adapter in ipairs({ "pwa-node", "pwa-chrome" }) do
  dap.adapters[adapter] = {
    type = "server",
    host = "localhost",
    port = "${port}",
    executable = {
      command = "node",
      args = { js_debug_path, "${port}" },
    },
  }
end

for _, language in ipairs({ "typescript", "javascript" }) do
  dap.configurations[language] = {
    {
      type = "pwa-node",
      request = "launch",
      name = "Launch current file",
      program = "${file}",
      cwd = "${workspaceFolder}",
      sourceMaps = true,
      skipFiles = { "<node_internals>/**" },
    },
    {
      type = "pwa-node",
      request = "attach",
      name = "Attach to Node --inspect (9229)",
      port = 9229,
      restart = true,
      cwd = "${workspaceFolder}",
      sourceMaps = true,
      skipFiles = { "<node_internals>/**" },
    },
    {
      type = "pwa-node",
      request = "attach",
      name = "Attach to process",
      processId = require("dap.utils").pick_process,
      cwd = "${workspaceFolder}",
      sourceMaps = true,
      skipFiles = { "<node_internals>/**" },
    },
    {
      type = "pwa-chrome",
      request = "launch",
      name = "Launch Chrome against localhost:4200 (ng serve)",
      url = "http://localhost:4200",
      webRoot = "${workspaceFolder}",
      sourceMaps = true,
    },
  }
end

dapui.setup()

dap.listeners.after.event_initialized["dapui_config"] = function()
  dapui.open()
end
dap.listeners.before.event_terminated["dapui_config"] = function()
  dapui.close()
end
dap.listeners.before.event_exited["dapui_config"] = function()
  dapui.close()
end

local opts = { noremap = true, silent = true }
local keymap = vim.keymap.set

keymap("n", "<leader>xb", dap.toggle_breakpoint, opts)
keymap("n", "<leader>xB", function()
  dap.set_breakpoint(vim.fn.input("Breakpoint condition: "))
end, opts)
keymap("n", "<leader>xc", dap.continue, opts)
keymap("n", "<leader>xi", dap.step_into, opts)
keymap("n", "<leader>xo", dap.step_over, opts)
keymap("n", "<leader>xO", dap.step_out, opts)
keymap("n", "<leader>xr", dap.repl.toggle, opts)
keymap("n", "<leader>xt", dap.terminate, opts)
keymap("n", "<leader>xu", dapui.toggle, opts)
keymap("n", "<leader>xk", function()
  require("dapui").eval()
end, opts)
