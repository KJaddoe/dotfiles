#!/bin/zsh
# claude-local: run Claude Code against a local Ollama model (offline/private).
# Default `claude` stays on the licensed Anthropic API. See docs/decisions/0002.

_claude_local_ensure_ollama() {
  if ! curl -fsS -o /dev/null http://localhost:11434/api/tags 2>/dev/null; then
    print -u2 "claude-local: starting Ollama..."
    if command -v brew >/dev/null 2>&1; then
      brew services start ollama >/dev/null 2>&1
    elif command -v systemctl >/dev/null 2>&1; then
      systemctl start ollama 2>/dev/null
    fi
    local i
    for i in {1..30}; do
      curl -fsS -o /dev/null http://localhost:11434/api/tags 2>/dev/null && return 0
      sleep 1
    done
    print -u2 "claude-local: Ollama not reachable on :11434"
    return 1
  fi
}

claude-local() {
  (
    # Local model tags (keep in sync with _system/roles/ollama/vars/main.yml).
    : ${CLAUDE_LOCAL_MODEL:=qwen2.5-coder-cc:14b}
    : ${CLAUDE_LOCAL_SMALL_MODEL:=qwen2.5-coder-cc:3b}
    _claude_local_ensure_ollama || exit 1
    export ANTHROPIC_BASE_URL=http://localhost:11434
    export ANTHROPIC_AUTH_TOKEN=ollama
    export ANTHROPIC_API_KEY=""
    export ANTHROPIC_MODEL="$CLAUDE_LOCAL_MODEL"
    export ANTHROPIC_DEFAULT_HAIKU_MODEL="$CLAUDE_LOCAL_SMALL_MODEL"
    export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
    exec claude "$@"
  )
}
