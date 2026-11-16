#!/usr/bin/env bash
# Installs the tools the gates need, at pinned versions. CI runs this before the gates.
# Python tools come from a hash-locked file, jscpd from package-lock.json, and the two
# binaries are checked against a SHA-256 that is pinned here.
set -euo pipefail

ACTIONLINT_VERSION=1.7.12
ACTIONLINT_SHA256=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
VALE_VERSION=3.27.0
VALE_SHA256=c80d62f6bce87b81843ac5b512a26e63213927b957adba0a64fc594570da2000

TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.github/tools" && pwd)"
BIN_DIR="${GATE_BIN_DIR:-$HOME/.local/bin}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$BIN_DIR"

fetch_binary() { # name url sha256 archive-member
  local name="$1" url="$2" sha="$3" member="$4"
  curl -fsSL "$url" -o "$WORK_DIR/$name.tgz"
  echo "$sha  $WORK_DIR/$name.tgz" | sha256sum -c -
  tar -xzf "$WORK_DIR/$name.tgz" -C "$BIN_DIR" "$member"
}

VENV_DIR="${GATE_VENV_DIR:-$HOME/.local/gate-venv}"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --require-hashes --no-deps -r "$TOOLS_DIR/requirements.txt"
ln -sf "$VENV_DIR/bin/lizard" "$BIN_DIR/lizard"
ln -sf "$VENV_DIR/bin/zizmor" "$BIN_DIR/zizmor"

npm ci --prefix "$TOOLS_DIR" --ignore-scripts --no-audit --no-fund
ln -sf "$TOOLS_DIR/node_modules/.bin/jscpd" "$BIN_DIR/jscpd"

fetch_binary actionlint "https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz" "$ACTIONLINT_SHA256" actionlint
fetch_binary vale "https://github.com/errata-ai/vale/releases/download/v${VALE_VERSION}/vale_${VALE_VERSION}_Linux_64-bit.tar.gz" "$VALE_SHA256" vale
echo "install-gate-tools: done"
