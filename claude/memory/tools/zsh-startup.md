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

## Fix (current architecture)
ONE compinit, correctly ordered in `zshrc`:
1. source `*/path.zsh`
2. source everything-except path/completion/**aliases** → builds full fpath (antidote, fpath.zsh)
3. `compinit` once (keeps the `~/.zcompdump(#qN.mh+24)` daily-rebuild guard; `-C` otherwise)
4. source `*/aliases.zsh` AFTER compinit — needed because `ssh/aliases.zsh` calls `compdef _pubkey`
   (compdef only exists post-compinit)
5. source `*/completion.zsh` last
Docker completions moved to `zsh/fpath.zsh` (`[ -d ~/.docker/completions ]` guard); `docker/completion.zsh`
deleted. Warm ~0.35s; cold dump rebuild ~1.57s once/24h (acceptable; old was 2.1s every shell).

## Other startup wins same change
- `angular/completion.zsh`: was `source <(ng completion script)` (node spawn every shell) → cache to
  `~/.cache/ng-completion.zsh` (mkdir -p guard), regenerate only if missing.
- Dead p10k prompt segments commented out (pyenv/nvm/rbenv/jenv — binaries gone after mise migration).

## Gotcha if editing zshrc loops
Anything using `compdef` at source time must load AFTER step 3. Anything contributing to `fpath` must
load in step 1–2 (before compinit) or its completions won't register until the next daily rebuild.
