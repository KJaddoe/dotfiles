#!/bin/bash
if test "$(uname)" = "Darwin"; then
  if test ! $(which gcc); then
    echo "Installing xcode..."
    xcode-select --install
  fi
  if test ! "$(which brew)"; then
    echo "Installing homebrew..."
    ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
  else
    brew update
  fi
  if test ! "$(which ansible)"; then
    echo "Installing ansible..."
    brew install ansible
  else
    brew upgrade ansible
  fi
elif test "$(uname)" = "Linux"; then
  if test -f /etc/lsb-release && test ! "$(which ansible)"; then
    echo "Installing ansible..."
    sudo apt-get update
    sudo apt-get install python3 python3-pip
    sudo -H pip3 install ansible
  fi
fi

if test ! "$(which ansible)"; then
  echo "Not supported yet."
  exit 1
fi

ansible-galaxy install -r requirements.yml --force
ansible-playbook main.yml -K
