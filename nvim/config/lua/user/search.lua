--- Shared ripgrep arguments for the Telescope pickers.
---
--- Gitignored files are searchable on purpose (`--no-ignore-vcs`): a local
--- config or a generated file is often exactly what you are looking for, and
--- respecting .gitignore put those out of reach. The directories below are the
--- exception, being dependency trees and build output large enough to drown a
--- picker. Browse those with oil rather than a fuzzy finder.
local M = {}

--- Directories excluded from every picker. A glob without a slash matches at
--- any depth; `bin` is spelled out per configuration so a repository's own
--- `bin/` of scripts stays reachable while .NET build output does not.
M.excluded = {
  ".git",
  ".DS_Store",
  "node_modules",
  ".angular",
  ".nx",
  "dist",
  "coverage",
  "obj",
  "**/bin/Debug",
  "**/bin/Release",
  "target",
  "zig-cache",
  "zig-out",
  "__pycache__",
  ".venv",
}

--- Build one rg exclude flag per entry in `M.excluded`.
---@return string[] flags rg `--glob=!` flags
function M.glob_flags()
  return vim.tbl_map(function(dir)
    return "--glob=!" .. dir
  end, M.excluded)
end

--- rg invocation listing files, for Telescope's find_files.
---@return string[] cmd Full rg command
function M.find_command()
  return vim.list_extend({
    "rg",
    "--hidden",
    "--files",
    "--smart-case",
    "--no-ignore-vcs",
  }, M.glob_flags())
end

--- rg invocation for searching file contents, for Telescope's live_grep and
--- grep_string.
---@return string[] args Full rg argument list
function M.vimgrep_arguments()
  return vim.list_extend({
    "rg",
    "--color=never",
    "--no-heading",
    "--with-filename",
    "--line-number",
    "--column",
    "--smart-case",
    "--hidden",
    "--no-ignore-vcs",
  }, M.glob_flags())
end

return M
