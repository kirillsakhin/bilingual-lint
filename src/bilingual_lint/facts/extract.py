"""Turn one segment of text into a normalised set of facts.

Order matters: each step blanks out what it consumed so a later step cannot
read the same characters again (an e-mail's digits are not 'numbers')."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..wordlists import Wordlists, load_wordlists, lookup
from .dates import DateFact, find_dates
from .numbers import NUM_RE, Quantity, parse_number
from .words import word_digit_mismatches, word_values

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>()«»\"]+", re.IGNORECASE)
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b")
LONG_DIGITS_RE = re.compile(r"(?<![\d.,])\d{9,}(?![\d.,]\d)")
LEADING_RE = re.compile(r"^\s*((?:\d{1,3}\.)+\d{0,3}|\d{1,3}[.)])(?=\s)")
REF_NUMBER_RE = re.compile(r"\d+(?:\.\d+)*")
PREFIX_RE = re.compile(r"(US\$|\$|€|£|₽|¥|(?<![A-Za-z])[A-Z]{3})[\s ]?\Z")


@dataclass
class Facts:
    quantities: list = field(default_factory=list)
    dates: list = field(default_factory=list)
    refs: list = field(default_factory=list)
    leading_number: str | None = None
    identifiers: list = field(default_factory=list)
    word_values: set = field(default_factory=set)
    word_digit_mismatches: list = field(default_factory=list)


def _blank(text: str, start: int, end: int) -> str:
    return text[:start] + " " * (end - start) + text[end:]


def _classify(before: str, after: str, wl: Wordlists) -> tuple[str, str, str]:
    prefix = PREFIX_RE.search(before)
    if prefix:
        token = prefix.group(1)
        iso = wl.symbols.get(token) or (token if token in wl.iso_codes else None)
        if iso:
            return "money", iso, ""
    for iso, pattern in wl.currency_after:
        if pattern.match(after):
            return "money", iso, ""
    if wl.percent_after.match(after):
        return "percent", "", ""
    if wl.duration_after is not None:
        m = wl.duration_after.match(after)
        if m:
            unit = lookup(wl.units, m.group("unit"))
            day_type = lookup(wl.day_types, m.group("day_type") or "")
            return "duration", unit, day_type
    return "number", "", ""


def extract_facts(text: str, lang: str, strict: bool = False) -> Facts:
    wl = load_wordlists(lang)
    facts = Facts()
    work = text

    for pattern, normalise in (
        (EMAIL_RE, str.lower),
        (URL_RE, lambda s: s.rstrip(".,;:").lower()),
        (IBAN_RE, lambda s: s.replace(" ", "")),
        (LONG_DIGITS_RE, str),
    ):
        for m in list(pattern.finditer(work)):
            facts.identifiers.append(normalise(m.group()))
            work = _blank(work, m.start(), m.end())

    leading = LEADING_RE.match(work)
    if leading:
        facts.leading_number = leading.group(1).rstrip(".)")
        work = _blank(work, leading.start(1), leading.end(1))
    if wl.ref_keywords is not None:
        for m in list(wl.ref_keywords.finditer(work)):
            facts.refs.extend(REF_NUMBER_RE.findall(m.group(1)))
            work = _blank(work, m.start(1), m.end(1))

    for start, end, fact in find_dates(work, lang, wl.months):
        facts.dates.append(fact)
        work = _blank(work, start, end)

    for m in NUM_RE.finditer(work):
        cands, primary = parse_number(m.group(), lang, strict)
        kind, unit, day_type = _classify(
            work[max(0, m.start() - 8):m.start()], work[m.end():m.end() + 220], wl)
        facts.quantities.append(
            Quantity(m.group(), cands, primary, kind, unit, day_type))

    facts.word_values = word_values(text, wl.number_words)
    facts.word_digit_mismatches = word_digit_mismatches(
        text, lang, wl.number_words, strict)
    return facts


__all__ = ["DateFact", "Facts", "Quantity", "extract_facts"]
