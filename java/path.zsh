#!/bin/zsh

OS="$(uname)"

if [[ "$OS" == "Linux" ]]; then
    export JAVA_HOME="$(readlink -f /usr/bin/java | sed 's:/bin/java::')"
elif [[ "$OS" == "Darwin" ]]; then
    export JAVA_HOME="$(/usr/libexec/java_home -v 17)"  # Adjust version if needed
fi

export PATH="$JAVA_HOME/bin:$PATH"
