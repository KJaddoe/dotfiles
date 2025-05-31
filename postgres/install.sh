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

install_postgresql_ubuntu() {
    echo "Installing PostgreSQL on Ubuntu..."
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
}

install_postgresql_macos() {
    echo "Installing PostgreSQL on macOS..."
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

setup_brew_env
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
