#!/usr/bin/env bash
REPO="NixOS/nixpkgs"

XDG_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
RUNTIME_DIR="$XDG_STATE_HOME/nixpkgs-failure-dashboard"

if [ ! -f "$RUNTIME_DIR/.run" ]; then
  echo "New run"

  rm "$RUNTIME_DIR/all_packages"
  rm -rf "$RUNTIME_DIR/build-logs"
  mkdir -p "$RUNTIME_DIR/build-logs"

  curl -s "https://api.github.com/repos/$REPO/commits?per_page=1" \
    | jq '.[0] | {rev: .sha, name: .commit.message, date: .commit.author.date}' \
    > "$RUNTIME_DIR/last-commit.json"
fi

REV=$(jq --raw-output .rev "$RUNTIME_DIR/last-commit.json")
echo "Using nixpkgs rev=$REV"

NIXPKGS_PATH=$(nix eval --impure --expr "
  let url = \"https://github.com/NixOS/nixpkgs/archive/${REV}.tar.gz\";
  in (fetchTarball { inherit url; })" | tr -d '"')

if [ ! -f ".run" ]; then
  nix eval --impure --json --expr "
    (import ./collect-packages.nix) {
      pkgs = import $NIXPKGS_PATH (import ./config.nix);
    }" -vv > "$RUNTIME_DIR/all_packages.json"

  cat $RUNTIME_DIR/all_packages.json \
    | tr -d '["]' \
    | tr ',' '\n' \
    > "$RUNTIME_DIR/all_packages"

  touch $RUNTIME_DIR/.run
fi

echo "starting build of $(wc -l < "$RUNTIME_DIR/all_packages") packages"
sleep 1

./run-build.sh "$RUNTIME_DIR/all_packages" "$NIXPKGS_PATH"
rm "$RUNTIME_DIR/.run"
