#!/usr/bin/env bash
# Push secrets from .env to GitHub Actions and Railway.
# Usage: ./scripts/sync-secrets.sh [--github-only | --railway-only] [--only KEY,...] [--langfuse] [--dry-run]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

GITHUB_KEYS=(
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  GEMINI_API_KEY
  OPENROUTER_API_KEY
  LANGFUSE_PUBLIC_KEY
  LANGFUSE_SECRET_KEY
)

RAILWAY_KEYS=(
  TELEGRAM_BOT_TOKEN
  TELEGRAM_USER_ID
  GEMINI_API_KEY
  OPENROUTER_API_KEY
  LANGFUSE_PUBLIC_KEY
  LANGFUSE_SECRET_KEY
  WEBHOOK_SECRET
  WEBHOOK_URL
)

SYNC_GITHUB=1
SYNC_RAILWAY=1
DRY_RUN=0
ONLY_KEYS=()

usage() {
  cat <<'EOF'
Sync secrets from .env to GitHub Actions and Railway.

Usage:
  ./scripts/sync-secrets.sh [options]

Options:
  --github-only   Update GitHub repository secrets only
  --railway-only  Update Railway service variables only
  --only KEYS     Sync only listed keys (comma-separated)
  --langfuse      Shortcut for --only LANGFUSE_PUBLIC_KEY,LANGFUSE_SECRET_KEY
  --dry-run       Show what would be synced (values masked)
  -h, --help      Show this help

Examples:
  ./scripts/sync-secrets.sh --langfuse --dry-run
  ./scripts/sync-secrets.sh --only LANGFUSE_PUBLIC_KEY,LANGFUSE_SECRET_KEY
  ./scripts/sync-secrets.sh --railway-only --only GEMINI_API_KEY

Requires:
  - .env in project root (see .env.example)
  - GitHub: GH_TOKEN env var or gh auth login
  - Railway: RAILWAY_TOKEN in .env or railway link

GitHub:  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, OPENROUTER_API_KEY, LANGFUSE_*
Railway: TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, OPENROUTER_API_KEY, LANGFUSE_*,
         WEBHOOK_SECRET, WEBHOOK_URL (optional)
EOF
}

mask_value() {
  local value="$1"
  local len="${#value}"
  if [[ "$len" -eq 0 ]]; then
    echo "(empty)"
    return
  fi
  echo "(${len} chars)"
}

load_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "error: $ENV_FILE not found (copy from .env.example)" >&2
    exit 1
  fi

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      if [[ "$value" =~ ^\"(.*)\"$ ]]; then
        value="${BASH_REMATCH[1]}"
      elif [[ "$value" =~ ^\'(.*)\'$ ]]; then
        value="${BASH_REMATCH[1]}"
      fi
      printf -v "$key" '%s' "$value"
      export "$key"
    fi
  done < "$ENV_FILE"
}

get_var() {
  local name="$1"
  printf '%s' "${!name-}"
}

key_is_selected() {
  local key="$1"
  if [[ ${#ONLY_KEYS[@]} -eq 0 ]]; then
    return 0
  fi
  local selected
  for selected in "${ONLY_KEYS[@]}"; do
    if [[ "$selected" == "$key" ]]; then
      return 0
    fi
  done
  return 1
}

require_command() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "error: $cmd not found ($hint)" >&2
    exit 1
  fi
}

gh_is_authenticated() {
  [[ -n "${GH_TOKEN:-}${GITHUB_TOKEN:-}" ]] && return 0
  gh auth status >/dev/null 2>&1
}

sync_github() {
  if [[ "$DRY_RUN" -eq 0 ]]; then
    require_command gh "install: https://cli.github.com/"
    if ! gh_is_authenticated; then
      echo "error: gh is not authenticated (set GH_TOKEN or run: gh auth login)" >&2
      exit 1
    fi
  fi

  echo "GitHub secrets:"
  for key in "${GITHUB_KEYS[@]}"; do
    if ! key_is_selected "$key"; then
      continue
    fi
    local value
    value="$(get_var "$key")"
    if [[ -z "$value" ]]; then
      echo "  skip $key (empty)"
      continue
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "  set $key = $(mask_value "$value")"
      continue
    fi
    printf '%s' "$value" | gh secret set "$key"
    echo "  set $key"
  done
}

railway_set_variables() {
  if railway variable set --help >/dev/null 2>&1; then
    railway variable set "$@"
    return
  fi
  railway variables --set "$@"
}

railway_is_ready() {
  [[ -n "${RAILWAY_TOKEN:-}" ]] && return 0
  railway status >/dev/null 2>&1
}

sync_railway() {
  if [[ "$DRY_RUN" -eq 0 ]]; then
    require_command railway "install: https://docs.railway.com/guides/cli"
    if ! railway_is_ready; then
      echo "error: railway CLI not ready (set RAILWAY_TOKEN in .env or run: railway link)" >&2
      exit 1
    fi
  fi

  echo "Railway variables:"
  local -a pairs=()
  for key in "${RAILWAY_KEYS[@]}"; do
    if ! key_is_selected "$key"; then
      continue
    fi
    local value
    value="$(get_var "$key")"
    if [[ -z "$value" ]]; then
      echo "  skip $key (empty)"
      continue
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "  set $key = $(mask_value "$value")"
      continue
    fi
    pairs+=("$key=$value")
    echo "  set $key"
  done

  if [[ "$DRY_RUN" -eq 0 && "${#pairs[@]}" -gt 0 ]]; then
    railway_set_variables "${pairs[@]}"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --github-only) SYNC_RAILWAY=0 ;;
    --railway-only) SYNC_GITHUB=0 ;;
    --langfuse)
      ONLY_KEYS=(LANGFUSE_PUBLIC_KEY LANGFUSE_SECRET_KEY)
      ;;
    --only)
      shift
      if [[ $# -eq 0 ]]; then
        echo "error: --only requires a comma-separated key list" >&2
        exit 1
      fi
      IFS=',' read -r -a ONLY_KEYS <<<"$1"
      ;;
    --dry-run) DRY_RUN=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

load_env

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run mode (no changes will be made)"
  echo
fi

if [[ ${#ONLY_KEYS[@]} -gt 0 ]]; then
  echo "filter: ${ONLY_KEYS[*]}"
  echo
fi

if [[ "$SYNC_GITHUB" -eq 1 ]]; then
  sync_github
  echo
fi

if [[ "$SYNC_RAILWAY" -eq 1 ]]; then
  sync_railway
fi

echo
echo "done"
