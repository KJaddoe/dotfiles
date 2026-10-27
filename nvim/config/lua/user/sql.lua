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
--- database, since it cannot connect without one; `trust` applies to SQL Server only.
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
  if conn.engine == "sqlserver" and conn.trust then
    url = url .. "?trustServerCertificate=true"
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

return M
