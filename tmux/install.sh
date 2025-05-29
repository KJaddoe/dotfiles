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
TPM_DIR="$HOME/.tmux/plugins/tpm"

install_tmux_ubuntu() {
    echo "Installing tmux on Ubuntu..."
    sudo apt update
    sudo apt install -y tmux
}

install_tmux_macos() {
    echo "Installing tmux on macOS..."
    brew install tmux
}

install_tpm() {
    echo "Installing TPM (Tmux Plugin Manager)..."

    if [ ! -d "$TPM_DIR" ]; then
        git clone https://github.com/tmux-plugins/tpm "$TPM_DIR"
        echo "TPM installed successfully."
    else
        echo "TPM is already installed."
    fi
}

verify_installation() {
    echo "Verifying installation..."

    if command -v tmux >/dev/null 2>&1; then
        echo "Tmux is installed: $(tmux -v)"
    else
        echo "Tmux installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_tmux_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_tmux_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

install_tpm
verify_installation

echo "Tmux and TPM installation completed successfully!"
