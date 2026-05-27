#!/bin/zsh
pubkey() {
	local key="${1:-ed25519}"
	local file
	for candidate in ~/.ssh/${key}.pub ~/.ssh/id_${key}.pub; do
		if [[ -f $candidate ]]; then
			file=$candidate
			break
		fi
	done
	if [[ -z $file ]]; then
		echo "pubkey: no key found matching '$key' (~/.ssh/${key}.pub or ~/.ssh/id_${key}.pub)" >&2
		return 1
	fi
	if command -v pbcopy >/dev/null 2>&1; then
		pbcopy < "$file"
	elif command -v xclip >/dev/null 2>&1; then
		xclip -selection clipboard < "$file"
	elif command -v xsel >/dev/null 2>&1; then
		xsel --clipboard --input < "$file"
	else
		echo "pubkey: no clipboard tool found (need pbcopy, xclip, or xsel)" >&2
		return 1
	fi
	echo "=> Copied $file to pasteboard."
}

_pubkey() {
	local -a keys
	local file
	for file in ~/.ssh/*.pub(N); do
		keys+=("${${file:t:r}#id_}")
	done
	_describe 'ssh key' keys
}
compdef _pubkey pubkey
