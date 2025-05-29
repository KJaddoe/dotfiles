#!/bin/bash

set -e

OS="$(uname)"

install_git_ubuntu() {
    echo "Installing Git on Ubuntu..."
    sudo apt update
    sudo apt install -y git
}

install_git_macos() {
    echo "Installing Git on macOS..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
    fi
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
