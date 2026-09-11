---@class UserDapDocker
local M = {}

--- Locate the nearest ancestor directory of the current buffer holding a
--- Docker Compose file.
---@return string|nil dir
local function compose_root()
  return vim.fs.root(0, function(fname)
    return fname == "docker-compose.yml" or fname == "compose.yml"
  end)
end

M.compose_root = compose_root

--- Find the running container id for a compose service, by convention named
--- `api`, discovered from the compose file nearest the current buffer.
---@param service string
---@param callback fun(container_id: string|nil)
function M.find_container(service, callback)
  local root = compose_root()
  if not root then
    vim.notify(
      "dap: no docker-compose.yml found above this buffer",
      vim.log.levels.WARN,
      { title = "dap" }
    )
    callback(nil)
    return
  end
  vim.system(
    { "docker", "compose", "ps", "-q", service },
    { cwd = root, text = true },
    function(result)
      local id = result.stdout and result.stdout:match("%S+")
      if result.code ~= 0 or not id then
        vim.notify(
          "dap: no running '"
            .. service
            .. "' container under "
            .. root
            .. " (docker compose up?)",
          vim.log.levels.WARN,
          { title = "dap" }
        )
        callback(nil)
        return
      end
      callback(id)
    end
  )
end

--- Find the pid of a process inside a running container whose command line
--- matches a pattern, via `pgrep -f`.
---@param container string Container id or name
---@param pattern string A pgrep -f (POSIX extended regex) pattern
---@param callback fun(pid: string|nil)
function M.find_pid(container, pattern, callback)
  vim.system(
    { "docker", "exec", container, "pgrep", "-f", pattern },
    { text = true },
    function(result)
      local pid = result.stdout and result.stdout:match("%d+")
      if result.code ~= 0 or not pid then
        vim.notify(
          "dap: no process matching '"
            .. pattern
            .. "' found in container "
            .. container,
          vim.log.levels.WARN,
          { title = "dap" }
        )
        callback(nil)
        return
      end
      callback(pid)
    end
  )
end

return M
