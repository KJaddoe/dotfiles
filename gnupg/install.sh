#!/bin/bash

set -e

OS=$(uname -s)

install_gpg_ubuntu() {
	echo "Installing GnuPG on Ubuntu..."
	sudo apt update
	sudo apt install -y gnupg
}

install_gpg_macos() {
	echo "Installing GnuPG on macOS..."
	brew install gnupg
}

verify_installation() {
	echo "Verifying installation..."

	if command -v gpg >/dev/null 2>&1; then
		echo "GnuPG is installed: $(gpg --version | head -n 1)"
	else
		echo "GnuPG installation failed!"
		exit 1
	fi

	echo "All components are installed successfully!"
}

setup_brew_env() {
	if [ "$OS" = "Darwin" ]; then
		if [ -x /opt/homebrew/bin/brew ]; then
			eval "$(/opt/homebrew/bin/brew shellenv)" # Apple Silicon
		elif [ -x /usr/local/bin/brew ]; then
			eval "$(/usr/local/bin/brew shellenv)" # Intel
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
		install_gpg_ubuntu
	else
		echo "Unsupported Linux distribution. You may need to build from source."
		exit 1
	fi
	;;
Darwin)
	install_gpg_macos
	;;
*)
	echo "Unsupported OS: $OS"
	exit 1
	;;
esac

verify_installation
