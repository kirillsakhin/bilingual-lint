"""Read the United Nations Parallel Corpus v1.0 test sets.

The archive holds two sets of 4,000 sentences, aligned one to one across the
six languages: 'devset' (documents of January-March 2015) and 'testset'
(April-June 2015). Each language is one UTF-8 file, one sentence per line;
the .ids file names the source document of each line.

The sentences are a sample, not whole documents, so a benchmark document is
a block of consecutive lines."""
from __future__ import annotations

import hashlib
from pathlib import Path

PARTS = ("devset", "testset")
BLOCK = 40   # rows per benchmark document


def _lines(path: Path) -> list:
    lines = path.read_text(encoding="utf-8").split("\n")
    return lines[:-1] if lines and lines[-1] == "" else lines


def set_files(root: Path, part: str, langs: tuple = ("en", "ru")) -> list:
    if part not in PARTS:
        raise ValueError(f"part must be one of {PARTS}, not {part!r}")
    return [root / part / f"UNv1.0.{part}.{suffix}" for suffix in (*langs, "ids")]


def load_set(root: Path, part: str, langs: tuple = ("en", "ru")) -> list:
    """Rows of the set as (text_a, text_b, document_id), in file order."""
    *texts, ids = (_lines(path) for path in set_files(root, part, langs))
    if not len(texts[0]) == len(texts[1]) == len(ids):
        raise ValueError(f"{part}: the language files and the ids file differ in length")
    return [(a, b, line.split(" ", 1)[0]) for a, b, line in zip(*texts, ids, strict=True)]


def documents(rows: list, block: int = BLOCK) -> list:
    """Cut the set into benchmark documents: lists of (text_a, text_b) of
    'block' rows each. A short tail is kept as its own document."""
    pairs = [(a, b) for a, b, _ in rows]
    return [pairs[i:i + block] for i in range(0, len(pairs), block)]


def set_hash(root: Path, part: str, langs: tuple = ("en", "ru")) -> str:
    """SHA-256 over the set's files, in a fixed order. Pins the data a result
    was scored on."""
    digest = hashlib.sha256()
    for path in set_files(root, part, langs):
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()
