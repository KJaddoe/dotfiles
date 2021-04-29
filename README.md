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
included into your shell. Anything with an extension of `.symlink` will get
symlinked without extension into `$HOME` when you run `script/bootstrap`.

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
- **topic/\*.symlink**: Any files ending in `*.symlink` get symlinked into
  your `$HOME`. This is so you can keep all of those versioned in your dotfiles
  but still keep those autoloaded files in your home directory. These get
  symlinked in when you run `script/bootstrap`.
- **topic/install.sh**: Any file with this name and with exec permission, will
  ran at `bootstrap` and `dot_update` phase, and are expected to install plugins,
  and stuff like that.

### ZSH plugins

This project uses the [Powerlevel10k][powerlevel10k] prompt (which is awesome!) and some other
[zsh plugins](/antibody/bundles.txt). All of them managed by [Antibody][antibody],
a faster and simpler Antigen-like program written in Go.

[powerlevel10k]: https://github.com/romkatv/powerlevel10k
[antibody]: https://github.com/caarlos0/antibody

### Compatibility

I Mostly work on Linux using either WSL or a distro of Linux.

# Installation

The entire setup can be installed when you run `script/bootstrap`. This will also run the `_system` installation file. The system installation will install everything that is required to get my exact setup.

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
