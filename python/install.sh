#!/bin/bash

set -e

OS="$(uname)"

# Define global Python packages list
PYTHON_PACKAGES=(
    "black"
	"isort"
    "rshell"
    "pylint"
    "jedi"
    "pynvim"
    "jedi_language_server"
    "ansible-dev-tools"
    "ansible-lint"
)

install_python_ubuntu() {
    echo "Installing Python and pip on Ubuntu..."
    sudo apt update
    sudo apt install -y python3 python3-pip
}

install_python_macos() {
    echo "Installing Python and pip on macOS..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    fi
    brew install python
}

install_python_packages() {
    echo "Installing default Python packages..."

    pip3 install --upgrade pip
    pip3 install "${PYTHON_PACKAGES[@]}"
}

verify_installation() {
    echo "Verifying installation..."

    if command -v python3 >/dev/null 2>&1; then
        echo "Python is installed: $(python3 --version)"
    else
        echo "Python installation failed!"
        exit 1
    fi

    if command -v pip3 >/dev/null 2>&1; then
        echo "pip is installed: $(pip3 --version)"
    else
        echo "pip installation failed!"
        exit 1
    fi

    for package in "${PYTHON_PACKAGES[@]}"; do
        if pip3 show "$package" >/dev/null 2>&1; then
            echo "$package is installed"
        else
            echo "$package installation failed!"
            exit 1
        fi
    done

    echo "All components are installed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_python_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_python_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

install_python_packages
verify_installation

echo "Python, pip, and Python packages installation completed successfully!"
