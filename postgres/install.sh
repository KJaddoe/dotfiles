#!/bin/bash

set -e

OS="$(uname)"

install_postgresql_ubuntu() {
    echo "Installing PostgreSQL on Ubuntu..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
}

install_postgresql_macos() {
    echo "Installing PostgreSQL on macOS..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    fi
    brew install postgresql
}

start_postgresql_service() {
    echo "Starting PostgreSQL service..."
    if [ "$OS" = "Linux" ]; then
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
    elif [ "$OS" = "Darwin" ]; then
        brew services start postgresql
    fi
}

configure_postgresql() {
    echo "Setting up PostgreSQL..."

    if [ "$OS" = "Linux" ]; then
        sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
    elif [ "$OS" = "Darwin" ]; then
        psql -c "ALTER USER postgres PASSWORD 'postgres';"
    fi

    echo "PostgreSQL setup completed with password 'postgres'."
}

verify_installation() {
    echo "Verifying installation..."

    if command -v psql >/dev/null 2>&1; then
        echo "PostgreSQL is installed: $(psql --version)"
    else
        echo "PostgreSQL installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_postgresql_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_postgresql_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

start_postgresql_service
configure_postgresql

verify_installation
echo "PostgreSQL installation and setup completed successfully!"
