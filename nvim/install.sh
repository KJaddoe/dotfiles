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
    brew install neovim

    echo "Configuring Neovim as the default editor..."
    sudo ln -sf "$(which nvim)" /usr/local/bin/vi
    sudo ln -sf "$(which nvim)" /usr/local/bin/vim
    sudo ln -sf "$(which nvim)" /usr/local/bin/editor
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

setup_brew_env
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
