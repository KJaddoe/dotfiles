#!/bin/bash

set -e

OS=$(uname -s)

install_stylua_ubuntu() {
	echo "Installing stylua on Ubuntu..."
	sudo apt update
	sudo apt install -y curl unzip

	curl -L "https://github.com/JohnnyMorganz/StyLua/releases/download/v2.0.2/stylua-linux-x86_64.zip" -o "$HOME/stylua-linux-x86_64.zip"
	unzip -o "$HOME/stylua-linux-x86_64.zip" -d "$HOME"
	sudo mv "$HOME/stylua" /usr/local/bin/
	rm "$HOME/stylua-linux-x86_64.zip"
}

install_stylua_macos() {
	echo "Installing stylua on macOS..."
	brew install stylua
}

verify_installation() {
	echo "Verifying installation..."

	if command -v stylua >/dev/null 2>&1; then
		echo "stylua is installed: $(stylua --version)"
	else
		echo "stylua installation failed!"
		exit 1
	fi

	echo "stylua installation completed successfully!"
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
		install_stylua_ubuntu
	else
		echo "Unsupported Linux distribution. You may need to install manually."
		exit 1
	fi
	;;
Darwin)
	install_stylua_macos
	;;
*)
	echo "Unsupported OS: $OS"
	exit 1
	;;
esac

verify_installation
