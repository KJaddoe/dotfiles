#!/bin/bash

set -e

OS="$(uname)"

setup_brew_env() {
    if [ "$OS" = "Darwin" ]; then
        if [ -x /opt/homebrew/bin/brew ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"  # Apple Silicon
        elif [ -x /usr/local/bin/brew ]; then
            eval "$(/usr/local/bin/brew shellenv)"     # Intel
        fi
    elif [ "$OS" = "Linux" ]; then
        if [ -x "$HOME/.linuxbrew/bin/brew" ]; then
            eval "$($HOME/.linuxbrew/bin/brew shellenv)"
        elif [ -x /home/linuxbrew/.linuxbrew/bin/brew ]; then
            eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
        fi
    fi
}

# Define a default directory for Zsh plugins (if you don't use Oh My Zsh)
ZSH_CUSTOM="$HOME/.zsh_plugins"

install_antidote_ubuntu() {
    echo "Installing Antidote on Ubuntu..."
    sudo apt update
    sudo apt install -y git curl
}

install_antidote_macos() {
    echo "Installing Antidote on macOS..."
    brew install git curl
}

install_antidote() {
    echo "Installing Antidote plugin manager..."

    if [ ! -d "$ZSH_CUSTOM/antidote" ]; then
        git clone https://github.com/mattmc3/antidote.git "$ZSH_CUSTOM/antidote"
    else
        echo "Antidote is already installed."
    fi
}

verify_installation() {
    echo "Verifying installation..."

    if command -v antidote >/dev/null 2>&1; then
        echo "Antidote is installed: : $(antidote --version)"
    else
        echo "Antidote installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
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

install_antidote
verify_installation

echo "Antidote installation and setup completed successfully!"
