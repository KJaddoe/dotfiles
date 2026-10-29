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

return M
