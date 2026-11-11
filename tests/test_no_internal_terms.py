"""Confidentiality guard: no internal or firm terms may enter the public tree.

Terms are assembled by concatenation so this file never matches itself.
If a term ever fires on a legitimate word, refine it to a word-boundary
regex — do not drop the guard.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ["".join(p) for p in [
    ("s", "bp"), ("sb", "plaw"), ("save", "liev"), ("bata", "nov"),
    ("lex", "ie"), ("arch", "ie"), ("cl", "io"), ("10.0.", "20."),
    ("tail", "scale"), ("henr", "y-1"),
]]
BINARY = (".png", ".docx")


def tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout.splitlines()
    return [ROOT / p for p in out if not p.endswith(BINARY) and (ROOT / p).is_file()]


def test_no_internal_terms_in_tracked_files():
    hits = []
    for path in tracked_text_files():
        if path == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for term in FORBIDDEN:
            if term in text:
                hits.append((str(path.relative_to(ROOT)), term))
    assert hits == [], f"internal terms found: {hits}"
