{pkgs}: let
  inherit (pkgs) lib;
  inherit (lib)
    isAttrs
    isDerivation
    showAttrPath
    mapAttrsToList
    concatLists
    recurseIntoAttrs
    ;

  # Stripped down version of
  # https://github.com/NixOS/nixpkgs/blob/a94513cdee868f1398fccc3a6b424857eb44a43f/pkgs/top-level/packages-info.nix
  getPackages = path: value:
    if path == [ "AAAAAASomeThingsFailToEvaluate" ] || !(isAttrs value) then
      [ ]
    else if isDerivation value then
      [ (showAttrPath path) ]
    else if value.recurseForDerivations or false then
      lib.pipe value [
        (mapAttrsToList (name: value: getPackages (path ++ [ name ]) value))
        concatLists
      ]
    else
      [ ];
in
  getPackages [ ] (recurseIntoAttrs pkgs)
