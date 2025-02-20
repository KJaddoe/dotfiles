#!/bin/sh

set -e

OS="$(uname)"

install_java_ubuntu() {
    echo "Installing OpenJDK on Ubuntu..."
    sudo apt update
    sudo apt install -y openjdk-17-jdk  # Change this to the latest LTS version if needed
}

install_java_macos() {
    echo "Installing OpenJDK on macOS..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    fi
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
