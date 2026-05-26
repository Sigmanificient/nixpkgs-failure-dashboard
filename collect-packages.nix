{pkgs}: let
  inherit (pkgs) lib;

  collect = prefix: pkg: name:
    if lib.isDerivation pkg
    then ["${prefix}${name}"]
    else if pkg.recurseForDerivations or false || pkg.recurseForRelease or false
    then packagesWith "${prefix}${name}." pkg
    else [];

  packagesWith = prefix: set:
    lib.flatten (
      lib.mapAttrsToList (
        name: pkg: let
          result = builtins.tryEval (collect prefix pkg name);
        in
          if result.success
          then result.value
          else []
      )
      set
    );
in
  packagesWith "" pkgs
