"""Load a bilingual contract laid out as a two-column table."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..models import Document, Finding, Pair, Segment, Severity
from ..text_utils import DEFAULT_LANG, letters, script_for_lang, script_of
from .docx_reader import LoaderError, read_docx

MIN_LETTERS = 3


def pick_columns(rows: list, langs: tuple | None) -> tuple | None:
    """Find the two text columns of a table and the language of each.
    Returns (left column, right column, left language, right language) or None
    when the table is not bilingual."""
    profile: dict = {}
    for row in rows:
        for column, text in row.items():
            count = letters(text)
            if count < MIN_LETTERS:
                continue
            entry = profile.setdefault(column, [0, Counter()])
            entry[0] += count
            entry[1][script_of(text)] += 1
    if len(profile) < 2:
        return None
    heaviest = sorted(profile, key=lambda c: -profile[c][0])[:2]
    left, right = sorted(heaviest)
    script_left = profile[left][1].most_common(1)[0][0]
    script_right = profile[right][1].most_common(1)[0][0]
    if langs is None:
        if {script_left, script_right} != {"latin", "cyrillic"}:
            return None
        return left, right, DEFAULT_LANG[script_left], DEFAULT_LANG[script_right]
    first, second = langs
    want_first, want_second = script_for_lang(first), script_for_lang(second)
    if want_first != want_second:
        if (script_left, script_right) == (want_first, want_second):
            return left, right, first, second
        if (script_left, script_right) == (want_second, want_first):
            return left, right, second, first
        return None
    if script_left == script_right == want_first:
        return left, right, first, second  # same script: trust the column order
    return None


def _has_text(row: dict) -> bool:
    return any(letters(text) for text in row.values())


def load_two_column(path: Path, langs: tuple | None = None) -> Document:
    blocks, notes = read_docx(path)
    pairs: list = []
    outside: list = []
    doc_langs: tuple | None = None
    for block in blocks:
        if block.kind == "paragraph":
            outside.append(block.location)
            continue
        picked = pick_columns(block.rows, langs)
        if picked is not None:
            col_a, col_b, lang_a, lang_b = picked
            if doc_langs is None:
                doc_langs = (lang_a, lang_b)
            elif (lang_a, lang_b) == doc_langs[::-1]:
                col_a, col_b = col_b, col_a  # this table has the columns swapped
            elif (lang_a, lang_b) != doc_langs:
                picked = None
        for number, row in enumerate(block.rows, start=1):
            location = f"{block.location}, row {number}"
            if picked is None or col_a not in row or col_b not in row:
                if _has_text(row):
                    outside.append(location)
                continue
            text_a, text_b = row[col_a], row[col_b]
            if not text_a.strip() and not text_b.strip():
                continue
            index = len(pairs)
            pairs.append(Pair(index + 1,
                              Segment(text_a, doc_langs[0], index, location),
                              Segment(text_b, doc_langs[1], index, location)))
    if not pairs or doc_langs is None:
        raise LoaderError(
            f"no two-language table found in {Path(path).name}. For two separate "
            "files pass both paths; for languages that share a script pass --langs")

    findings = [Finding("BI000", Severity.INFO, note) for note in notes]
    if outside:
        findings.append(Finding(
            "BI000", Severity.INFO,
            f"{len(outside)} block(s) of text outside the bilingual table were not checked",
            context={"locations": outside}))
    return Document(pairs, doc_langs[0], doc_langs[1], "two-column", [Path(path)], findings)
