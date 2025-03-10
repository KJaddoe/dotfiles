#!/bin/sh

set -e

OS="$(uname)"

install_dotnet_ubuntu() {
    echo "Installing .NET on Ubuntu..."
    sudo apt update
    sudo apt install -y dotnet-sdk-8.0
    install_csharp_ls
}

install_dotnet_macos() {
    echo "Installing .NET on macOS..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | bash
    fi
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
