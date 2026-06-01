#!/bin/bash

set -e

export PATH="$HOME/.local/bin:$PATH"

if ! command -v claude >/dev/null 2>&1; then
	echo "Installing Claude Code..."
	curl -fsSL https://claude.ai/install.sh | bash
else
	echo "Claude Code already installed: $(claude --version)"
fi

if ! command -v claude >/dev/null 2>&1; then
	echo "Claude Code not on PATH after install, skipping plugin setup."
	exit 0
fi

echo "Configuring marketplaces..."
claude plugin marketplace add anthropics/claude-plugins-official || true
claude plugin marketplace add obra/superpowers-marketplace || true

echo "Installing plugins..."
claude plugin install csharp-lsp@claude-plugins-official || true
claude plugin install typescript-lsp@claude-plugins-official || true
claude plugin install frontend-design@claude-plugins-official || true
claude plugin install superpowers@superpowers-marketplace || true

echo "Claude Code setup complete."
