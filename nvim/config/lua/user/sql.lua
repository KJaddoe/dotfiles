---@class UserSql
local M = {}

---@alias UserSqlEngine "sqlserver"|"postgresql"

---@class UserSqlConn
---@field engine UserSqlEngine
---@field host string
---@field port? string
---@field user string
---@field password? string
---@field database? string
---@field trust? boolean SQL Server only: skip certificate validation

---@class UserSqlDefaults
---@field host string prefill, `host:port` when the engine's env names a port
---@field user string
---@field password? string set only when host and user both came from the env

local ENV = {
  sqlserver = {
    host = "SQLCMDSERVER",
    user = "SQLCMDUSER",
    password = "SQLCMDPASSWORD",
  },
  postgresql = {
    host = "PGHOST",
    port = "PGPORT",
    user = "PGUSER",
    password = "PGPASSWORD",
  },
}

local DEFAULT_USER = { sqlserver = "sa", postgresql = "postgres" }

local ENGINE_LABELS = { sqlserver = "SQL Server", postgresql = "PostgreSQL" }

local NO_CONNECTION = "no connection for this buffer; connect with <leader>sc"

--- Logins held for this nvim session, keyed by `login_key`, without a database.
---@type table<string, UserSqlConn>
local logins = {}

--- Percent-encode all but RFC 3986's unreserved characters; `vim.uri_encode`
--- keeps `@`, `:` and `/`, which would break the URL's user and password.
---@param value string
---@return string
local function encode(value)
  return (
    value:gsub("[^%w%-%._~]", function(char)
      return ("%%%02X"):format(char:byte())
    end)
  )
end

--- The vim-dadbod URL for a connection. PostgreSQL falls back to the `postgres`
--- database, since it cannot connect without one. SQL Server always requires encryption, and
--- `trust` (SQL Server only) skips its certificate check.
---@param conn UserSqlConn
---@return string
function M.build_url(conn)
  local userinfo = encode(conn.user)
  if conn.password then
    userinfo = userinfo .. ":" .. encode(conn.password)
  end
  local url = ("%s://%s@%s"):format(conn.engine, userinfo, conn.host)
  if conn.port then
    url = url .. ":" .. conn.port
  end
  local database = conn.database
  if conn.engine == "postgresql" then
    database = database or "postgres"
  end
  if database then
    url = url .. "/" .. encode(database)
  end
  if conn.engine == "sqlserver" then
    url = url
      .. "?encrypt=mandatory"
      .. (conn.trust and "&trustServerCertificate=true" or "")
  end
  return url
end

--- Split a host answer: `host`, `host,port` (sqlcmd style), `host:port` or `[ipv6]:port`;
--- a bare IPv6 address is kept whole.
---@param input string|nil
---@return string|nil host nil when the answer is blank
---@return string|nil port
function M.parse_host(input)
  local trimmed = vim.trim(input or "")
  if trimmed == "" then
    return nil, nil
  end
  local host, port = trimmed:match("^(.+),(%d+)$")
  if not host then
    host, port = trimmed:match("^(%b[]):(%d+)$")
  end
  if not host then
    host, port = trimmed:match("^([^:]+):(%d+)$")
  end
  if host then
    return host, port
  end
  return trimmed, nil
end

--- Prefills for the connect prompts, from the engine's environment variables.
---@param engine UserSqlEngine
---@param env table<string, string> usually `vim.env`; an empty value counts as unset
---@return UserSqlDefaults
function M.defaults(engine, env)
  local keys = ENV[engine]
  local function get(name)
    local value = name and env[name]
    if value ~= "" then
      return value
    end
  end
  local host, port, user = get(keys.host), get(keys.port), get(keys.user)
  return {
    host = (host or "localhost") .. (port and (":" .. port) or ""),
    user = user or DEFAULT_USER[engine],
    password = (host and user) and get(keys.password) or nil,
  }
end

--- The env password, only when the host and user answers kept their prefills.
---@param defaults UserSqlDefaults
---@param host_answer string the host as typed, before `parse_host`
---@param user_answer string
---@return string|nil
function M.password_from_env(defaults, host_answer, user_answer)
  if host_answer == defaults.host and user_answer == defaults.user then
    return defaults.password
  end
  return nil
end

--- Whether to skip SQL Server's certificate check: only for this machine.
---@param host string the host after `parse_host`, without a port
---@return boolean
function M.auto_trust(host)
  return host == "localhost" or host == "127.0.0.1"
end

--- Client arguments that print one database name per line, with no header or row
--- count; appended to vim-dadbod's interactive command for the engine.
---@param engine UserSqlEngine
---@return string[]
function M.database_list_args(engine)
  if engine == "sqlserver" then
    return {
      "-h-1",
      "-W",
      "-Q",
      "SET NOCOUNT ON; SELECT name FROM sys.databases ORDER BY name",
    }
  end
  return {
    "--no-psqlrc",
    "-tAX",
    "-c",
    "SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY 1",
  }
end

function M.parse_database_list(stdout)
  local names = {}
  for line in vim.gsplit(stdout or "", "\n", { plain = true }) do
    local name = vim.trim(line)
    if name ~= "" then
      table.insert(names, name)
    end
  end
  return names
end

local function is_separator(line, header)
  return (line == "-" or line:match("^%-[- ]*%-$") ~= nil)
    and not line:find("  ", 1, true)
    and vim.fn.strchars(header) == #line
end

local function align_block(block)
  local width = #block[2]
  for _, line in ipairs(block) do
    if vim.fn.strchars(line) ~= width then
      return block
    end
  end
  local aligned, rule = {}, {}
  for i = 1, #block do
    aligned[i] = {}
  end
  for start, run in block[2]:gmatch("()(%-+)") do
    local offset, span = start - 1, #run
    local header = vim.fn.strcharpart(block[1], offset, span):gsub("%s+$", "")
    local lead, trail = span, span
    for i = 3, #block do
      local cell = vim.fn.strcharpart(block[i], offset, span)
      lead = math.min(lead, #cell:match("^ *"))
      trail = math.min(trail, #cell:match(" *$"))
    end
    local content = math.max(0, span - lead - trail)
    local column = math.max(content, vim.fn.strchars(header))
    local right = lead > 0 and trail == 0
    aligned[1][#aligned[1] + 1] = header
      .. (" "):rep(column - vim.fn.strchars(header))
    rule[#rule + 1] = ("-"):rep(column)
    for i = 3, #block do
      local cell = vim.fn.strcharpart(block[i], offset + lead, content)
      local pad = (" "):rep(column - content)
      aligned[i][#aligned[i] + 1] = right and pad .. cell or cell .. pad
    end
  end
  local lines = {}
  for i = 1, #block do
    lines[i] = i == 2 and table.concat(rule, " ")
      or table.concat(aligned[i], " ")
  end
  return lines
end

--- Shrink sqlcmd's result columns to their content; sqlcmd pads each to its declared width.
---@param lines string[] the lines of a SQL Server result buffer
---@return string[]
function M.align_sqlserver(lines)
  local out, i = {}, 1
  while i <= #lines do
    local header, separator = lines[i], lines[i + 1]
    if header ~= "" and separator and is_separator(separator, header) then
      local last = i + 1
      while lines[last + 1] and lines[last + 1] ~= "" do
        last = last + 1
      end
      vim.list_extend(out, align_block(vim.list_slice(lines, i, last)))
      i = last + 1
    else
      out[#out + 1] = header
      i = i + 1
    end
  end
  return out
end

--- The statement under the cursor: the block of non-blank lines holding `row`.
---@param lines string[] the buffer's lines
---@param row integer the cursor's 1-based line
---@return integer|nil first nil on a blank line
---@return integer|nil last
function M.statement_range(lines, row)
  if not (lines[row] or ""):match("%S") then
    return nil
  end
  local first, last = row, row
  while first > 1 and lines[first - 1]:match("%S") do
    first = first - 1
  end
  while last < #lines and lines[last + 1]:match("%S") do
    last = last + 1
  end
  return first, last
end

local function login_key(conn)
  local host = conn.port and (conn.host .. ":" .. conn.port) or conn.host
  return ("%s %s@%s"):format(conn.engine, conn.user, host)
end

local function notify(message, level)
  vim.notify(message, level, { title = "sql" })
end

--- Prompt for a line; Esc and an empty answer both cancel, so `on_answer` never
--- sees nil or "".
---@param prompt string
---@param default string
---@param on_answer fun(answer: string)
local function ask(prompt, default, on_answer)
  vim.ui.input({ prompt = prompt, default = default }, function(answer)
    if answer and answer ~= "" then
      on_answer(answer)
    end
  end)
end

local function list_databases(conn, on_names)
  -- Not vim-dadbod's complete_database(): its db#systemlist returns {} on any failure and drops stderr.
  local cmd = vim.fn["db#adapter#dispatch"](M.build_url(conn), "interactive")
  vim.list_extend(cmd, M.database_list_args(conn.engine))
  vim.system(
    cmd,
    { text = true },
    vim.schedule_wrap(function(result)
      if result.code ~= 0 then
        local output =
          vim.trim(result.stderr ~= "" and result.stderr or result.stdout)
        notify(
          ("could not list databases for %s:\n%s"):format(
            login_key(conn),
            output
          ),
          vim.log.levels.ERROR
        )
        return
      end
      local names = M.parse_database_list(result.stdout)
      if #names == 0 then
        notify(
          ("no databases visible to %s"):format(login_key(conn)),
          vim.log.levels.WARN
        )
        return
      end
      on_names(names)
    end)
  )
end

local function pick_database(buf, conn)
  list_databases(conn, function(names)
    vim.ui.select(names, { prompt = "Database" }, function(database)
      if not database then
        return
      end
      local key = login_key(conn)
      logins[key] = conn
      vim.b[buf].db =
        M.build_url(vim.tbl_extend("force", conn, { database = database }))
      vim.b[buf].user_sql_login = key
      -- vim-dadbod-completion fetches the schema on FileType only, before b:db existed.
      vim.fn["vim_dadbod_completion#fetch"](buf)
    end)
  end)
end

local function new_connection(buf)
  vim.ui.select({ "sqlserver", "postgresql" }, {
    prompt = "Engine",
    format_item = function(engine)
      return ENGINE_LABELS[engine]
    end,
  }, function(engine)
    if not engine then
      return
    end
    local defaults = M.defaults(engine, vim.env)
    ask("Host: ", defaults.host, function(host_answer)
      local host, port = M.parse_host(host_answer)
      if not host then
        return
      end
      ask("User: ", defaults.user, function(user)
        local conn = { engine = engine, host = host, port = port, user = user }
        local env_password = M.password_from_env(defaults, host_answer, user)
        if not env_password then
          local password = vim.fn.inputsecret("Password: ")
          if password == "" then
            return
          end
          conn.password = password
        elseif engine == "sqlserver" then
          conn.password = env_password
        end
        -- A PostgreSQL env password stays out of the URL: psql reads PGPASSWORD itself, and a
        -- URL password would show in ps.
        if engine == "sqlserver" then
          if M.auto_trust(host) then
            conn.trust = true
          else
            local choice = vim.fn.confirm(
              ("Trust the server certificate of %s?"):format(host),
              "&No\n&Yes",
              1
            )
            if choice == 0 then
              return
            end
            conn.trust = choice == 2
          end
        end
        pick_database(buf, conn)
      end)
    end)
  end)
end

function M.connect()
  local buf = vim.api.nvim_get_current_buf()
  local held = vim.tbl_keys(logins)
  if #held == 0 then
    new_connection(buf)
    return
  end
  table.sort(held)
  local new = "New connection"
  table.insert(held, new)
  vim.ui.select(held, {
    prompt = "Connection",
    format_item = function(item)
      return item == new and item or ("Reuse " .. item)
    end,
  }, function(choice)
    if not choice then
      return
    end
    if choice == new then
      new_connection(buf)
    else
      pick_database(buf, logins[choice])
    end
  end)
end

function M.switch_database()
  local buf = vim.api.nvim_get_current_buf()
  local conn = logins[vim.b[buf].user_sql_login or ""]
  if not (vim.b[buf].db and conn) then
    notify(NO_CONNECTION, vim.log.levels.WARN)
    return
  end
  pick_database(buf, conn)
end

--- Run part of the current buffer through vim-dadbod into its result split.
---@param range string `%` for the whole buffer, `'<,'>` for the last selection
function M.run(range)
  if not vim.b.db then
    notify(NO_CONNECTION, vim.log.levels.WARN)
    return
  end
  vim.cmd(range .. "DB")
end

local function attach(buf)
  local function map(mode, lhs, rhs, desc)
    vim.keymap.set(mode, lhs, rhs, { buffer = buf, silent = true, desc = desc })
  end
  map("n", "<leader>sc", M.connect, "SQL: connect")
  map("n", "<leader>sd", M.switch_database, "SQL: switch database")
  map("n", "<leader>sr", function()
    M.run("%")
  end, "SQL: run buffer")
  map("n", "<leader>ss", function()
    local first, last = M.statement_range(
      vim.api.nvim_buf_get_lines(0, 0, -1, false),
      vim.fn.line(".")
    )
    if not first then
      notify("no statement under the cursor", vim.log.levels.WARN)
      return
    end
    M.run(("%d,%d"):format(first, last))
  end, "SQL: run statement")
  map(
    "x",
    "<leader>sr",
    [[<Esc><Cmd>lua require("user.sql").run("'<,'>")<CR>]],
    "SQL: run selection"
  )
end

function M.setup()
  vim.api.nvim_create_user_command(
    "SqlConnect",
    M.connect,
    { desc = "Connect this buffer to a database" }
  )
  vim.api.nvim_create_user_command(
    "SqlDatabase",
    M.switch_database,
    { desc = "Switch this buffer's database" }
  )
  local group = vim.api.nvim_create_augroup("UserSql", { clear = true })
  vim.api.nvim_create_autocmd("FileType", {
    pattern = "sql",
    callback = function(args)
      attach(args.buf)
    end,
    group = group,
  })
  vim.api.nvim_create_autocmd("User", {
    pattern = "*/DBExecutePost",
    callback = function(args)
      -- Parenthesised: gsub's count would become bufnr's create flag.
      local buf = vim.fn.bufnr((args.match:gsub("/DBExecutePost$", "")))
      if buf == -1 or not vim.api.nvim_buf_is_loaded(buf) then
        return
      end
      local query = vim.b[buf].db
      if
        type(query) ~= "table"
        or not vim.startswith(query.db_url or "", "sqlserver:")
      then
        return
      end
      local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
      vim.bo[buf].modifiable = true
      vim.api.nvim_buf_set_lines(buf, 0, -1, false, M.align_sqlserver(lines))
      vim.bo[buf].modifiable = false
      vim.bo[buf].modified = false
    end,
    group = group,
  })
  -- lazy.nvim runs this from the first sql buffer's FileType, which has already fired for it.
  if vim.bo.filetype == "sql" then
    attach(vim.api.nvim_get_current_buf())
  end
end

return M
