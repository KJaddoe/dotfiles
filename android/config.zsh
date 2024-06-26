#!/bin/zsh
export WSL_HOST=$(ip route show | grep -i default | awk '{ print $3}')
export ADB_SERVER_SOCKET=tcp:$WSL_HOST:5037
