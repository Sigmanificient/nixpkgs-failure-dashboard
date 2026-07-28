#!/usr/bin/env bash

set -euo pipefail

XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
RUNTIME_DIR="$XDG_STATE_HOME/nixpkgs-failure-dashboard"

INPUT_FILE="$1"
NIXPKGS_PATH="$2"

JOBS=$(nproc)
TIMEOUT="${3:-30}"
BATCH_SIZE="${4:-5000}"
LOG_DIR="$RUNTIME_DIR/build-logs"

mkdir -p "$LOG_DIR"

build_package() {
  nfd-build --nixpkgs-path="$NIXPKGS_PATH" --log-dir="$LOG_DIR" "$1"
}

export -f build_package
export LOG_DIR TIMEOUT NIXPKGS_PATH

CHUNK_DIR=$(mktemp -d)
trap 'rm -rf "$CHUNK_DIR"' EXIT

split -l "$BATCH_SIZE" --filter='tr "\n" "\0" > $FILE' "$INPUT_FILE" "$CHUNK_DIR/chunk_"

for chunk in "$CHUNK_DIR"/chunk_*; do
  cat "$chunk" | xargs -0 -I{} -P "$JOBS" bash -c 'build_package "$@"' _ {}

  DISK_USAGE=$(df /nix/store --output=pcent | tail -1 | tr -dc '0-9')
  if [ "$DISK_USAGE" -gt 90 ]; then
    nix-collect-garbage -d
  fi
done
