#!/bin/sh

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
	if ! command -v brew >/dev/null 2>&1; then
		echo "Homebrew not found! Installing Homebrew..."
		curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
	fi
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
