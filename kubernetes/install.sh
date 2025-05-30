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

install_kubernetes_ubuntu() {
    echo "Installing Kubernetes (kubectl, kubeadm, minikube) on Ubuntu..."

    sudo apt update
    sudo apt install -y apt-transport-https ca-certificates curl

    curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    sudo apt-add-repository "deb https://apt.kubernetes.io/ kubernetes-xenial main"
    sudo apt update
    sudo apt install -y kubectl kubeadm kubelet

    sudo apt-mark hold kubectl kubeadm kubelet
}

install_kubernetes_macos() {
    echo "Installing Kubernetes (kubectl, minikube) on macOS..."
    brew install kubectl minikube
}

install_minikube() {
    echo "Installing Minikube..."

    if [ "$OS" = "Linux" ]; then
        curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
        sudo mv minikube-linux-amd64 /usr/local/bin/minikube
        sudo chmod +x /usr/local/bin/minikube
    elif [ "$OS" = "Darwin" ]; then
        brew install minikube
    fi
}

setup_kubernetes_completions() {
    echo "Setting up Kubernetes (kubectl) Zsh completions..."

    mkdir -p "$HOME/.kubernetes/completions"

    if command -v kubectl >/dev/null 2>&1; then
        curl -sL https://raw.githubusercontent.com/kubernetes/kubernetes/master/cluster/kubectl.sh \
            -o "$HOME/.kubernetes/completions/_kubectl"
    fi
}

start_minikube() {
    echo "Starting Minikube..."
    if [ "$OS" = "Linux" ]; then
        minikube start --driver=docker
    elif [ "$OS" = "Darwin" ]; then
        minikube start
    fi
}

verify_installation() {
    echo "Verifying Kubernetes installation..."

    if command -v kubectl >/dev/null 2>&1; then
        echo "kubectl is installed: $(kubectl version --client --short)"
    else
        echo "kubectl installation failed!"
        exit 1
    fi

    if command -v kubeadm >/dev/null 2>&1; then
        echo "kubeadm is installed: $(kubeadm version -o short)"
    else
        echo "kubeadm installation failed!"
        exit 1
    fi

    if command -v minikube >/dev/null 2>&1; then
        echo "minikube is installed: $(minikube version)"
    else
        echo "minikube installation failed!"
        exit 1
    fi

    echo "All Kubernetes components are installed successfully!"
}

setup_brew_env
case "$OS" in
    Linux)
        if grep -qi "ubuntu" /etc/os-release; then
            install_kubernetes_ubuntu
        else
            echo "Unsupported Linux distribution."
            exit 1
        fi
        ;;
    Darwin)
        install_kubernetes_macos
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

install_minikube
setup_kubernetes_completions
start_minikube
verify_installation

echo "Kubernetes (kubectl, kubeadm, minikube) installation and setup completed successfully!"

