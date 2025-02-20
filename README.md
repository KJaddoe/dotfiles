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

The default `EDITOR` right now is `vim`, more specifically neovim. You can change that by adding your custom
override to that variable in `~/.localrc`.

`PROJECTS` is default to `~/projects`. The shortcut to that folder in the shell
is `c`. You can override this default in `~/.localrc`.

### Topical

Everything's built around topic areas. If you're adding a new area to your
forked dotfiles — say, "Erlang" — you can simply add a `erlang` directory and
put files in there. Anything with an extension of `.zsh` will get automatically
included into your shell.

### Naming conventions

There are a few special files in the hierarchy:

- **bin/**: Anything in `bin/` will get added to your `$PATH` and be made
  available everywhere.
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

This project uses the [Powerlevel10k][powerlevel10k] prompt with the [Powerline font][https://github.com/powerline/fonts] and status bar (which is awesome!) and some other
[zsh plugins](/antidote/zsh_plugins.txt). All of them managed by [Antidote][antidote].

[powerlevel10k]: https://github.com/romkatv/powerlevel10k
[antidote]: https://antidote.sh/
[powerline font]: https://github.com/powerline/fonts

### Compatibility

I Mostly work on Linux using either WSL or a distro of Linux.

# Installation

The entire setup can be installed when you run `script/bootstrap`. This will also run the `_system` installation file. The system installation will install everything that is required to get my exact setup.

## Tmux

to install the tmux plugins you will have to manually do `prefix + I` to install the plugins using tpm. The set prefix is `ctrl + b`

## Issues

When having issues installing on wsl some of the following links helped me to get it working:
https://github.com/MicrosoftDocs/WSL/issues/457#issuecomment-730731900 (deamon not running or can't get deamon status)

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

### Symlinking the dotfiles

For symlinking the dotfiles I chose to use [Dotbot](https://github.com/anishathalye/dotbot). This is a very handy tool for cleaning some files, linking the dotfiles and running some shell commands. The configuration for [Dotbot](https://github.com/anishathalye/dotbot) can be found in dotbot.conf.yaml
