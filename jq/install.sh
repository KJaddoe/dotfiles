#!/bin/bash

set -e

OS=$(uname -s)

install_jq_ubuntu() {
    echo "Installing jq on Ubuntu..."
    sudo apt update
    sudo apt install -y jq
}

install_jq_macos() {
    echo "Installing jq on macOS..."
    brew install jq
}

verify_installation() {
    echo "Verifying installation..."

    if command -v jq >/dev/null 2>&1; then
        echo "jq is installed: $(jq --version)"
    else
        echo "jq installation failed!"
        exit 1
    fi

    echo "jq installation completed successfully!"
}

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_jq_ubuntu
        else
            echo "Unsupported Linux distribution. You may need to install manually."
            exit 1
        fi
        ;;
    Darwin)
        install_jq_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
