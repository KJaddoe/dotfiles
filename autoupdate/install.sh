#!/bin/bash
# setups the auto-update
if [ "$DOTFILES_AUTOUPDATE" != "true" ]; then
    echo "  skipping auto-update cron (set DOTFILES_AUTOUPDATE=true to enable)"
    exit 0
fi

(
    crontab -l | grep -v "dot_update"
    echo "0 */2 * * * $HOME/dotfiles/bin/dot_update > ${TMPDIR:-/tmp}/dot_update.log 2>&1"
) | crontab -
