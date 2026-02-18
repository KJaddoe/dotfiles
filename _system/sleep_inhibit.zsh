#!/bin/zsh

if [ -n "$TMUX" ]; then
  TMUX_SERVER_PID=$(pgrep -xo tmux)

  LOCKFILE="$HOME/.tmux_sleep_inhibit_lock"

  is_running_sleep_inhibit() {
      [[ -f "$LOCKFILE" ]] || return 1
      local pid
      pid=$(<"$LOCKFILE")
      [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1
  }

  if [[ -f "$LOCKFILE" ]] && ! is_running_sleep_inhibit; then
      rm -f "$LOCKFILE"
  fi

  if ! is_running_sleep_inhibit; then
      OS="$(uname)"

      if [[ "$OS" == "Darwin" ]] && command -v caffeinate >/dev/null 2>&1; then
          caffeinate -d -w "$TMUX_SERVER_PID" >/dev/null 2>&1 &
          echo $! > "$LOCKFILE"

      elif [[ "$OS" == "Linux" ]] && command -v systemd-inhibit >/dev/null 2>&1; then
          systemd-inhibit --what=idle:handle-lid-switch \
            --why="tmux-server" \
            bash -c "while kill -0 $TMUX_SERVER_PID 2>/dev/null; do sleep 60; done" \
            >/dev/null 2>&1 &
          echo $! > "$LOCKFILE"
      fi
  fi
fi
