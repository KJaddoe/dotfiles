#!/bin/sh

set -e

OS="$(uname)"
TPM_DIR="$HOME/.tmux/plugins/tpm"

install_tmux_ubuntu() {
    echo "Installing tmux on Ubuntu..."
    sudo apt update
    sudo apt install -y tmux
}

install_tmux_macos() {
    echo "Installing tmux on macOS..."

    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    fi

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
