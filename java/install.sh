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

install_java_ubuntu() {
    echo "Installing OpenJDK on Ubuntu..."
    sudo apt update
    sudo apt install -y openjdk-17-jdk  # Change this to the latest LTS version if needed
}

install_java_macos() {
    echo "Installing OpenJDK on macOS..."
    brew install openjdk@17  # Change this to the latest LTS version if needed
}

verify_installation() {
    echo "Verifying installation..."

    if command -v node >/dev/null 2>&1; then
        echo "Java OpenJDK is installed: $(java --version)"
    else
        echo "Java OpenJDK installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_java_ubuntu
            setup_java_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_java_macos
        setup_java_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation

echo "Java OpenJDK installation completed successfully!"
