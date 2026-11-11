"""Numbers written in words: 'ten', 'сто тысяч', and the 'ten (10)' pattern."""
from __future__ import annotations

import re
from decimal import Decimal

from ..wordlists import NumberWords
from .numbers import NUM_PATTERN, parse_number

TOKEN_RE = re.compile(r"[^\W\d_]+")
GAP_RE = re.compile(r"[\s -]*\Z")
DIGITS_THEN_WORDS = re.compile(r"(" + NUM_PATTERN + r")\s*\(([^()\d]{2,160})\)")
WORDS_THEN_DIGITS = re.compile(r"\(\s*(" + NUM_PATTERN + r")\s*\)")
MAX_TRAILING_WORDS = 3


def _tokens(text: str) -> list:
    return [(m.group().lower().replace("ё", "е"), m.start(), m.end())
            for m in TOKEN_RE.finditer(text)]


def parse_number_words(words: list, nw: NumberWords) -> int | None:
    """'two hundred and five' -> 205. None if any word is not a number word."""
    total = current = 0
    seen = False
    for word in words:
        if word in nw.fillers:
            continue
        if word in nw.values:
            current += nw.values[word]
        elif word in nw.hundred:
            current = (current or 1) * 100
        elif word in nw.multipliers:
            total += (current or 1) * nw.multipliers[word]
            current = 0
        else:
            return None
        seen = True
    return total + current if seen else None


def _runs(text: str, nw: NumberWords) -> list:
    """Maximal runs of adjacent number words, as lists of (word, start, end)."""
    vocabulary = nw.vocabulary
    runs: list = []
    current: list = []
    for token in _tokens(text):
        word, start, _ = token
        adjacent = bool(current) and GAP_RE.match(text[current[-1][2]:start])
        if word in vocabulary and (not current or adjacent):
            current.append(token)
            continue
        if current:
            runs.append(current)
        current = [token] if word in vocabulary else []
    if current:
        runs.append(current)
    cleaned = []
    for run in runs:
        while run and run[0][0] in nw.fillers:
            run = run[1:]
        while run and run[-1][0] in nw.fillers:
            run = run[:-1]
        if run:
            cleaned.append(run)
    return cleaned


def word_values(text: str, nw: NumberWords | None) -> set:
    """Every number spelled out in the text, as Decimal values."""
    if nw is None:
        return set()
    values = set()
    for run in _runs(text, nw):
        value = parse_number_words([word for word, _, _ in run], nw)
        if value is not None:
            values.add(Decimal(value))
    return values


def word_digit_mismatches(text: str, lang: str, nw: NumberWords | None,
                          strict: bool = False) -> list:
    """Find 'ten (15)' and '15 (ten)'. Returns [(digits, words)]."""
    if nw is None:
        return []
    out: list = []
    vocabulary = nw.vocabulary
    for m in DIGITS_THEN_WORDS.finditer(text):
        inner = [word for word, _, _ in _tokens(m.group(2))]
        prefix: list = []
        for word in inner:
            if word not in vocabulary:
                break
            prefix.append(word)
        while prefix and prefix[-1] in nw.fillers:
            prefix.pop()
        if not prefix or len(inner) - len(prefix) > MAX_TRAILING_WORDS:
            continue
        value = parse_number_words(prefix, nw)
        cands, _ = parse_number(m.group(1), lang, strict)
        if value is not None and Decimal(value) not in cands:
            out.append((m.group(1), " ".join(prefix)))
    for m in WORDS_THEN_DIGITS.finditer(text):
        before = text[max(0, m.start() - 160):m.start()]
        runs = _runs(before, nw)
        if not runs or not GAP_RE.match(before[runs[-1][-1][2]:]):
            continue
        words = [word for word, _, _ in runs[-1]]
        value = parse_number_words(words, nw)
        cands, _ = parse_number(m.group(1), lang, strict)
        if value is not None and Decimal(value) not in cands:
            out.append((m.group(1), " ".join(words)))
    return out
