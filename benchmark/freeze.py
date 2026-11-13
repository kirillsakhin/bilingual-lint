"""Pin the defect-planting tool and the data before any rule is tuned.

FROZEN.json records the hash of mutate.py and of both UN sets. A hold-out
score counts only if both still match: the definition of a defect and the
data it is planted in were fixed before the linter was tuned against them.

    python -m benchmark.freeze --data benchmark/data/testsets --archive <tar.gz>
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path

from .un import PARTS, set_hash

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "FROZEN.json"
MUTATE = HERE / "mutate.py"


def code_hash(path: Path) -> str:
    """SHA-256 of a source file with line endings normalised, so a Windows
    checkout that rewrites LF as CRLF hashes the same."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def snapshot(data_root: Path, archive: Path | None = None) -> dict:
    record = {"frozen_on": datetime.date.today().isoformat(),
              "mutate_sha256": code_hash(MUTATE)}
    if archive is not None:
        record["archive"] = archive.name
        record["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    for part in PARTS:
        record[f"{part}_sha256"] = set_hash(data_root, part)
    return record


def problems(data_root: Path | None = None, frozen: Path = FROZEN,
             mutate: Path = MUTATE) -> list:
    """Reasons the current tree does not match the freeze; empty when it does.
    Without data_root only the code is checked."""
    if not frozen.is_file():
        return [f"{frozen.name} does not exist: nothing has been frozen"]
    record = json.loads(frozen.read_text(encoding="utf-8"))
    found = []
    if code_hash(mutate) != record["mutate_sha256"]:
        found.append("mutate.py has changed since the freeze")
    if data_root is not None:
        for part in PARTS:
            if set_hash(data_root, part) != record[f"{part}_sha256"]:
                found.append(f"the {part} files differ from the frozen ones")
    return found


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze the mutation tool and the data.")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args(argv)
    if FROZEN.exists():
        print(f"{FROZEN} already exists. The freeze is made once; a new hold-out "
              "needs a new file name and a note in benchmark/README.md.")
        return 2
    record = snapshot(args.data, args.archive)
    FROZEN.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
