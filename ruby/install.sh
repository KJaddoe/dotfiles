#!/bin/bash

set -e

OS="$(uname)"

install_ruby_ubuntu() {
    echo "Installing Ruby on Ubuntu..."
    sudo apt update
    sudo apt install -y ruby-full
}

install_ruby_macos() {
    echo "Installing Ruby on macOS..."

    # Check if Homebrew is installed
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
    fi

    brew install ruby
}

verify_installation() {
    echo "Verifying installation..."

    if command -v ruby >/dev/null 2>&1; then
        echo "Ruby is installed: $(ruby -v)"
    else
        echo "Ruby installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

# Determine OS and install Ruby accordingly
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_ruby_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_ruby_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation

echo "Ruby installation completed successfully!"
