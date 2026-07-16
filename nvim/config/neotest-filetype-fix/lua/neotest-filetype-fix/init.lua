--- Workaround for neotest's parse subprocess failing to detect typescript:
--- core nvim resolves *.ts by sniffing the buffer for XML, which returns nil
--- in neotest's config-less (-u NONE) child process. Neotest adds the plugin
--- root of every loaded `neotest-*` module to the child's rtp and sources
--- plugin/filetypes.lua from it, so requiring this module makes the child
--- pick up the direct ts -> typescript mapping shipped next to it.
--- Remove once neotest-jest ships its own plugin/filetypes.lua.
local M = {}

--- No-op; neotest resolves a plugin's root directory for the child process
--- rtp by inspecting a function member of the loaded module.
function M.setup() end

return M
