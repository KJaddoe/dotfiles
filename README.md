# KJaddoe's dotfiles

# PHILOSOPHY

> Philosophical stuff about this dotfiles structure, decisions, etc..

## Why?

I was a little tired of having long alias files and everything strewn about
(which is extremely common on other dotfiles projects, too). That led to this
project being much more topic-centric. I realized I could split a lot of things
up into the main areas I used (git, system libraries, and so on), so I
structured the project accordingly.

## Decisions

### Default `EDITOR` and `PROJECTS`

The default `EDITOR` is `nvim` (neovim); `VEDITOR` is `code`. You can change either by adding your
custom override to that variable in `~/.localrc`.

`PROJECTS` is default to `~/projects`. The shortcut to that folder in the shell
is `c`. You can override this default in `~/.localrc`.

### Topical

Everything's built around topic areas. If you're adding a new area to your
forked dotfiles (say, "Erlang") you can simply add a `erlang` directory and
put files in there. Anything with an extension of `.zsh` will get automatically
included into your shell.

### Naming conventions

There are a few special files in the hierarchy:

- **bin/**: Anything in `bin/` will get added to your `$PATH` and be made
  available everywhere. Currently `dot_update` (see [Updating](#updating)), `myip`, and
  `new-project`.
- **topic/\*.zsh**: Any files ending in `.zsh` get loaded into your
  environment.
- **topic/path.zsh**: Any file named `path.zsh` is loaded first and is
  expected to setup `$PATH` or similar.
- **topic/completion.zsh**: Any file named `completion.zsh` is loaded
  last and is expected to setup autocomplete.
- **topic/install.sh**: Any file with this name and with exec permission, will
  ran at `bootstrap` and `dot_update` phase, and are expected to install plugins,
  and stuff like that.

### ZSH plugins

This project uses the [Powerlevel10k][powerlevel10k] prompt with the [Powerline font][powerline font] and status bar (which is awesome!) and some other
[zsh plugins](/antidote/zsh_plugins.txt). All of them managed by [Antidote][antidote].

[powerlevel10k]: https://github.com/romkatv/powerlevel10k
[antidote]: https://antidote.sh/
[powerline font]: https://github.com/powerline/fonts

### Compatibility

macOS and Ubuntu are the supported platforms, both first-class. `_system/install.sh` exits with an
error on any other OS, including non-Ubuntu Linux distributions. WSL works where it presents as
Ubuntu (see [Issues](#issues)).

# Installation

## Prerequisites

`git`, `zsh`, `python3` and `sudo` must be present before bootstrapping; everything else is
installed for you. On macOS the Xcode command line tools cover the first three.

## Clone location

**The repo must live at `~/dotfiles`.** The path is hardcoded in `zsh/zshrc` (`DOTFILES`), the
autoupdate crontab entry, and `git/gitconfig.local`. Cloning elsewhere will half-work in ways that
are annoying to debug.

```sh
git clone <this-repo> ~/dotfiles
cd ~/dotfiles
script/bootstrap
```

`script/bootstrap` installs everything: it runs the `_system` Ansible provisioning, links configs
with Dotbot, and executes every topic's `install.sh`.

## Symlinking

Symlinking is handled by [Dotbot](https://github.com/anishathalye/dotbot), which cleans dead links,
links the dotfiles into `$HOME`, and runs shell commands. Its configuration lives in
`dotbot.conf.yaml`. See `docs/architecture.md` for why provisioning and symlinking are separate.

## Updating

`bin/dot_update` (on `$PATH` as `dot_update`) pulls the latest dotfiles, syncs submodules, re-runs
every `install.sh` via `script/install`, and updates the zsh plugins.

**This also runs automatically.** `autoupdate/install.sh` registers a crontab entry that runs
`dot_update` **every two hours**, logging to `$TMPDIR/dot_update.log`, so a machine pulls and
re-applies dotfiles changes on its own. Remove the entry with `crontab -e` if you don't want that.

Because it runs unattended, the update **fast-forwards or does nothing**: it never rewrites
history or touches work in progress. It skips the pull, and says so in the log, when:

- you are not on the default branch;
- the working tree is not clean;
- the update channel is unreachable;
- local commits have diverged from upstream ones.

That last case needs a real merge, and it stays a decision for a human at a terminal. Run
`dot_update` yourself, or merge by hand, when you see it skipped. The rest of the update
(submodules, `script/install`, zsh plugins) runs either way.

## Testing

`script/test` is the end-to-end check. It is **destructive**: it copies the repo over `~/dotfiles`,
overwrites your global git identity, and runs a full bootstrap, so it is meant for a throwaway
machine or CI, not your working setup.

For the hook unit tests alone (safe to run anywhere), see `docs/architecture.md`.

## Tmux

to install the tmux plugins you will have to manually do `prefix + I` to install the plugins using tpm. The set prefix is `ctrl + b`

## Claude Code

The `claude` topic installs [Claude Code][claude-code] and restores the global config. Its `install.sh` installs the binary, then adds the configured marketplaces and plugins. Dotbot symlinks `settings.json`, `CLAUDE.md`, `keybindings.json`, `hooks/`, `memory/`, `skills/` and `templates/` into `~/.claude`, so they stay in sync with the repo. You will need to authenticate once with `claude` on a new machine.

[claude-code]: https://github.com/anthropics/claude-code

## Issues

When having issues installing on wsl some of the following links helped me to get it working:
<https://github.com/MicrosoftDocs/WSL/issues/457#issuecomment-730731900> (deamon not running or can't get deamon status)

# Personalization

> How to add custom configuration without messing the local repository

## For the shell itself

You can add anything you want (secret stuff, for example), to the `~/.localrc`
file.

## For git

You can just change the default `~/.gitconfig` file, since it includes the
dotfiles managed one.

## For ssh

You can edit the `~/.ssh/config.local` file.
