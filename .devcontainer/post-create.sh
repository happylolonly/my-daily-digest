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

if [ -f requirements.txt ]; then
  pip install --user -r requirements.txt
fi
