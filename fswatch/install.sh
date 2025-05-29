#!/bin/bash

set -e

OS="$(uname)"

install_fswatch_ubuntu() {
    echo "Installing fswatch on Ubuntu..."
    sudo apt update
    sudo apt install -y fswatch
}

install_fswatch_macos() {
    echo "Installing fswatch on macOS..."
    brew install fswatch
}

verify_installation() {
    echo "Verifying installation..."

    if command -v fswatch >/dev/null 2>&1; then
        echo "fswatch is installed: $(fswatch --version)"
    else
        echo "fswatch installation failed!"
        exit 1
    fi

    echo "fswatch installation completed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_fswatch_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_fswatch_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
