#!/bin/sh

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

    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    fi

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
