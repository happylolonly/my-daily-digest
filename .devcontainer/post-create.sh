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

if [ -f requirements.txt ]; then
  pip install --user -r requirements.txt
fi
