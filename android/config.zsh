#!/bin/zsh
export ANDROID_HOME=/opt/android-sdk-linux

export PATH=$ANDROID_HOME/tools:$PATH
export PATH=$ANDROID_HOME/platform-tools:$PATH

export ADB_SERVER_SOCKET=tcp:0.0.0.0:5037
