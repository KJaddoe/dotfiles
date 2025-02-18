#!/bin/sh
if command -v brew >/dev/null 2>&1; then
	brew install antidote
else
	git clone --depth=1 https://github.com/mattmc3/antidote.git ${ZDOTDIR:-~}/.antidote
fi
