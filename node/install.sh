#!/bin/bash

set -e

OS="$(uname)"

NPM_PACKAGES=(
	"eslint"
	"eslint_d"
	"prettier"
	"typescript"
	"tern"
	"diff-so-fancy"
	"@angular/cli"
	"tree-sitter-cli"
	"typescript-language-server"
	"vscode-langservers-extracted"
	"dockerfile-language-server-nodejs"
	"yaml-language-server"
	"diagnostic-languageserver"
	"@angular/language-server"
	"emmet-ls"
	"bash-language-server"
	"vim-language-server"
	"sql-formatter"
)

install_nvm_ubuntu() {
	echo "Installing NVM on Ubuntu..."
	curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
	source $NVIM_DIR/nvm.sh
	nvm install --lts
}

install_nvm_macos() {
	echo "Installing NVM on macOS..."
	if ! command -v brew >/dev/null 2>&1; then
		echo "Homebrew not found! Installing Homebrew..."
		curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
	fi
	brew install nvm
	mkdir -p "$HOME/.nvm"
	nvm install --lts
}

install_npm_packages() {
	echo "Installing specified npm packages..."
	npm install -g "${NPM_PACKAGES[@]}"
}

verify_installation() {
	echo "Verifying installation..."

	if command -v nvm >/dev/null 2>&1; then
		echo "NVM is installed"
	else
		echo "NVM installation failed!"
		exit 1
	fi

	if command -v node >/dev/null 2>&1; then
		echo "Node.js is installed: $(node -v)"
	else
		echo "Node.js installation failed!"
		exit 1
	fi

	if command -v npm >/dev/null 2>&1; then
		echo "npm is installed: $(npm -v)"
	else
		echo "npm installation failed!"
		exit 1
	fi

	for package in "${NPM_PACKAGES[@]}"; do
		if npm list -g --depth=0 "$package" >/dev/null 2>&1; then
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
		install_nvm_ubuntu
	else
		echo "Unsupported Linux distribution."
		exit 1
	fi
	;;
Darwin)
	install_nvm_macos
	;;
*)
	echo "Unsupported OS: $OS"
	exit 1
	;;
esac

install_npm_packages
verify_installation

echo "NVM, Node.js LTS, and npm packages installation completed successfully!"
