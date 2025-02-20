#!/bin/sh

set -e

OS="$(uname)"

install_xcode_macos() {
    if ! command -v gcc >/dev/null 2>&1; then
        echo "Installing Xcode Command Line Tools..."
        xcode-select --install
    fi
}

install_homebrew() {
    if ! command -v brew >/dev/null 2>&1; then
        echo "Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    else
        echo "Updating Homebrew..."
        brew update
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

case "$OS" in
    Darwin)
        install_xcode_macos
        install_homebrew
        install_ansible_macos
        ;;
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_homebrew
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
