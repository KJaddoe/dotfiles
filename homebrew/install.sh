#!/bin/bash

set -e

OS="$(uname)"
BREWFILE="$(cd "$(dirname "$0")" && pwd)/Brewfile"

setup_brew_env() {
    if [ "$OS" = "Darwin" ]; then
        if [ -x /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -x /usr/local/bin/brew ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    elif [ "$OS" = "Linux" ]; then
        if [ -x "$HOME/.linuxbrew/bin/brew" ]; then
            eval "$($HOME/.linuxbrew/bin/brew shellenv)"
        elif [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
            eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        fi
    fi
}

setup_brew_env

if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found, skipping brew bundle."
    exit 0
fi

if [ -f "$BREWFILE" ]; then
    echo "Installing from $BREWFILE..."
    brew bundle --file="$BREWFILE"
else
    echo "No Brewfile at $BREWFILE, skipping."
fi
