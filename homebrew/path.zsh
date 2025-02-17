#!/bin/zsh
# Homebrew env
case "$(uname -s)" in
    Darwin)
        [[ -f /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
        ;;
    Linux)
        [[ -f /home/linuxbrew/.linuxbrew/bin/brew ]] && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        ;;
esac
