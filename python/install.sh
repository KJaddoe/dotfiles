#!/bin/bash

set -e

OS="$(uname)"

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
PYTHON_VERSION="3.11.9"

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

install_pyenv_ubuntu() {
	echo "Installing pyenv on Ubuntu..."

	sudo apt update
	sudo apt install -y make build-essential libssl-dev zlib1g-dev \
		libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
		libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

	if [ ! -d "$HOME/.pyenv" ]; then
		curl https://pyenv.run | bash
	fi

	export PATH="$HOME/.pyenv/bin:$PATH"
	eval "$(pyenv init -)"
	eval "$(pyenv virtualenv-init -)"
}

install_pyenv_macos() {
	echo "Installing pyenv on macOS..."

	brew install pyenv pyenv-virtualenv

	export PATH="$HOME/.pyenv/bin:$PATH"
	eval "$(pyenv init -)"
	eval "$(pyenv virtualenv-init -)"
}

verify_pyenv_installation() {
	echo "Verifying pyenv installation..."
	export PATH="$HOME/.pyenv/bin:$PATH"
	eval "$(pyenv init -)" >/dev/null
	eval "$(pyenv virtualenv-init -)" >/dev/null

	if ! command -v pyenv >/dev/null 2>&1; then
		echo "pyenv installation failed or is not in PATH!"
		exit 1
	fi

	echo "pyenv is installed: $(pyenv --version)"
}

install_python_with_pyenv() {
	echo "Installing Python $PYTHON_VERSION via pyenv..."

	if ! pyenv versions | grep -q "$PYTHON_VERSION"; then
		pyenv install "$PYTHON_VERSION"
	fi

	pyenv global "$PYTHON_VERSION"
	eval "$(pyenv init -)"
	eval "$(pyenv virtualenv-init -)"

	echo "Using Python: $(python --version)"
}

install_python_packages() {
	echo "Installing Python packages with pip..."

	pip install --upgrade pip
	pip install "${PYTHON_PACKAGES[@]}"
}

verify_installation() {
	echo "Verifying Python and package installation..."

	python --version
	pip --version

	for package in "${PYTHON_PACKAGES[@]}"; do
		if pip show "$package" >/dev/null 2>&1; then
			echo "$package is installed"
		else
			echo "$package installation failed!"
			exit 1
		fi
	done
}

# Detect OS and install pyenv
setup_brew_env
case "$OS" in
Linux)
	if grep -qi "ubuntu" /etc/os-release; then
		install_pyenv_ubuntu
	else
		echo "Unsupported Linux distribution."
		exit 1
	fi
	;;
Darwin)
	install_pyenv_macos
	;;
*)
	echo "Unsupported OS: $OS"
	exit 1
	;;
esac

verify_pyenv_installation
install_python_with_pyenv
install_python_packages
verify_installation

echo "Python $PYTHON_VERSION and packages installed successfully using pyenv!"
