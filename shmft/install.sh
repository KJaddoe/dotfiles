#!/bin/bash

set -e

OS=$(uname -s)

install_shfmt_ubuntu() {
    echo "Installing shfmt on Ubuntu..."
    sudo apt update
    sudo apt install -y shfmt
}

install_shfmt_macos() {
    echo "Installing shfmt on macOS..."
    brew install shfmt
}

verify_installation() {
    echo "Verifying installation..."

    if command -v shfmt >/dev/null 2>&1; then
        echo "shfmt is installed: $(shfmt --version)"
    else
        echo "shfmt installation failed!"
        exit 1
    fi

    echo "shfmt installation completed successfully!"
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
            install_shfmt_ubuntu
        else
            echo "Unsupported Linux distribution. You may need to install manually."
            exit 1
        fi
        ;;
    Darwin)
        install_shfmt_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
