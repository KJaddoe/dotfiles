#!/bin/zsh
export ANDROID_HOME=$HOME/Android
export ANDROID_SDK_ROOT=$ANDROID_HOME

export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$PATH
export PATH=$ANDROID_HOME/platform-tools:$PATH

export WSL_HOST=$(tail -1 /etc/resolv.conf | cut -d' ' -f2)
export ADB_SERVER_SOCKET=tcp:$WSL_HOST:5037
