local notify = require("notify")
vim.notify = notify

vim.keymap.set("n", "<leader>un", function()
  notify.dismiss({ silent = true, pending = true })
end, {
  noremap = true,
  silent = true,
  desc = "Delete all Notifications",
})
