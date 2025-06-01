#!/bin/zsh
#
if [ "$OS" = "Linux" ]; then
  export WSL_HOST=$(ip route show | grep -i default | awk '{ print $3}')
  export GPG_TTY=$(tty)
fi
