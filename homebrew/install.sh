#!/bin/bash

set -e

OS=$(uname -s)

install_homebrew_ubuntu() {
    echo "Installing Homebrew on Ubuntu..."

    # Install dependencies
    sudo apt update
    sudo apt install -y build-essential procps curl file git

    # Run the Homebrew installation script
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
}

install_homebrew_macos() {
    echo "Installing Homebrew on macOS..."

    # Run the Homebrew installation script
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
}

verify_installation() {
    echo "Verifying Homebrew installation..."

    if command -v brew >/dev/null 2>&1; then
        echo "Homebrew is installed: $(brew --version | head -n1)"
    else
        echo "Homebrew installation failed!"
        exit 1
    fi

    echo "Homebrew installation completed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_homebrew_ubuntu
        else
            echo "Unsupported Linux distribution. You may need to install Homebrew manually."
            exit 1
        fi
        ;;
    Darwin)
        install_homebrew_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation

