#!/bin/bash

set -e

OS=$(uname -s)

install_powerline_ubuntu() {
	echo "Installing Powerline on Ubuntu..."

	sudo apt update

	# Install pip3 if missing
	if ! command -v pip3 >/dev/null 2>&1; then
		echo "Installing python3-pip..."
		sudo apt install -y python3-pip
	fi

	# Install powerline-status using pip3 --user
	pip3 install --user powerline-status

	echo "Powerline installed for user $(whoami) in ~/.local/bin"
}

install_powerline_macos() {
	echo "Installing Powerline on macOS using pipx..."

	# Install pipx if missing
	if ! command -v pipx >/dev/null 2>&1; then
		echo "pipx not found, installing pipx via Homebrew..."
		brew install pipx
		# Add pipx to PATH for current shell
		export PATH="$HOME/.local/bin:$PATH"
	fi

	# Install powerline via pipx
	pipx install powerline-status || echo "Powerline already installed via pipx."

	echo "Powerline installed via pipx."
}

verify_installation() {
	echo "Verifying Powerline installation..."

	if command -v powerline >/dev/null 2>&1; then
		echo "Powerline is installed: $(powerline --version)"
	elif [ -x "$HOME/.local/bin/powerline" ]; then
		echo "Powerline installed in ~/.local/bin: $($HOME/.local/bin/powerline --version)"
	else
		echo "Powerline installation failed or 'powerline' is not in PATH."
		exit 1
	fi

	echo "Powerline installation verified successfully!"
}

setup_brew_env() {
	if [ "$OS" = "Darwin" ]; then
		if [ -x /opt/homebrew/bin/brew ]; then
			eval "$(/opt/homebrew/bin/brew shellenv)" # Apple Silicon
		elif [ -x /usr/local/bin/brew ]; then
			eval "$(/usr/local/bin/brew shellenv)" # Intel
		fi
	fi
}

setup_brew_env

case "$OS" in
Linux)
	if grep -qi "ubuntu" /etc/os-release; then
		install_powerline_ubuntu
	else
		echo "Unsupported Linux distribution. Please install Powerline manually."
		exit 1
	fi
	;;
Darwin)
	install_powerline_macos
	;;
*)
	echo "Unsupported OS: $OS"
	exit 1
	;;
esac

verify_installation
