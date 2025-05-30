#!/bin/zsh

OS_TYPE="$(uname -s)"

if [[ "$OS_TYPE" == "Darwin" ]]; then
  if command -v brew >/dev/null 2>&1; then
    export NVM_DIR="$(brew --prefix nvm)/.nvm"
  fi
else
  export NVM_DIR="$HOME/.nvm"
fi

[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
