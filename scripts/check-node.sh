#!/usr/bin/env sh
set -eu

# Allows overriding the node binary explicitly.
# Example: NODE_BIN=~/.nvm/versions/node/v24.1.0/bin/node make format
NODE_BIN_OVERRIDE="${NODE_BIN:-}"

resolve_node_bin() {
  if [ -n "$NODE_BIN_OVERRIDE" ]; then
    echo "$NODE_BIN_OVERRIDE"
    return 0
  fi

  # Prefer Homebrew Node on macOS to avoid non-interactive shells
  # picking up an older /usr/local/bin/node.
  if [ -x "/opt/homebrew/bin/node" ]; then
    echo "/opt/homebrew/bin/node"
    return 0
  fi

  if command -v node >/dev/null 2>&1; then
    command -v node
    return 0
  fi

  return 1
}

NODE_BIN_PATH="$(resolve_node_bin || true)"
if [ -z "$NODE_BIN_PATH" ]; then
  echo "❌ Node.js is not installed (required: 24.1+)."
  echo "   Install Node 24.1+ and re-run the command."
  exit 1
fi

VER_RAW="$($NODE_BIN_PATH --version)"
VER="$(echo "$VER_RAW" | sed 's/^v//')"

# Compare major/minor against 24.1
MAJOR="$(echo "$VER" | cut -d. -f1)"
MINOR="$(echo "$VER" | cut -d. -f2)"

if [ -z "$MAJOR" ] || [ -z "$MINOR" ]; then
  echo "❌ Could not parse Node.js version: $VER_RAW ($NODE_BIN_PATH)"
  exit 1
fi

if [ "$MAJOR" -lt 24 ] || { [ "$MAJOR" -eq 24 ] && [ "$MINOR" -lt 1 ]; }; then
  echo "❌ Node.js $VER detected at $NODE_BIN_PATH, but this repo requires Node 24.1+."
  echo "   Fix: upgrade Node (recommended: Homebrew, nvm, or fnm) then re-run."
  exit 1
fi

echo "✅ Node.js $VER ($NODE_BIN_PATH)"
