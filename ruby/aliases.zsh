#!/bin/zsh
alias migrate='rake db:migrate'

if command -v foreman >/dev/null 2>&1; then
	alias fs='bundle exec foreman start'
	alias fsdev='bundle exec foreman start -f Procfile.dev'
fi
