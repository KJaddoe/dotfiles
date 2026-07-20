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

-- netcoredbg (.NET), installed by the neovim ansible role
dap.adapters.coreclr = {
  type = "executable",
  command = "netcoredbg",
  args = { "--interpreter=vscode" },
}

--- Find the nearest ancestor directory of the current buffer that holds a file
--- matching `pattern` (e.g. a `.csproj` or `.sln`).
---@param pattern string Lua pattern a filename in the directory must match
---@return string|nil dir Absolute directory, or nil when none is found upward
local function nearest_root(pattern)
  return vim.fs.root(0, function(fname)
    return fname:match(pattern) ~= nil
  end)
end

--- Locate the built, debuggable assembly for the current .NET solution.
---
--- A runnable app (not a class library) ships a sibling
--- `<name>.runtimeconfig.json`, so we scan the solution's Debug output for
--- those and keep only assemblies whose name matches their owning project
--- folder — which drops copied dependencies and tooling such as roslyn's
--- BuildHost. Test assemblies are skipped, the app the current buffer belongs
--- to wins, and we prompt only when several candidates still remain.
---@return string|nil program Absolute path to the dll, or nil when none is built
local function find_dotnet_dll()
  local root = nearest_root("%.sln[x]?$")
    or nearest_root("%.csproj$")
    or vim.fn.getcwd()

  local configs = vim.fs.find(function(name, path)
    return name:match("%.runtimeconfig%.json$") ~= nil
      and path:match("[/\\]bin[/\\]Debug[/\\]") ~= nil
  end, { path = root, type = "file", limit = 100 })

  local dlls = {}
  for _, cfg in ipairs(configs) do
    local dll = cfg:gsub("%.runtimeconfig%.json$", ".dll")
    local project_dir = dll:match("^(.*)/bin/")
    local project = project_dir and vim.fs.basename(project_dir)
    local name = vim.fs.basename(dll):gsub("%.dll$", "")
    if
      vim.uv.fs_stat(dll)
      and project == name
      and not name:match("[Tt]ests?$")
    then
      table.insert(dlls, dll)
    end
  end

  if #dlls == 0 then
    vim.notify(
      "dap: no built .NET app under " .. root .. " (run dotnet build?)",
      vim.log.levels.WARN,
      { title = "dap" }
    )
    return nil
  end

  local buffer_project = nearest_root("%.csproj$")
  if buffer_project then
    for _, dll in ipairs(dlls) do
      if vim.startswith(dll, buffer_project .. "/") then
        return dll
      end
    end
  end

  if #dlls == 1 then
    return dlls[1]
  end

  -- dap resolves configs inside a coroutine, so vim.ui.select can yield.
  local co = coroutine.running()
  vim.ui.select(dlls, {
    prompt = "Select .NET assembly to debug",
    format_item = function(dll)
      return vim.fn.fnamemodify(dll, ":.")
    end,
  }, function(choice)
    coroutine.resume(co, choice)
  end)
  return coroutine.yield()
end

dap.configurations.cs = {
  {
    type = "coreclr",
    request = "launch",
    name = "Launch .NET assembly",
    program = find_dotnet_dll,
    --- Run from the owning project directory so ASP.NET resolves appsettings
    --- and content-root relative paths as it would under `dotnet run`.
    cwd = function()
      return nearest_root("%.csproj$") or vim.fn.getcwd()
    end,
    --- Launching the dll directly bypasses launchSettings.json, so ASP.NET
    --- binds Kestrel's default port. Forward ASPNETCORE_URLS/ENVIRONMENT from
    --- the shell when set (e.g. `export ASPNETCORE_URLS=http://localhost:5179`
    --- to match a frontend proxy) -- nil values drop out, leaving defaults.
    env = {
      ASPNETCORE_URLS = vim.env.ASPNETCORE_URLS,
      ASPNETCORE_ENVIRONMENT = vim.env.ASPNETCORE_ENVIRONMENT,
    },
  },
  {
    type = "coreclr",
    request = "attach",
    name = "Attach to process",
    processId = require("dap.utils").pick_process,
  },
}

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
