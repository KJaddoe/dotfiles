#!/bin/zsh
export WSL_HOST=$(tail -1 /etc/resolv.conf | cut -d' ' -f2)
