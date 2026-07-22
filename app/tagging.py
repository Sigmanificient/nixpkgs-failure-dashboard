from dataclasses import dataclass, field


@dataclass(frozen=True)
class ErrorCheck:
    name: str
    pattern: str
    hints: list[str] = field(default_factory=list)


TAG_CHECKS = [
    ErrorCheck(
        name="aclocal/missing-deps",
        pattern=r"aclocal: error: couldn't open directory '.*': No such file or directory",
        hints=[
            "error: aclocal failed with exit status: 1",
        ],
    ),
    ErrorCheck(
        name="cmake/boost 1.89",
        pattern=r"CMake Error at",
        hints=[
            "(requested version 1.89.0)",
            "lib/cmake/Boost-1.89.0",
        ],
    ),
    ErrorCheck(
        name="cmake/minimal-version-fail",
        pattern=r"CMake Error at",
        hints=[
            "Compatibility with CMake < 3.5 has been removed",
            "add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway",
        ],
    ),
    ErrorCheck(
        name="cmake/configure-error",
        pattern=r"CMake Error at",
        hints=[
            "cmake flags:",
            "CMakeLists.txt",
            "-- Configuring incomplete, errors occurred!",
        ],
    ),
    ErrorCheck(
        name="patchelf/missing-deps",
        pattern=r"auto-patchelf: \d+ dependencies could not be satisfied",
        hints=[
            "auto-patchelf could not satisfy dependency",
            "auto-patchelf failed to find all the required dependencies",
        ],
    ),
    ErrorCheck(
        name="python/import-error",
        pattern=(
            r"(ImportError: cannot import name '.*' from '.*'"
            r"|ModuleNotFoundError: No module named '.*')"
        ),
        hints=["<module>"],
    ),
    ErrorCheck(
        name="python/runtime-deps",
        pattern=r"(not installed)|(not satisfied by version)",
        hints=[
            "Checking runtime dependencies",
            "Executing pythonRuntimeDepsCheck",
        ],
    ),
    ErrorCheck(
        name="python/missing-legacy-setup",
        pattern=r"Traceback \(most recent call last\):",
        hints=[
            "FileNotFoundError: [Errno 2]",
            "No such file or directory: 'setup.py'",
            "exec(compile(getattr(tokenize",
        ],
    ),
    ErrorCheck(
        name="python/backend-error",
        pattern=r"(BackendUnavailable|ERROR Backend .* is not available)",
        hints=[
            "Executing pypaBuildPhase",
            "pyproject_hooks._impl.BackendUnavailable",
        ],
    ),
    ErrorCheck(
        name="python/build-deps-failure",
        pattern=r"ERROR Missing dependencies:",
        hints=[
            "Creating a wheel...",
            "pypa build flags",
        ],
    ),
    ErrorCheck(
        name="python/pytest-failure",
        pattern=r"=========+.*(errors?|failed)",
        hints=[r"==== short test summary info ===="],
    ),
    ErrorCheck(
        name="python/missing-toPythonModule",
        pattern=r"error: .* should use `buildPythonPackage` or `toPythonModule` if it is to be part of the Python packages set.",
    ),
    ErrorCheck(
        name="python/dist-info-mismatch",
        pattern=r"but \.dist-info/METADATA specifies version",
        hints=["Executing pythonMetadataCheckPhase", "pyprojectVersionPatchHook"]
    ),
    ErrorCheck(
        name="python/missing-metadata",
        pattern=r"importlib.metadata.PackageNotFoundError: No package metadata was found for",
        hints=["pythonMetadataCheckPhase"]
    ),
    ErrorCheck(
        name="c-compile-error", pattern=r"\S+\.[ch]{1,2}:\d+:\d+: error:"
    ),
    ErrorCheck(
        name="haskell-deps-failure",
        pattern=r"Error: \[Cabal-8010\]",
        hints=["Encountered missing or private dependencies:"],
    ),
    ErrorCheck(
        name="npm-dependency-failure",
        pattern=r"npm error",
        hints=["package-lock.json"],
    ),
    ErrorCheck(
        name="npm-dependency-failure",
        pattern=r"ERROR: npm failed to install dependencies",
        hints=[
            "npm error",
            "Here are a few things you can try",
            "--legacy-peer-deps",
        ],
    ),
    ErrorCheck(
        name="sbcl-create-homeless-shelter",
        pattern=r"BUILD FAILED: Can't create directory /homeless-shelter",
        hints=["; compilation unit aborted"],
    ),
    ErrorCheck(
        name="sbcl-compilation-fail",
        pattern=r"; compilation unit aborted",
        hints=["SBCL is free software"],
    ),
    ErrorCheck(
        name="sbcl-missing-component",
        pattern=r"BUILD FAILED: Component .* not found",
        hints=["SBCL is free software"],
    ),
    ErrorCheck(
        name="generic/missing-header",
        pattern=r": No such file or directory",
        hints=["#include <", "compilation terminated."],
    ),
    ErrorCheck(
        name="generic/fetch-error",
        pattern=r"error: cannot download .* from any mirror",
        hints=["curl: (", "Warning: Problem"],
    ),
    ErrorCheck(
        name="generic/hash-mismatch",
        pattern=r"error: hash mismatch in fixed-output derivation",
        hints=["specified: ", "got: "],
    ),
    ErrorCheck(
        name="generic/hunk-failed",
        pattern=r"(hunks? FAILED -- saving rejects|\d+ out of \d+ hunk ignored)",
        hints=["Hunk #", "applying patch"],
    ),
    ErrorCheck(
        name="generic/hunk-ignored",
        pattern=r"(hunks ignored -- saving rejects|\d+ out of \d+ hunk ignored)",
        hints=["Skipping patch", "applying patch"],
    ),
    ErrorCheck(
        name="generic/substitute-error",
        pattern=r"substituteStream\(\) in derivation",
        hints=["ERROR:"],
    ),
    ErrorCheck(
        name="generic/substitute-error",
        pattern=r"substitute\(\): ERROR:",
        hints=["does not exist"],
    ),
    ErrorCheck(
        name="generic/missing-file",
        pattern=r"No such file or directory",
        hints=["error:"],
    ),
    ErrorCheck(
        name="generic/broken-symlink",
        pattern=r"ERROR: noBrokenSymlinks: found \d+ dangling symlinks, \d+ reflexive symlinks and \d+ unreadable symlinks",
    ),
    ErrorCheck(
        name="generic/out-of-space",
        pattern=r"note: build failure may have been caused by lack of free disk space",
    ),
    ErrorCheck(
        name="unknown",
        pattern=r"error: ",
    ),
]

__all__ = ("TAG_CHECKS",)
