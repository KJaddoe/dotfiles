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

install_git_ubuntu() {
    echo "Installing Git on Ubuntu..."
    sudo apt update
    sudo apt install -y git
}

install_git_macos() {
    echo "Installing Git on macOS..."
    brew install git
}

configure_git_diff() {
    echo "Configuring Git with diff-so-fancy..."
    if command -v diff-so-fancy >/dev/null 2>&1; then
        git config --global core.pager "diff-so-fancy | less --tabs=4 -RFX"
        echo "Git configured with diff-so-fancy pager."
    else
        echo "diff-so-fancy not found. Skipping Git pager configuration."
    fi
}

verify_installation() {
    echo "Verifying installation..."

    if command -v git >/dev/null 2>&1; then
        echo "Git is installed: $(git --version)"
    else
        echo "Git installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_git_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_git_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

configure_git_diff
verify_installation

echo "Git installation and configuration completed successfully!"
