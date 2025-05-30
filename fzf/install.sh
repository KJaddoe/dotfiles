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

install_fzf_ubuntu() {
    echo "Installing fzf on Ubuntu..."
    sudo apt update
    sudo apt install -y fzf
}

install_fzf_macos() {
    echo "Installing fzf on macOS..."
    brew install fzf
}

setup_fzf_keybindings() {
    echo "Setting up fzf keybindings and completions..."

    if [ -f ~/.fzf.zsh ]; then
        source ~/.fzf.zsh
    else
        echo "fzf configuration not found. Running fzf installation script..."

        if [ "$OS" = "Darwin" ]; then
            if [ -x /opt/homebrew/bin/brew ]; then
                HOMEBREW_PREFIX="/opt/homebrew"
            elif [ -x /usr/local/bin/brew ]; then
                HOMEBREW_PREFIX="/usr/local"
            else
                echo "Homebrew not found! Cannot run fzf install script."
                exit 1
            fi

            FZF_INSTALL_SCRIPT="$HOMEBREW_PREFIX/opt/fzf/install"

            if [ -x "$FZF_INSTALL_SCRIPT" ]; then
                "$FZF_INSTALL_SCRIPT"
            else
                echo "fzf install script not found at $FZF_INSTALL_SCRIPT"
                exit 1
            fi

        elif [ "$OS" = "Linux" ]; then
            if [ -x /usr/share/doc/fzf/examples/install ]; then
                /usr/share/doc/fzf/examples/install
            else
                if command -v fzf >/dev/null 2>&1; then
                    fzf --install || {
                        echo "fzf install script not available"
                        exit 1
                    }
                else
                    echo "fzf install script not found on Ubuntu"
                    exit 1
                fi
            fi

        else
            echo "fzf install script setup is not supported on this OS by this script."
            exit 1
        fi
    fi
}

verify_installation() {
    echo "Verifying installation..."

    if command -v fzf >/dev/null 2>&1; then
        echo "fzf is installed: $(fzf --version)"
    else
        echo "fzf installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_fzf_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_fzf_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

setup_fzf_keybindings
verify_installation

echo "fzf installation and setup completed successfully!"
