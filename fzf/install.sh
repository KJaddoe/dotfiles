#!/bin/bash
if test ! "$(which brew)"; then
	echo "Installing fzf..."
	brew install fzf
fi
