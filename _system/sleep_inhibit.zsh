#!/bin/zsh

LOCKFILE="$HOME/.sleep_inhibit_lock"

MAIN_ZSH_PID=$(pgrep -xo zsh)
[[ -z "$MAIN_ZSH_PID" ]] && MAIN_ZSH_PID=$$

is_running_sleep_inhibit() {
  [[ -f "$LOCKFILE" ]] || return 1
  local pid
  pid=$(<"$LOCKFILE")
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

[[ -f "$LOCKFILE" ]] && ! is_running_sleep_inhibit && rm -f "$LOCKFILE"

if ! is_running_sleep_inhibit; then
  OS=$(uname)

  if [[ "$OS" == "Darwin" ]] && command -v caffeinate >/dev/null 2>&1; then
    caffeinate -d -w "$MAIN_ZSH_PID" >/dev/null 2>&1 < /dev/null &
    echo $! >| "$LOCKFILE"

  elif [[ "$OS" == "Linux" ]] && command -v systemd-inhibit >/dev/null 2>&1; then
    systemd-inhibit --what=idle:handle-lid-switch \
        --why="zsh-sleep-inhibit" \
        bash -c "while kill -0 $MAIN_ZSH_PID 2>/dev/null; do sleep 60; done" \
        >/dev/null 2>&1 < /dev/null &
    echo $! >| "$LOCKFILE"
  fi
fi
