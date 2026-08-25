# ADR 0003: Build the tmux status bar from native config, not a status-bar plugin

- Status: accepted
- Date: 2026-08-19

## Context

The status bar was `tmux-powerline` running its bundled `default` theme, whose segment colours
(148/33/24/29/89/167/137/37/136) bear no relation to anything else on the machine. nvim runs
`tokyonight-night`. The obvious fix was a `tmux-powerline` user theme in matching colours, and that
was built first: it worked, and it exposed why the plugin was the wrong foundation.

Three limits, each verified against the plugin's source rather than assumed:

- **It owns only a third of the surface.** `tmux-powerline` sets `status-left`, `status-right` and
  the two window formats. `pane-border-style`, `pane-active-border-style`, `mode-style` and
  `copy-mode-current-match-style` were never touched, so they sat at tmux's ANSI defaults, a green
  pane border, a yellow copy-mode selection, a magenta search match. The bar could match the editor
  exactly while every other tmux surface clashed with it.
- **Config is split and silently coupled.** Settings live in `config.sh`, colours and segments in a
  theme file, and `lib/config_file.sh:65-70` resolves the theme as
  `$TMUX_POWERLINE_DIR_USER_THEMES/$TMUX_POWERLINE_THEME.sh`. A basename that does not match the
  configured theme name falls back to the bundled theme with no error.
- **One colour cannot be a hex.** `segments/vcs_branch.sh:80` interpolates the branch glyph colour
  as `colour${VAR}`, so that value is restricted to the 256-palette regardless of terminal support.

One assumption did not survive checking, and it was not a reason to leave: `tmux-powerline` does
*not* fork a process per segment. `lib/powerline.sh:106` sources each segment into a single bash per
side. Performance was never the problem.

Meanwhile tmux is 3.5a, whose native formats express everything the bar displays, and
`tokyonight.nvim` ships `extras/tmux/tokyonight_night.tmux`, plain tmux options generated from the
same palette source as the editor colorscheme.

## Decision

The status bar is native tmux configuration in `tmux/tmux.conf`, placed after the `run` line that
loads TPM so that plugin defaults cannot override it. Anything requiring a shell is a standalone
script in `bin/` (`tmux-battery` and `tmux-git-branch`), invoked from `#()`.

The palette is tokyonight-night, and it is applied to every surface tmux exposes, not just the bar:
pane borders, copy mode, search matches and messages included. Ghostty is set to its built-in
`TokyoNight Night` so the terminal underneath matches rather than showing through as a stock palette.

Rejected:

- **Keeping `tmux-powerline` with the custom theme.** Leaves pane borders and copy mode unthemed,
  keeps the two-file coupling, and keeps the `colour$VAR` restriction.
- **Another status-bar plugin** (`catppuccin/tmux`, `tmux2k`, `dracula/tmux`). Same class of thing:
  a framework owning part of the surface and imposing its own theme contract. Expect this to be
  re-proposed; the objection is structural, not about which plugin.
- **Sourcing `tokyonight_night.tmux` verbatim.** It hardcodes its own layout and segment choices
  (hostname, full date), which is not the curated set that was wanted. It was used as a reference
  for which options need styling, not as a drop-in.

## Consequences

- One file to read, and every tmux surface is themed rather than a third of them.
- Two scripts to maintain. They are resolved through `$PATH`, so a tmux server started without
  `bin/` in its environment renders the branch and battery as empty rather than failing loudly.
  Silent degradation is right for a status bar and wrong when debugging one, so check `$PATH` first.
- `#()` runs both helpers on every status refresh (`status-interval 5`).
- Reverting means restoring `tmux/tmux-powerline.config.sh` from git history and re-adding the
  `@plugin` line; the TPM checkout re-clones on demand.
- Palette values now live in three places: nvim and Ghostty reference tokyonight by *name*, while
  tmux hardcodes the *hexes*. Only the tmux copy can drift if upstream retunes the palette.
