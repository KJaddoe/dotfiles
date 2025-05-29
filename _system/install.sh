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

install_xcode_macos() {
    if ! command -v gcc >/dev/null 2>&1; then
        echo "Installing Xcode Command Line Tools..."
        xcode-select --install
    fi
}

install_ansible_macos() {
    if ! command -v ansible >/dev/null 2>&1; then
        echo "Installing Ansible..."
        brew install ansible
    else
        echo "Upgrading Ansible..."
        brew upgrade ansible
    fi
}

install_ansible_ubuntu() {
    if ! command -v ansible >/dev/null 2>&1; then
        echo "Installing Ansible..."
        sudo apt-get update
        sudo apt-get install -y software-properties-common
        sudo add-apt-repository --yes --update ppa:ansible/ansible
        sudo apt-get install -y ansible
    fi
}

setup_brew_env
case "$OS" in
    Darwin)
        install_xcode_macos
        install_ansible_macos
        ;;
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_ansible_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

if ! command -v ansible >/dev/null 2>&1; then
    echo "Ansible installation failed or is not supported on this system."
    exit 1
fi

ANSIBLE_DIR="$(pwd -P)/_system"
echo "Running Ansible..."
ansible-galaxy install -r "$ANSIBLE_DIR/requirements.yml" --force
ansible-playbook "$ANSIBLE_DIR/main.yml" -K
