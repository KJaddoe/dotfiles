#!/bin/bash

set -e

OS="$(uname)"
ZSH_CUSTOM="$HOME/.zsh_plugins"
ANTIDOTE_DIR="$ZSH_CUSTOM/antidote"

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

install_antidote_macos() {
    echo "Installing Antidote via Homebrew on macOS..."
    brew install antidote
}

install_antidote_ubuntu() {
    echo "Installing Antidote manually on Ubuntu..."
    mkdir -p "$ZSH_CUSTOM"
    if [ ! -d "$ANTIDOTE_DIR" ]; then
        git clone https://github.com/mattmc3/antidote.git "$ANTIDOTE_DIR"
    else
        echo "Antidote already installed at $ANTIDOTE_DIR"
    fi
}

verify_installation() {
    if [ "$OS" = "Darwin" ]; then
        if command -v antidote > /dev/null 2>&1; then
            echo "Antidote installed successfully (brew version)."
        else
            echo "Antidote installation failed on macOS."
            exit 1
        fi
    elif [ -f "$ANTIDOTE_DIR/antidote.zsh" ]; then
        echo "Antidote installed successfully at $ANTIDOTE_DIR"
    else
        echo "Antidote installation failed on Ubuntu."
        exit 1
    fi
}

setup_brew_env

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_antidote_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_antidote_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
