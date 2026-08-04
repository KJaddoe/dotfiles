#!/bin/zsh
# jump to a directory under $PROJECTS; bare `c` goes to $PROJECTS itself
c() {
  cd "$PROJECTS/${1}"
}

_c() {
  _files -W "$PROJECTS" -/
}

compdef _c c
