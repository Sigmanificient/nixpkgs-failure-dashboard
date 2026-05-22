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
  local name="$1"
  local escaped_name=$(python3 -c "print('.'.join(f'\"{x}\"' for x in '$name'.split('.')))")
  local out_log="$LOG_DIR/${name}.log"

  echo "Starting build: $escaped_name"
  out_log="$LOG_DIR/${name}.log"
  if [[ -f "$out_log" ]] && tail -n 1 "$out_log" | grep -q "@@@ \[.*\] @@@"; then
    return 0
  fi

  timeout "$TIMEOUT" \
    nix-build -E "(import $NIXPKGS_PATH (import ./config.nix)).${escaped_name}" \
      --max-jobs 1 \
      --cores 1 \
      --no-link \
      2>&1 | tee "$out_log"

  status=${PIPESTATUS[0]}

  if [ $status -eq 0 ]; then
    echo "@@@ [SUCCESS] @@@" | tee -a "$out_log"
  elif [ $status -eq 124 ]; then
    echo "@@@ [TIMEOUT] @@@" | tee -a "$out_log"
  else
    echo "@@@ [FAIL] @@@" | tee -a "$out_log"
  fi
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
