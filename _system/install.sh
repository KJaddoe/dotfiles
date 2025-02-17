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
	sudo apt install software-properties-common
	sudo add-apt-repository --yes --update ppa:ansible/ansible
	sudo apt install ansible
  fi
  if test ! "$(which brew)"; then
    echo "Installing homebrew..."
	/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  else
    brew update
  fi
fi

if test ! "$(which ansible)"; then
  echo "Not supported yet."
  exit 1
fi

ansible-galaxy install -r $(pwd -P)/_system/requirements.yml --force
ansible-playbook $(pwd -P)/_system/main.yml -K
