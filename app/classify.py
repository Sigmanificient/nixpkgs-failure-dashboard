import csv
import io
import os
import re
import urllib.request
from collections import defaultdict
from contextlib import contextmanager

from .config import RUNTIME_DIR, BUILD_LOGS_DIR
from .db import get_db, reset_db
from .models import Build
from .tagging import TAG_CHECKS, ErrorCheck

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Sigmanificient/nixpkgs-failure-notify"
    "/refs/heads/results"
    "/results/3-failures-x86_64-linux.csv"
)

GENERIC_ERROR_RE = re.compile(
    r"(error:|Error:|ERROR|FAILED|fatal:|Failed)", re.IGNORECASE
)


SKIP_BUILD_LOG_IF_MATCHES = (
    "error: Refusing to evaluate package",
    "error: attempt to call something which is not a function",
    "error: cannot evaluate a function",
    "error: expected a set but found a function",
    "error: expression does not evaluate to a derivation",
    "error: undefined variable",
    # unsupported
    "unsupported configuration: x86_64-linux",
    "not supported for interpreter python",
    # needs external input
    "Please ensure you have set the username and token with config.nix",
    "Quake 3 Arena requires the original pak0.pk3 file",
    "nix-store --add-fixed",
    "nix-prefetch-url",
    "config.cplex.releasePath = /path/to/download",
    "set the environment variable NIX_ITCHIO_API_KEY",
    # licenses based derivation
    "Microsoft Software License Terms are not accepted",
    "commercial license of Silverfort",
    "android_sdk.accept_license = true",
    "dyalog.acceptLicense = true",
    "input-fonts.acceptLicense",
    "joypixels.acceptLicense = true",
    "nvidia.acceptLicense = true",
    "sc2-headless.accept_license = true",
    "segger-jlink.acceptLicense = true",
    "xxe-pe.acceptLicense = true",
)


def fetch_hydra_ids() -> dict[str, int]:
    with urllib.request.urlopen(CSV_URL) as resp:
        content = resp.read().decode()

    reader = csv.DictReader(io.StringIO(content))
    return {row["name"]: int(row["id"]) for row in reader}


def get_status(log: str) -> str:
    if log.endswith("@@@ [SUCCESS] @@@\n"):
        return "success"
    if log.endswith("@@@ [TIMEOUT] @@@\n"):
        return "timeout"
    return "failed"


def is_hash_mismatch(log: str) -> bool:
    return "error: hash mismatch in fixed-output derivation" in log


def run_tag_check(rev_log: str, check: ErrorCheck) -> int | None:
    matched = re.search(check.pattern, rev_log)

    if not matched:
        return None

    if check.hints and any(h not in rev_log for h in check.hints):
        return None

    start, _ = matched.span()
    return 1 + rev_log[start:].count("\n")


def find_error_and_tag(log: str) -> tuple[str, int | None]:
    lines = log.splitlines()
    reversed_log = '\n'.join(lines[::-1])

    for check in TAG_CHECKS:
        line_num = run_tag_check(reversed_log, check)
        if line_num:
            return check.name, line_num

    return "unknown", 1


def main():
    builds = []
    logs = sorted(
        BUILD_LOGS_DIR / entry
        for entry in os.listdir(BUILD_LOGS_DIR)
        if entry.endswith(".log")
    )

    reset_db()
    hydra_ids = fetch_hydra_ids()
    count = 0

    per_tags = defaultdict(list)

    with contextmanager(get_db)() as session:
        for logfile in logs:
            attrpath = logfile.name.removesuffix(".log")
            print("processing", attrpath)

            log = logfile.read_bytes().decode(errors="ignore")
            if get_status(log) != "failed":
                continue

            if (
                any(text in log for text in SKIP_BUILD_LOG_IF_MATCHES)
                or log == "@@@ [FAIL] @@@\n" # empty log
            ):
                continue

            matches = re.findall("error: attribute '.*' missing\n", log)
            if matches:
                continue

            tag, error_line = find_error_and_tag(log)

            build = Build(
                attrpath=attrpath,
                hydra_id=hydra_ids.get(attrpath),
                tag=tag,
                error_line_number=error_line,
            )

            per_tags[build.tag].append(build)
            builds.append(build)
            count += 1

        print("Registered", count, "packages")
        session.add_all(builds)
        session.commit()

        print("\nTagged:")
        tag_names = set(t.name for t in TAG_CHECKS)
        for tag in tag_names:
            print(f"- {tag}:", len(per_tags[tag]))


if __name__ == "__main__":
    main()
