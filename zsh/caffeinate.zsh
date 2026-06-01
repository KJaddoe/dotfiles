#!/bin/zsh
if [ "$(uname -s)" = "Darwin" ] && command -v caffeinate >/dev/null 2>&1; then
	if ! pgrep -xq caffeinate; then
		caffeinate -d &!
	fi
fi
