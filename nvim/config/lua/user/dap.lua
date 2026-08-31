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
--- folder, which drops copied dependencies and tooling such as roslyn's
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

--- Read the environment a project's launch profile defines.
---
--- Rider and Visual Studio start a project through the first `commandName ==
--- "Project"` profile in `Properties/launchSettings.json`, which is where
--- `ASPNETCORE_ENVIRONMENT` and the application URLs live. Debugging the built
--- dll bypasses that file, so without this the app boots as Production (no
--- `appsettings.Development.json` and therefore no dev connection strings) on
--- Kestrel's default port 5000, which on macOS also collides with Control
--- Centre's AirPlay receiver.
---@param project_dir string Directory holding the `.csproj`
---@return table<string, string> env Variables the profile sets, empty when it defines none
local function launch_profile_env(project_dir)
  local file = io.open(project_dir .. "/Properties/launchSettings.json", "r")
  if not file then
    return {}
  end
  local content = file:read("*a")
  file:close()

  local ok, settings = pcall(vim.json.decode, content)
  if
    not ok
    or type(settings) ~= "table"
    or type(settings.profiles) ~= "table"
  then
    return {}
  end

  -- vim.json.decode drops JSON object order, so pick by sorted name to keep the
  -- same profile winning on every launch.
  local names = vim.tbl_keys(settings.profiles)
  table.sort(names)

  for _, name in ipairs(names) do
    local profile = settings.profiles[name]
    if type(profile) == "table" and profile.commandName == "Project" then
      local env = {}
      for key, value in pairs(profile.environmentVariables or {}) do
        env[key] = tostring(value)
      end
      if profile.applicationUrl then
        env.ASPNETCORE_URLS = profile.applicationUrl
      end
      return env
    end
  end

  return {}
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
    --- Launching the dll bypasses launchSettings.json, so read the profile's
    --- environment ourselves. The shell still wins where it sets a value, so
    --- `ASPNETCORE_URLS=http://localhost:5179 nvim` keeps overriding the port.
    env = function()
      local env =
        launch_profile_env(nearest_root("%.csproj$") or vim.fn.getcwd())
      env.ASPNETCORE_URLS = vim.env.ASPNETCORE_URLS or env.ASPNETCORE_URLS
      env.ASPNETCORE_ENVIRONMENT = vim.env.ASPNETCORE_ENVIRONMENT
        or env.ASPNETCORE_ENVIRONMENT
      return env
    end,
  },
  {
    type = "coreclr",
    request = "attach",
    name = "Attach to process",
    processId = require("dap.utils").pick_process,
  },
}

-- Stack-agnostic layout (Angular, .NET, Nest, ...): Scopes over Stacks on the
-- left, REPL + Console along the bottom. The Breakpoints and Watches panels are
-- dropped -- breakpoints show as gutter signs, and ad-hoc values come from
-- <leader>xk (eval) and the REPL -- which reclaims the space they wasted.
dapui.setup({
  layouts = {
    {
      position = "left",
      size = 42,
      elements = {
        { id = "scopes", size = 0.6 },
        { id = "stacks", size = 0.4 },
      },
    },
    {
      position = "bottom",
      size = 10,
      elements = {
        { id = "repl", size = 0.5 },
        { id = "console", size = 0.5 },
      },
    },
  },
})

dap.listeners.after.event_initialized["dapui_config"] = function()
  dapui.open()
end
-- vscode-js-debug spawns a child session per page target, so an Angular
-- live-reload terminates the old target while the root session lives on. A
-- child carries `session.parent`; the root does not. Tear the UI down only
-- when the root session ends, so a reload keeps the panels open but a real
-- quit (dap.terminate) closes them. (nvim-dap can't count remaining sessions
-- here: `before` listeners fire before the terminating session is removed, so
-- dap.sessions() still holds it and would never read as empty.)
local function close_ui_on_root_exit(session)
  if not (session and session.parent) then
    dapui.close()
  end
end
dap.listeners.before.event_terminated["dapui_config"] = close_ui_on_root_exit
dap.listeners.before.event_exited["dapui_config"] = close_ui_on_root_exit

-- Signs. nvim-dap highlights the stopped line with `debugPC`, which renders
-- darker than the background (invisible); re-point it at `DapStoppedLine`,
-- defined in `user.colorscheme`, and give every marker a visible colour
-- instead of the default low-contrast `SignColumn`.
vim.fn.sign_define("DapStopped", {
  text = "→",
  texthl = "DiagnosticWarn",
  linehl = "DapStoppedLine",
  numhl = "DiagnosticWarn",
})
vim.fn.sign_define("DapBreakpoint", {
  text = "●",
  texthl = "DiagnosticError",
  linehl = "",
  numhl = "",
})
vim.fn.sign_define("DapBreakpointCondition", {
  text = "◆",
  texthl = "DiagnosticWarn",
  linehl = "",
  numhl = "",
})
vim.fn.sign_define("DapBreakpointRejected", {
  text = "○",
  texthl = "DiagnosticError",
  linehl = "",
  numhl = "",
})

--- Add a normal-mode debugging keymap.
---@param lhs string Keymap
---@param rhs function|string Action
---@param desc string which-key description
local function map(lhs, rhs, desc)
  vim.keymap.set("n", lhs, rhs, { noremap = true, silent = true, desc = desc })
end

map("<leader>xb", dap.toggle_breakpoint, "Toggle breakpoint")
map("<leader>xB", function()
  dap.set_breakpoint(vim.fn.input("Breakpoint condition: "))
end, "Conditional breakpoint")
map("<leader>xc", dap.continue, "Continue / start")
map("<leader>xi", dap.step_into, "Step into")
map("<leader>xo", dap.step_over, "Step over")
map("<leader>xO", dap.step_out, "Step out")
map("<leader>xr", dap.repl.toggle, "Toggle REPL")
map("<leader>xt", dap.terminate, "Terminate session")
map("<leader>xu", dapui.toggle, "Toggle debug UI")
map("<leader>xk", function()
  require("dapui").eval()
end, "Evaluate expression")
