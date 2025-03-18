#!/bin/sh

set -e

OS=$(uname -s)

install_sql_formatter_ubuntu() {
    echo "Installing sql-formatter on Ubuntu..."
    if ! command -v npm >/dev/null 2>&1; then
        echo "Node.js and npm not found! Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt install -y nodejs
    fi
    npm install -g sql-formatter
}

install_sql_formatter_macos() {
    echo "Installing sql-formatter on macOS..."
    if ! command -v npm >/dev/null 2>&1; then
        echo "Node.js and npm not found! Installing Node.js..."
        brew install node
    fi
    npm install -g sql-formatter
}

verify_installation() {
    echo "Verifying installation..."

    if command -v sql-formatter >/dev/null 2>&1; then
        echo "sql-formatter is installed: $(sql-formatter --version 2>/dev/null || echo 'Installed')"
    else
        echo "sql-formatter installation failed!"
        exit 1
    fi

    echo "sql-formatter installation completed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_sql_formatter_ubuntu
        else
            echo "Unsupported Linux distribution. You may need to install manually."
            exit 1
        fi
        ;;
    Darwin)
        install_sql_formatter_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation
