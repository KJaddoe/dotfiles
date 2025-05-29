#!/bin/bash

set -e

OS=$(uname -s)

install_pgformat_ubuntu() {
    echo "Installing pg_format on Ubuntu..."
    sudo apt update
    sudo apt install -y pgformatter
}

install_pgformat_macos() {
    echo "Installing pg_format on macOS..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    fi
    brew install pgformatter
}

verify_installation() {
    echo "Verifying installation..."

    if command -v pg_format >/dev/null 2>&1; then
        echo "pg_format is installed: $(pg_format --version)"
    else
        echo "pg_format installation failed!"
        exit 1
    fi

    echo "pg_format installation completed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_pgformat_ubuntu
        else
            echo "Unsupported Linux distribution. You may need to install manually."
            exit 1
        fi
        ;;
    Darwin)
        install_pgformat_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
