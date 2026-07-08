#!/usr/bin/env bash
set -euo pipefail

PIP_CACHE_DIR="/home/vscode/.cache/pip"
if [ -d "$PIP_CACHE_DIR" ]; then
  sudo chown -R vscode:vscode "$PIP_CACHE_DIR"
fi

# Named volumes are created owned by root; claude needs to write here as vscode.
PLUGINS_DIR="/home/vscode/.claude/plugins"
if [ -d "$PLUGINS_DIR" ]; then
  sudo chown -R vscode:vscode "$PLUGINS_DIR"
fi

# The claude-code feature installs via npm, but the config expects the native
# path (~/.local/bin/claude). Symlink so `/doctor` finds it.
CLAUDE_BIN="$(command -v claude || true)"
if [ -n "$CLAUDE_BIN" ]; then
  mkdir -p /home/vscode/.local/bin
  ln -sf "$CLAUDE_BIN" /home/vscode/.local/bin/claude
fi

# Keep ~/.claude.json inside the bind-mounted ~/.claude dir. A separate bind
# mount for ~/.claude.json truncates writes on Docker Desktop (consistency=cached).
CLAUDE_CONFIG="/home/vscode/.claude/.claude.json"
if [ ! -f "$CLAUDE_CONFIG" ]; then
  LATEST_BACKUP="$(ls -1t /home/vscode/.claude/backups/.claude.json.backup.* 2>/dev/null | head -1 || true)"
  if [ -n "$LATEST_BACKUP" ]; then
    cp "$LATEST_BACKUP" "$CLAUDE_CONFIG"
  else
    echo '{}' > "$CLAUDE_CONFIG"
  fi
fi
ln -sfn "$CLAUDE_CONFIG" /home/vscode/.claude.json

# Named volumes are created owned by root; railway link writes here as vscode.
RAILWAY_DIR="/home/vscode/.railway"
if [ -d "$RAILWAY_DIR" ]; then
  sudo chown -R vscode:vscode "$RAILWAY_DIR"
fi

# Railway CLI (installs to ~/.railway/bin, persisted via volume). Piped to bash,
# not sh — the script uses bash syntax. npm install fails on arm64 (no gnu build).
if ! command -v railway >/dev/null 2>&1; then
  curl -fsSL https://railway.com/install.sh | bash -s -- -y
fi

# Dev deps include prod ones (requirements-dev.txt starts with -r requirements.txt).
if [ -f requirements-dev.txt ]; then
  pip install --user -r requirements-dev.txt
fi
