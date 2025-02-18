#!/bin/zsh
## Detect OS
OS_TYPE="$(uname -s)"

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Set Antidote path dynamically
if command_exists brew; then
  # If Homebrew is installed, check the install location
  ANTIDOTE_PATH="$(brew --prefix)/share/antidote/antidote.zsh"
elif [[ -f "/usr/local/share/antidote/antidote.zsh" ]]; then
  ANTIDOTE_PATH="/usr/local/share/antidote/antidote.zsh"
elif [[ -f "$HOME/.antidote/antidote.zsh" ]]; then
  ANTIDOTE_PATH="$HOME/.antidote/antidote.zsh"
else
  ANTIDOTE_PATH=""
fi

# Source Antidote if found
if [[ -n "$ANTIDOTE_PATH" ]]; then
  source "$ANTIDOTE_PATH"

  # Initialize plugins from ~/.zsh_plugins.txt
  antidote load
else
  echo "Warning: Antidote not found!"
fi
