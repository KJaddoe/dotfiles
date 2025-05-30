#!/bin/zsh

OS="$(uname)"

if [[ "$OS" == "Darwin" ]]; then
    if [[ -d "/Applications/Visual Studio Code.app" ]]; then
        CODE_BIN="/Applications/Visual Studio Code.app/Contents/Resources/app/bin"
        export PATH="$CODE_BIN:$PATH"
    fi
elif [[ "$OS" == "Linux" ]]; then
    if ! command -v code > /dev/null 2>&1; then
        :
    fi
fi
