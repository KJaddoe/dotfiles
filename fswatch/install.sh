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

install_fswatch_ubuntu() {
    echo "Installing fswatch on Ubuntu..."
    sudo apt update
    sudo apt install -y fswatch
}

install_fswatch_macos() {
    echo "Installing fswatch on macOS..."
    brew install fswatch
}

verify_installation() {
    echo "Verifying installation..."

    if command -v fswatch >/dev/null 2>&1; then
        echo "fswatch is installed: $(fswatch --version)"
    else
        echo "fswatch installation failed!"
        exit 1
    fi

    echo "fswatch installation completed successfully!"
}

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_fswatch_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_fswatch_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
