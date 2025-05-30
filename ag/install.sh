#!/bin/bash

set -e

OS=$(uname -s)

install_ag_ubuntu() {
    echo "Installing The Silver Searcher (Ag) on Ubuntu..."
    sudo apt update
    sudo apt install -y silversearcher-ag
}

install_ag_macos() {
    echo "Installing The Silver Searcher (Ag) on macOS..."
    brew install the_silver_searcher
}

verify_installation() {
    echo "Verifying installation..."

    if command -v ag >/dev/null 2>&1; then
        echo "The Silver Searcher (Ag) is installed: : $(ag --version)"
    else
        echo "The Silver Searcher (Ag) installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

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

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_ag_ubuntu
        else
            echo "Unsupported Linux distribution. You may need to build from source."
            exit 1
        fi
        ;;
    Darwin)
        install_ag_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
echo "The Silver Searcher (Ag) installation completed!"
