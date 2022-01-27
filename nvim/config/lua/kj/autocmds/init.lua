local M = {}
function M.autocmd(event, triggers, operations)
  local cmd = string.format("autocmd %s %s %s", event, triggers, operations)
 vim.cmd(cmd)
end

M.autocmd("BufEnter",     "*",   "if &buftype == 'terminal' | :startinsert | endif")
M.autocmd("BufReadPost",  "*",   [[if line("'\"") > 0 && line ("'\"") <= line("$") | exe "normal! g'\"" | endif]])
M.autocmd("BufWritePre",  "*",   "%s/\\s\\+$//e")
M.autocmd("BufWritePost", "*",   "FormatWrite")

M.autocmd("ColorScheme",  "*",   "lua require('kj.colors').setItalics()")
M.autocmd("CompleteDone", "*",   "pclose")

M.autocmd("FileType",     "vue", "syntax sync fromstart")

M.autocmd("TermOpen",     "*",   "setl bufhidden=hide")
M.autocmd("TermOpen",     "*",   "startinsert")
M.autocmd("TermOpen",     "*",   "setl nonumber")

M.autocmd("WinLeave",     "*",   "if exists('w:last_fdm') | let &l:foldmethod=w:last_fdm | unlet w:last_fdm | endif")


return M
