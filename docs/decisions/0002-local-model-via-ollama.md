# ADR 0002: Local model for Claude Code via Ollama (no proxy)

- Status: accepted
- Date: 2026-07-03

## Context

We use the licensed Anthropic model in Claude Code. We also want a fully local,
offline/privacy fallback — nothing leaving the machine, no API key — accepting lower
quality. Claude Code speaks Anthropic's `/v1/messages`; historically routing it to a
local model needed a translation proxy (LiteLLM / router / shim).

## Decision

No proxy. Ollama now exposes a native Anthropic-compatible endpoint on
`http://localhost:11434`, so we point Claude Code straight at it. Install is an Ansible
role (`_system/roles/ollama/`, brew on macOS / official script on Ubuntu) that pulls
local coding models. A `claude/local.zsh` wrapper defines `claude-local`, which sets the
Ollama env vars + disables non-essential traffic and `exec`s Claude Code in a subshell.
The default `claude` command is unchanged and stays on the Anthropic API.

Ollama defaults to a 4096-token context, too small for Claude Code's system prompt and
tool definitions; we bake `num_ctx 32768` into derived model variants
(`qwen2.5-coder-cc:3b`) via Modelfiles so they load with a usable window on any
platform without service-level env changes. The wrapper targets these variants.

Local model tags only (no `:cloud` — those are Ollama-hosted and defeat the privacy goal).

## Consequences

- A local fallback with no code change to Claude Code itself; toggle is a separate command.
- Quality/speed are bounded by local hardware and model — this is a fallback, not a peer of
  the licensed model, especially for tool-heavy agentic work.
- The context-tuned model tags are defined in `_system/roles/ollama/vars/main.yml` and must
  stay in sync with the wrapper defaults in `claude/local.zsh` (both `qwen2.5-coder-cc`).
- The 32k window raises the 3b model's memory use to ~2.8 GB (fits 24 GB); a larger model or
  `ollama_num_ctx` trades quality/context for memory and speed.
- If Ollama drops or changes the native Anthropic endpoint, this reverts to needing a proxy.
