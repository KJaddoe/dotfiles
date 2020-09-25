#!/bin/zsh
export ANDROID_HOME=~/Android

export PATH=$ANDROID_HOME/tools:$PATH
export PATH=$ANDROID_HOME/platform-tools:$PATH

export ADB_SERVER_SOCKET=tcp:$WSL_HOST:5037
