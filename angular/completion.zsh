#!/bin/zsh
ng_completion_cache="${XDG_CACHE_HOME:-$HOME/.cache}/ng-completion.zsh"
if [[ ! -s "$ng_completion_cache" ]] && command -v ng >/dev/null 2>&1; then
  mkdir -p "${ng_completion_cache:h}"
  ng completion script >"$ng_completion_cache" 2>/dev/null
fi
[[ -s "$ng_completion_cache" ]] && source "$ng_completion_cache"
unset ng_completion_cache
