#!/bin/sh
export FZF_COMPLETION_TRIGGER='**'
export FZF_BASE='/home/linuxbrew/.linuxbrew/bin/fzf'

# Set up fzf key bindings and fuzzy completion
source <(fzf --zsh)
