#!/bin/bash

set -e

OS="$(uname)"

install_fzf_ubuntu() {
    echo "Installing fzf on Ubuntu..."
    sudo apt update
    sudo apt install -y fzf
}

install_fzf_macos() {
    echo "Installing fzf on macOS..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
    fi
    brew install fzf
}

setup_fzf_keybindings() {
    echo "Setting up fzf keybindings and completions..."

    if [ -f ~/.fzf.zsh ]; then
        source ~/.fzf.zsh
    else
        echo "fzf configuration not found. Running fzf installation script..."
        /usr/local/opt/fzf/install
    fi
}

verify_installation() {
    echo "Verifying installation..."

    if command -v fzf >/dev/null 2>&1; then
        echo "fzf is installed: $(fzf --version)"
    else
        echo "fzf installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_fzf_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_fzf_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

setup_fzf_keybindings
verify_installation

echo "fzf installation and setup completed successfully!"
