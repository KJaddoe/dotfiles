# colors
RED="\[\033[0;31m\]"
YELLOW="\[\033[1;33m\]"
GREEN="\[\033[0;32m\]"
BLUE="\[\033[1;34m\]"
LIGHT_RED="\[\033[1;31m\]"
LIGHT_GREEN="\[\033[1;32m\]"
CYAN="\[\033[0;36m\]"
LIGHT_CYAN="\[\033[1;36m\]"
WHITE="\[\033[1;37m\]"
LIGHT_GRAY="\[\033[0;37m\]"
COLOR_NONE="\[\e[0m\]"

alias ls="ls --color=auto"

#PS1="${GREEN}\u:\W\$ ${GREEN}"
trap '[[ -t 1 ]] && tput sgr0' DEBUG

export LC_ALL=en_US.utf-8
export LANG="$LC_ALL"

# tmux cd
tc()
{
    cd $1;
    tmux refresh-client -S;
}

LS_COLORS='ow=01;36;40'

export LS_COLORS
export LC_ALL=en_US.utf-8
export LANG="$LC_ALL"

export DOCKER_HOST=tcp://localhost:2375

alias hostfile="vim /mnt/c/Windows/System32/drivers/etc/hosts"

