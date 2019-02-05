#!/bin/sh
if command -v nvm >/dev/null 2>&1; then
  wget -qO- https://raw.githubusercontent.com/creationix/nvm/v0.34.00/install.sh | zsh
fi
