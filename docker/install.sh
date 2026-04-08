#!/usr/bin/env bash
set -e

OS="$(uname)"

log() {
  echo "==> $1"
}

install_docker_linux() {
  log "Installing Docker (Linux)"

  sudo apt update
  sudo apt install -y ca-certificates curl gnupg

  sudo install -m 0755 -d /etc/apt/keyrings

  if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  fi

  echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt update

  sudo apt install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

  sudo usermod -aG docker "$USER"

  log "Docker installed"
}

install_docker_macos() {
  log "Installing Docker (macOS)"

  if ! command -v brew >/dev/null; then
    echo "Homebrew required but not installed."
    exit 1
  fi

  brew install --cask docker
}

setup_zsh_completions() {
  log "Installing Zsh completions"

  mkdir -p "$HOME/.docker/completions"

  if command -v docker >/dev/null; then
    docker completion zsh > "$HOME/.docker/completions/_docker"
  fi
}

verify_install() {
  log "Verifying Docker installation"

  docker --version
  docker compose version

  echo
  echo "Docker installed successfully."
  echo
  echo "⚠️  You may need to log out and log back in for docker group changes."
}

main() {

  case "$OS" in
    Linux)
      if grep -qi ubuntu /etc/os-release; then
        install_docker_linux
      else
        echo "Unsupported Linux distribution"
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

  setup_zsh_completions
  verify_install
}

main