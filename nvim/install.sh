#!/bin/bash

set -e

OS="$(uname)"

install_neovim_ubuntu() {
    echo "Installing Neovim on Ubuntu..."
    sudo apt update
    sudo apt install -y software-properties-common
    sudo add-apt-repository --yes --update ppa:neovim-ppa/unstable
    sudo apt install -y neovim

	 echo "Configuring Neovim as the default editor..."
    sudo update-alternatives --install /usr/bin/vi vi /usr/bin/nvim 60
    sudo update-alternatives --install /usr/bin/vim vim /usr/bin/nvim 60
    sudo update-alternatives --install /usr/bin/editor editor /usr/bin/nvim 60
    sudo update-alternatives --set vi /usr/bin/nvim
    sudo update-alternatives --set vim /usr/bin/nvim
    sudo update-alternatives --set editor /usr/bin/nvim
}

install_neovim_macos() {
    echo "Installing Neovim on macOS..."

    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    fi

    brew install neovim

    echo "Configuring Neovim as the default editor..."
    ln -sf "$(which nvim)" /usr/local/bin/vi
    ln -sf "$(which nvim)" /usr/local/bin/vim
    ln -sf "$(which nvim)" /usr/local/bin/editor
}

verify_installation() {
    echo "Verifying installation..."

    if command -v nvim >/dev/null 2>&1; then
        echo "Neovim is installed: $(nvim --version)"
    else
        echo "Neovim installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_neovim_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_neovim_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

verify_installation

echo "Neovim installation completed successfully!"
