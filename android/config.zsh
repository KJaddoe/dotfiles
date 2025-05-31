#!/bin/zsh

OS_TYPE="$(uname -s)"

if [[ "$OS" == "Linux" ]]; then
  export WSL_HOST=$(ip route show | grep -i default | awk '{ print $3}')
  export ADB_SERVER_SOCKET=tcp:$WSL_HOST:5037
elif [[ "$OS" == "Darwin" ]]; then
fi
