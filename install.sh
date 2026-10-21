#!/usr/bin/env bash
# Install Claude Agent Exchange: the explorer app, its launcher, and the exchange folder.
#   ./install.sh               everything
#   ./install.sh --no-app      only the folder and the CLAUDE.md block
#   ./install.sh --dry-run     show what apply.py would change; install nothing
# Any other flags go to template/apply.py (--root DIR, --claude-md FILE).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
APP=1; DRY=0; ARGS=()
for a in "$@"; do
  case "$a" in --no-app) APP=0 ;; --dry-run) DRY=1; ARGS+=("$a") ;; *) ARGS+=("$a") ;; esac
done
if [ "$APP" = 1 ] && [ "$DRY" = 0 ]; then
  if command -v uv >/dev/null; then uv tool install --force --quiet "$HERE/explorer"
  elif command -v pipx >/dev/null; then pipx install --force "$HERE/explorer"
  else echo "need uv or pipx to install the explorer (or run with --no-app)" >&2; exit 1; fi
  install -Dm644 "$HERE/launcher/claude-agent-exchange.desktop" "$HOME/.local/share/applications/claude-agent-exchange.desktop"
  install -Dm644 "$HERE/launcher/claude-agent-exchange.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/claude-agent-exchange.svg"
  update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
  gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi
python3 -I "$HERE/template/apply.py" "${ARGS[@]}"
