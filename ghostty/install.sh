#!/bin/bash

set -e

OS=$(uname -s)

install_ghostty_ubuntu() {
	echo "Installing Ghostty on Ubuntu using Homebrew..."
	if ! command -v brew >/dev/null 2>&1; then
		echo "Homebrew not found. Installing Homebrew..."
		/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
		setup_brew_env
	fi
	brew install ghostty
}

install_ghostty_macos() {
	echo "Installing Ghostty on macOS using Homebrew..."
	if ! command -v brew >/dev/null 2>&1; then
		echo "Homebrew not found. Installing Homebrew..."
		/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
		setup_brew_env
	fi
	brew install ghostty
}

verify_installation() {
	echo "Verifying Ghostty installation..."

	if command -v ghostty >/dev/null 2>&1; then
		echo "Ghostty is installed: $(ghostty --version || echo '(version not available)')"
	else
		echo "Ghostty installation failed!"
		exit 1
	fi

	echo "Ghostty installed successfully!"
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
		install_ghostty_ubuntu
	else
		echo "Unsupported Linux distribution. Try using Homebrew or building Ghostty from source: https://github.com/mitchellh/ghostty"
		exit 1
	fi
	;;
Darwin)
	install_ghostty_macos
	;;
*)
	echo "Unsupported OS: $OS"
	exit 1
	;;
esac

verify_installation
