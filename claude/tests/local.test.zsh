#!/bin/zsh
# Test: sourcing local.zsh defines claude-local, and invoking it exports the
# expected env and calls `claude`. We stub `claude` to print the env it sees.
set -e
SCRIPT_DIR="${0:A:h}"
source "$SCRIPT_DIR/../local.zsh"

# stub `claude`: print the relevant env, then exit (replaces exec target)
claude() {
  print "MODEL=$ANTHROPIC_MODEL"
  print "BASE=$ANTHROPIC_BASE_URL"
  print "TOKEN=$ANTHROPIC_AUTH_TOKEN"
  print "HAIKU=$ANTHROPIC_DEFAULT_HAIKU_MODEL"
  print "TELEMETRY=$CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"
  print "ARGS=$*"
}
# neutralise the readiness check so the test needs no running Ollama
_claude_local_ensure_ollama() { return 0 }

out="$(claude-local --resume 2>&1)"

print "$out" | grep -q 'BASE=http://localhost:11434' || { print "FAIL: base url"; exit 1 }
print "$out" | grep -q 'TOKEN=ollama'                || { print "FAIL: auth token"; exit 1 }
print "$out" | grep -q 'MODEL=qwen2.5-coder-cc:3b'   || { print "FAIL: main model"; exit 1 }
print "$out" | grep -q 'HAIKU=qwen2.5-coder-cc:3b'   || { print "FAIL: haiku model"; exit 1 }
print "$out" | grep -q 'TELEMETRY=1'                 || { print "FAIL: telemetry flag"; exit 1 }
print "$out" | grep -q 'ARGS=--resume'               || { print "FAIL: arg passthrough"; exit 1 }

# env must NOT leak into the caller (function ran in a subshell)
[[ -z "$ANTHROPIC_BASE_URL" ]] || { print "FAIL: env leaked into parent shell"; exit 1 }

print "PASS"
