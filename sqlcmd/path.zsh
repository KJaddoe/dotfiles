#!/bin/zsh

OS="$(uname)"

if [[ "$OS" == "Linux" ]]; then
    export PATH="$PATH:/opt/mssql-tools/bin"
elif [[ "$OS" == "Darwin" ]]; then
fi
