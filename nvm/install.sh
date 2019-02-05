#!/bin/sh
if command -v nvm >/dev/null 2>&1; then
  curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.34.0/install.sh
fi
