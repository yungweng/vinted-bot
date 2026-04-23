#!/bin/bash
# Doppelklick-Launcher fuer den Vinted-Bot.
# Installiert uv falls noetig und startet den Bot via uvx aus dem GitHub-Repo.
# Aenderungen auf dem main-Branch landen beim naechsten Start beim User.

set -e
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv ist nicht installiert. Installiere..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
    if [ -f "$HOME/.config/vinted-bot/env" ]; then
        # shellcheck disable=SC1091
        source "$HOME/.config/vinted-bot/env"
    fi
fi

exec uvx \
    --refresh-package vinted-bot \
    --from "git+https://github.com/yungweng/vinted-bot@main" \
    vinted-bot
