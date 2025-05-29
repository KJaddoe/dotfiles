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
