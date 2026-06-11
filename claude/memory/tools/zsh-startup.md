# zsh startup performance (dotfiles)

2026-06-11 — Cut interactive shell startup ~2.1s → ~0.35s (warm). Root cause + architecture so it
isn't rediscovered.

## What was slow
`compinit` ran TWICE per shell: once in `zsh/zshrc` (top) and again, unconditionally and full, in
`docker/completion.zsh`. Each call did a full security audit (`compaudit`) + dump rebuild + ~1955
`compdef` registrations. Profile with: a temp `ZDOTDIR` whose `.zshrc` does
`zmodload zsh/zprof; source ~/dotfiles/zsh/zshrc; zprof`, then `ZDOTDIR=/tmp/zprof zsh -ic exit`.

## Why two compinits existed (the ordering trap)
`zshrc` sources hooks in loops keyed by filename: `*/path.zsh`, then everything else, then
`*/completion.zsh` LAST. But `fpath` is built across many of those files (`zsh/fpath.zsh` adds topic
folders; antidote `load` adds plugins; docker added `~/.docker/completions`). The top-of-zshrc
compinit ran before any of that, so docker's late compinit existed to re-scan the now-complete fpath.

## Fix (current architecture) — ONE compinit, deferred-compdef (oh-my-zsh pattern)
The hard part: antidote `load` (in the middle loop) sources oh-my-zsh git/tmux/pip plugins that call
`compdef` AT LOAD TIME, and `ssh/aliases.zsh` calls `compdef _pubkey`. So compdef must exist before
the middle loop, but compinit must run after it (to scan the fpath those plugins build). A first
attempt that just moved compinit after the middle loop and sourced aliases afterward FAILED — the
plugins (not just aliases) error `command not found: compdef`. Solution in `zshrc`:
1. install a stub `compdef() { _deferred_compdefs+=("${(j: :)@}") }` that queues calls
2. source `*/path.zsh`, then everything-but-completion (builds full fpath: antidote incl
   zsh-completions, `zsh/fpath.zsh`) — plugin/alias compdef calls get queued, not run
3. `unfunction compdef`; run `compinit` once (keeps `~/.zcompdump(#qN.mh+24)` daily-rebuild guard,
   `-C` otherwise)
4. replay: `for _cd in $_deferred_compdefs; do compdef ${=_cd}; done`
5. source `*/completion.zsh` last (fzf/angular call the now-real compdef)
Docker completions moved to `zsh/fpath.zsh` (`[ -d ~/.docker/completions ]` guard); `docker/completion.zsh`
deleted. Verify completions registered: `_comps[git]`/`_comps[docker]`/`_comps[pubkey]` == 1.
Warm ~0.32s (was 2.1s every shell). NOTE: "gitstatus failed to initialize" under `zsh -ic` piped
tests is a p10k TTY artifact, NOT a regression — real terminals are clean.

## Other startup wins same change
- `angular/completion.zsh`: was `source <(ng completion script)` (node spawn every shell) → cache to
  `~/.cache/ng-completion.zsh` (mkdir -p guard), regenerate only if missing.
- Dead p10k prompt segments commented out (pyenv/nvm/rbenv/jenv — binaries gone after mise migration).

## Gotcha if editing zshrc loops
Anything contributing to `fpath` must load before the single compinit (step 3). Anything calling
`compdef` at source time is fine anywhere — the stub queues it and step 4 replays it. Do NOT remove
the stub/replay: antidote's oh-my-zsh plugins call compdef during `load` and will error without it.
