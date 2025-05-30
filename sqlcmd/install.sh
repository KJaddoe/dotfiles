#!/bin/bash

set -e

OS=$(uname -s)

install_sqlcmd_ubuntu() {
    echo "Installing sqlcmd on Ubuntu..."

    curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
    sudo add-apt-repository "$(curl -fsSL https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list)"
    sudo apt update
    sudo apt install -y mssql-tools unixodbc-dev
}

install_sqlcmd_macos() {
    echo "Installing sqlcmd on macOS..."
    brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
    brew install sqlcmd
}

verify_installation() {
    echo "Verifying installation..."

    if command -v sqlcmd >/dev/null 2>&1; then
        echo "sqlcmd is installed: $(sqlcmd -? | head -n 1)"
    else
        echo "sqlcmd installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

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

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_sqlcmd_ubuntu
        else
            echo "Unsupported Linux distribution. You may need to install manually."
            exit 1
        fi
        ;;
    Darwin)
        install_sqlcmd_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation

echo "sqlcmd installation completed!"
