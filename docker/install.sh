#!/bin/sh

set -e

OS="$(uname)"

install_docker_ubuntu() {
    echo "Installing Docker on Ubuntu..."
    sudo apt update
    sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
}

install_docker_macos() {
    echo "Installing Docker on macOS..."
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found! Installing Homebrew..."
        curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh | sh
    fi
    brew install --cask docker
}

install_docker_compose() {
    echo "Installing Docker Compose..."
    if [ "$OS" = "Linux" ]; then
        curl -L "https://github.com/docker/compose/releases/download/$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name)/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    elif [ "$OS" = "Darwin" ]; then
        brew install docker-compose
    fi
}

install_docker_machine() {
    echo "Installing Docker Machine..."
    if [ "$OS" = "Linux" ]; then
        curl -L https://github.com/docker/machine/releases/download/v0.16.2/docker-machine-$(uname -s)-$(uname -m) > /usr/local/bin/docker-machine
        sudo chmod +x /usr/local/bin/docker-machine
    elif [ "$OS" = "Darwin" ]; then
        brew install docker-machine
    fi
}

setup_docker_completions() {
    echo "Setting up Docker, Docker Compose, and Docker Machine Zsh completions..."

    mkdir -p "$HOME/.docker/completions"

    if command -v docker-compose >/dev/null 2>&1; then
        curl -sL https://raw.githubusercontent.com/docker/compose/master/contrib/completion/zsh/_docker-compose \
            -o "$HOME/.docker/completions/_docker-compose"
    fi
    if command -v docker-machine >/dev/null 2>&1; then
        curl -sL https://raw.githubusercontent.com/docker/machine/master/contrib/completion/zsh/_docker-machine \
            -o "$HOME/.docker/completions/_docker-machine"
    fi
    if command -v docker >/dev/null 2>&1; then
        curl -sL https://raw.githubusercontent.com/docker/cli/master/contrib/completion/zsh/_docker \
            -o "$HOME/.docker/completions/_docker"
    fi
}

verify_installation() {
    echo "Verifying installation..."

    if command -v docker >/dev/null 2>&1; then
        echo "Docker is installed: $(docker --version)"
    else
        echo "Docker installation failed!"
        exit 1
    fi

    if command -v docker-compose >/dev/null 2>&1; then
        echo "Docker Compose is installed: $(docker-compose --version)"
    else
        echo "Docker Compose installation failed!"
        exit 1
    fi

    if command -v docker-machine >/dev/null 2>&1; then
        echo "Docker Machine is installed: $(docker-machine --version)"
    else
        echo "Docker Machine installation failed!"
        exit 1
    fi

    echo "All components are installed successfully!"
}

case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_docker_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_docker_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

install_docker_compose
install_docker_machine
setup_docker_completions
verify_installation

echo "Docker, Docker Compose, Docker Machine installation and setup completed successfully!"
