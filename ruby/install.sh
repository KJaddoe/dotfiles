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

install_ruby_ubuntu() {
    echo "Installing Ruby on Ubuntu..."
    sudo apt update
    sudo apt install -y ruby-full
}

install_ruby_macos() {
    echo "Installing Ruby on macOS..."
    brew install ruby
}

verify_installation() {
    echo "Verifying installation..."

    if command -v ruby >/dev/null 2>&1; then
        echo "Ruby is installed: $(ruby -v)"
    else
        echo "Ruby installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

# Determine OS and install Ruby accordingly
setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_ruby_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_ruby_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation

echo "Ruby installation completed successfully!"
