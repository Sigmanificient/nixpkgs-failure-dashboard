import click
import io
import subprocess
import sys

from enum import Enum, auto
from pathlib import Path

DEFAULT_TIMEOUT = 60
NIX_BUILD_EXTRA_ARGS = (
    "--max-jobs",
    "1",
    "--cores",
    "1",
    "--no-link",
)


def escape_package_attrpath(attrpath: str) -> str:
    return ".".join(f'"{p}"' for p in attrpath.split("."))


class CommandState(Enum):
    SUCCESS = auto()
    FAIL = auto()
    TIMEOUT = auto()
    EXCEPTION = auto()


def run_piped_cmd_with_timeout(
    cmd: tuple[str, ...], timeout: int, output_buffer: io.StringIO
) -> CommandState:
    process = None

    try:
        process = subprocess.Popen(
            ("timeout", str(timeout), *cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        if process.stdout is None:
            process.kill()
            return CommandState.EXCEPTION

        for line in process.stdout:
            sys.stdout.write(line)
            output_buffer.write(line)

    except Exception as e:
        print(e)
        return CommandState.EXCEPTION

    # at this point it should be stopped already
    try:
        process.wait(timeout=1)
    except Exception as e:
        print(e)
        return CommandState.EXCEPTION

    print("Process returncode:", process.returncode)
    if process.returncode == 124:
        return CommandState.TIMEOUT

    if process.returncode == 0:
        return CommandState.SUCCESS

    return CommandState.FAIL


def build_single_package(
    attrpath: str, out_log: Path, nixpkgs: Path, timeout: int
):
    escaped_name = escape_package_attrpath(attrpath)

    if out_log.is_file():
        lines = out_log.read_text().splitlines()
        if lines and "@@@ [" in lines[-1] and "]" in lines[-1]:
            print(f"Already built, skipping.")
            return

    out_log.parent.mkdir(parents=True, exist_ok=True)
    output_buffer = io.StringIO()

    cmd = (
        "nix-build",
        "-E",
        f"(import {nixpkgs} (import ./config.nix)).{escaped_name}",
        *NIX_BUILD_EXTRA_ARGS
    )

    state = run_piped_cmd_with_timeout(cmd, timeout, output_buffer)
    if state == CommandState.EXCEPTION:
        return

    output_buffer.write(f"@@@ [{state.name.upper()}] @@@\n")
    out_log.write_text(output_buffer.getvalue())


@click.command()
@click.argument("attrpath", required=True, type=str)
@click.option("--nixpkgs-path", required=True, type=click.Path(path_type=Path))
@click.option("--log-dir", required=True, type=click.Path(path_type=Path))
@click.option("--timeout", type=int, default=DEFAULT_TIMEOUT)
def main(attrpath: str, nixpkgs_path: Path, log_dir: Path, timeout: int):
    print("Starting build:", attrpath)
    build_single_package(
        attrpath=attrpath,
        out_log=log_dir / f"{attrpath}.log",
        nixpkgs=nixpkgs_path,
        timeout=timeout,
    )


if __name__ == "__main__":
    main()
