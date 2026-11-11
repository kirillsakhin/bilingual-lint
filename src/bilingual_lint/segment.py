"""Refine pairs into smaller pairs, but only when that is provably safe.

A pair is split by line, then by sentence, only if both sides split into the
same number of parts AND the split does not create a digit disagreement that
the whole pair did not have (which would mean the parts are in another order)."""
from __future__ import annotations

import re
from collections import Counter

from .models import Document, Pair, Segment

BOUNDARY = re.compile(r"(?<=[.!?;])\s+(?=[A-ZА-ЯЁ«\"“(\d])")
LAST_WORD = re.compile(r"([^\W_]+)\.\Z")
ABBREVIATIONS = {
    "no", "art", "cl", "e.g", "i.e", "g", "eg", "ie", "etc", "inc", "ltd", "co", "mr",
    "ms", "mrs", "dr", "vs", "п", "пп", "ст", "г", "гг", "т", "д", "др", "руб", "коп",
    "см", "ул", "им", "тыс", "млн", "млрд", "стр", "рис", "ч",
}
DIGITS = re.compile(r"\d+")
CLAUSE_NUMBER = re.compile(r"[\d.]+\Z")  # "5.1." at the start is not a sentence


def split_sentences(text: str) -> list:
    parts = []
    start = 0
    for m in BOUNDARY.finditer(text):
        head = text[start:m.start()]
        last = LAST_WORD.search(head)
        if last:
            word = last.group(1)
            clause_number = CLAUSE_NUMBER.match(head.strip()) is not None
            if len(word) == 1 or clause_number or word.lower() in ABBREVIATIONS:
                continue
        parts.append(head.strip())
        start = m.end()
    parts.append(text[start:].strip())
    return [part for part in parts if part]


def _digit_gap(a: str, b: str) -> int:
    count_a, count_b = Counter(DIGITS.findall(a)), Counter(DIGITS.findall(b))
    return sum(((count_a - count_b) + (count_b - count_a)).values())


def _split(pair: Pair, splitter) -> list:
    parts_a, parts_b = splitter(pair.a.text), splitter(pair.b.text)
    if len(parts_a) != len(parts_b) or len(parts_a) < 2:
        return [pair]
    whole = _digit_gap(pair.a.text, pair.b.text)
    if sum(_digit_gap(x, y) for x, y in zip(parts_a, parts_b, strict=True)) != whole:
        return [pair]
    out = []
    for number, (text_a, text_b) in enumerate(zip(parts_a, parts_b, strict=True), start=1):
        out.append(Pair(
            0,
            Segment(text_a, pair.a.lang, pair.a.index, f"{pair.a.location}, part {number}"),
            Segment(text_b, pair.b.lang, pair.b.index, f"{pair.b.location}, part {number}"),
            pair.confidence))
    return out


def _lines(text: str) -> list:
    return [line for line in text.split("\n") if line.strip()]


def refine(doc: Document) -> Document:
    pairs: list = []
    for pair in doc.pairs:
        if not pair.complete:
            pairs.append(pair)
            continue
        for by_line in _split(pair, _lines):
            pairs.extend(_split(by_line, split_sentences))
    for number, pair in enumerate(pairs, start=1):
        pair.pair_no = number
    doc.pairs = pairs
    return doc
