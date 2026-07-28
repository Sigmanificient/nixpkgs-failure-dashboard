import csv
import io
import json
import os
import re
import urllib.request
from collections import defaultdict
from contextlib import contextmanager

from .config import RUNTIME_DIR, BUILD_LOGS_DIR
from .db import get_db, init_db
from .models import Build
from .tagging import TAG_CHECKS, ErrorCheck

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Sigmanificient/nixpkgs-failure-notify"
    "/refs/heads/results"
    "/results/trunk/3-failures-x86_64-linux.csv"
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
    reversed_log = "\n".join(lines[::-1])

    for check in TAG_CHECKS:
        line_num = run_tag_check(reversed_log, check)
        if line_num:
            return check.name, line_num

    return "unknown", 1


def main():
    logs = sorted(
        BUILD_LOGS_DIR / entry
        for entry in os.listdir(BUILD_LOGS_DIR)
        if entry.endswith(".log")
    )

    commit = json.loads((RUNTIME_DIR / "last-commit.json").read_text())
    commit_rev = commit["rev"]
    commit_date = commit["date"]

    init_db()
    hydra_ids = fetch_hydra_ids()
    count = 0
    per_tags = defaultdict(list)
    seen_attrpaths = set()

    with contextmanager(get_db)() as session:
        existing: dict[str, Build] = {
            b.attrpath: b for b in session.query(Build).all()
        }

        for logfile in logs:
            attrpath = logfile.name.removesuffix(".log")
            print("processing", attrpath)

            log = logfile.read_bytes().decode(errors="ignore")
            status = get_status(log)
            seen_attrpaths.add(attrpath)

            if status == "success":
                if attrpath in existing:
                    b = existing[attrpath]
                    b.tag = "success"
                    b.hydra_id = hydra_ids.get(attrpath)
                    b.error_line_number = None
                    b.last_success_rev = commit_rev
                    b.last_success_date = commit_date
                else:
                    session.add(
                        Build(
                            attrpath=attrpath,
                            hydra_id=hydra_ids.get(attrpath),
                            tag="success",
                            error_line_number=None,
                            last_success_rev=commit_rev,
                            last_success_date=commit_date,
                        )
                    )
                continue

            if status != "failed":
                continue

            if (
                any(text in log for text in SKIP_BUILD_LOG_IF_MATCHES)
                or log == "@@@ [FAIL] @@@\n"
            ):
                continue

            if re.search("error: attribute '.*' missing\n", log):
                continue

            tag, error_line = find_error_and_tag(log)

            if attrpath in existing:
                b = existing[attrpath]
                b.tag = tag
                b.hydra_id = hydra_ids.get(attrpath)
                b.error_line_number = error_line
            else:
                b = Build(
                    attrpath=attrpath,
                    hydra_id=hydra_ids.get(attrpath),
                    tag=tag,
                    error_line_number=error_line,
                    last_success_rev=None,
                    last_success_date=None,
                )
                session.add(b)

            per_tags[tag].append(attrpath)
            count += 1

        for attrpath, b in existing.items():
            if attrpath not in seen_attrpaths:
                session.delete(b)

        print("Registered", count, "packages")
        session.commit()

        print("\nTagged:")
        tag_names = set(t.name for t in TAG_CHECKS)
        for tag in tag_names:
            print(f"- {tag}:", len(per_tags[tag]))


if __name__ == "__main__":
    main()
