#!/bin/bash

set -e

OS="$(uname)"

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
