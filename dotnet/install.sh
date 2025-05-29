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

install_dotnet_ubuntu() {
    echo "Installing .NET on Ubuntu..."
    sudo apt update
    sudo apt install -y dotnet-sdk-8.0
    install_csharp_ls
}

install_dotnet_macos() {
    echo "Installing .NET on macOS..."
    brew install dotnet-sdk
    install_csharp_ls
}

install_csharp_ls() {
    if ! command -v dotnet >/dev/null 2>&1; then
        echo ".NET is not installed! Skipping C# Language Server installation."
        return
    fi
    echo "Installing C# Language Server..."
    dotnet tool install --global csharp-ls
}

verify_installation() {
    echo "Verifying installation..."

    if command -v dotnet >/dev/null 2>&1; then
        echo ".NET is installed: $(dotnet --version)"
    else
        echo ".NET installation failed!"
        exit 1
    fi

    if command -v csharp-ls >/dev/null 2>&1; then
        echo "C# Language Server is installed: $(csharp-ls --version)"
    else
        echo "C# Language Server installation failed!"
        exit 1
    fi

    echo ".NET and C# Language Server installation completed successfully!"
}

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_dotnet_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_dotnet_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
