require("kanagawa").setup({
  overrides = function(colors)
    local theme = colors.theme
    local panel = theme.ui.bg_m1
    local prompt = theme.ui.bg_p1
    return {
      DapStoppedLine = {
        bg = colors.palette.winterYellow,
      },
      TelescopeNormal = {
        bg = panel,
        fg = theme.ui.fg_dim,
      },
      TelescopeBorder = {
        bg = panel,
        fg = panel,
      },
      TelescopePromptNormal = {
        bg = prompt,
      },
      TelescopePromptBorder = {
        bg = prompt,
        fg = prompt,
      },
      TelescopePromptTitle = {
        bg = prompt,
        fg = prompt,
      },
      TelescopePreviewTitle = {
        bg = panel,
        fg = panel,
      },
      TelescopeResultsTitle = {
        bg = panel,
        fg = panel,
      },
    }
  end,
})
vim.cmd.colorscheme("kanagawa-wave")
