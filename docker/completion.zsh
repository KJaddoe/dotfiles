#!/bin/zsh
fpath=(~/.docker/completions $fpath)
autoload -Uz compinit
compinit
