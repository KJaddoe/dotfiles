#!/bin/bash

set -e

OS=$(uname -s)

install_ag_ubuntu() {
    echo "Installing The Silver Searcher (Ag) on Ubuntu..."
    sudo apt update
    sudo apt install -y silversearcher-ag
}

install_ag_macos() {
    echo "Installing The Silver Searcher (Ag) on macOS..."

    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
    fi

    brew install the_silver_searcher
}

verify_installation() {
    echo "Verifying installation..."

    if command -v ag >/dev/null 2>&1; then
        echo "The Silver Searcher (Ag) is installed: : $(ag --version)"
    else
        echo "The Silver Searcher (Ag) installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_ag_ubuntu
        else
            echo "Unsupported Linux distribution. You may need to build from source."
            exit 1
        fi
        ;;
    Darwin)
        install_ag_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
echo "The Silver Searcher (Ag) installation completed!"
