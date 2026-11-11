"""Wordlists: per-language YAML data compiled into regular expressions.

A language without its own YAML file gets the neutral lists only, so the
language-neutral checks still work for any pair."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

import yaml

# After a number: an optional closing bracket, an optional "(in words)" block,
# then spaces or a hyphen before the unit or currency.
AFTER_HEAD = r"^\)?(?:\s*\([^()]{0,160}\))?[\s -]*"
FLAGS = re.IGNORECASE | re.UNICODE


@dataclass(frozen=True)
class NumberWords:
    values: dict
    hundred: frozenset
    multipliers: dict
    fillers: frozenset

    @property
    def vocabulary(self) -> frozenset:
        return (frozenset(self.values) | self.hundred | frozenset(self.multipliers)
                | self.fillers)


@dataclass(frozen=True)
class Wordlists:
    lang: str
    has_language_rules: bool
    iso_codes: frozenset
    symbols: dict
    currency_after: tuple
    percent_after: re.Pattern
    duration_after: re.Pattern | None
    units: tuple
    day_types: tuple
    months: dict
    ref_keywords: re.Pattern | None
    number_words: NumberWords | None
    raw: dict = field(default_factory=dict)


def _read(name: str) -> dict | None:
    path = resources.files(__package__).joinpath(f"{name}.yaml")
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _alt(patterns: list) -> str:
    return "(?:" + "|".join(patterns) + ")"


def _named(mapping: dict) -> tuple:
    return tuple((name, re.compile(_alt(pats) + r"\Z", FLAGS))
                 for name, pats in mapping.items())


@cache
def load_wordlists(lang: str) -> Wordlists:
    neutral = _read("neutral")
    own = _read(lang) if re.fullmatch(r"[a-z]{2,3}", lang) else None
    data = own or {}

    currency_after = []
    for iso, pats in (data.get("currencies") or {}).items():
        currency_after.append(
            (iso, re.compile(AFTER_HEAD + _alt(pats) + r"(?!\w)", FLAGS)))
    for iso in neutral["iso_codes"]:
        currency_after.append((iso, re.compile(AFTER_HEAD + iso + r"(?!\w)")))
    for symbol, iso in neutral["symbols"].items():
        currency_after.append(
            (iso, re.compile(AFTER_HEAD + re.escape(symbol) + r"(?!\w)")))

    percent = list(neutral["percent"]) + list(data.get("percent") or [])
    percent_after = re.compile(AFTER_HEAD + _alt(percent) + r"(?![^\W\d_])", FLAGS)

    units = data.get("duration_units") or {}
    day_types = data.get("day_types") or {}
    duration_after = None
    if units:
        all_units = [p for pats in units.values() for p in pats]
        all_types = [p for pats in day_types.values() for p in pats] or ["(?!)"]
        duration_after = re.compile(
            AFTER_HEAD + r"(?:(?P<day_type>" + "|".join(all_types) + r")\s+)?"
            + r"(?P<unit>" + "|".join(all_units) + r")(?!\w)", FLAGS)

    keywords = data.get("ref_keywords")
    ref_keywords = None
    if keywords:
        number = r"\d+(?:\.\d+)*"
        ref_keywords = re.compile(
            r"(?<!\w)" + _alt(keywords) + r"\s*(" + number
            + r"(?:\s*(?:,|and|or|to|и|или|по|–|-)\s*" + number + r")*)", FLAGS)

    nw = data.get("number_words")
    number_words = None
    if nw:
        number_words = NumberWords(
            values=dict(nw.get("values") or {}),
            hundred=frozenset(nw.get("hundred") or []),
            multipliers=dict(nw.get("multipliers") or {}),
            fillers=frozenset(nw.get("fillers") or []),
        )

    return Wordlists(
        lang=lang,
        has_language_rules=own is not None,
        iso_codes=frozenset(neutral["iso_codes"]),
        symbols=dict(neutral["symbols"]),
        currency_after=tuple(currency_after),
        percent_after=percent_after,
        duration_after=duration_after,
        units=_named(units),
        day_types=_named(day_types),
        months={str(k).lower(): int(v) for k, v in (data.get("months") or {}).items()},
        ref_keywords=ref_keywords,
        number_words=number_words,
        raw=data,
    )


def lookup(named: tuple, text: str) -> str:
    """Name of the first (name, pattern) entry that fully matches text."""
    for name, pattern in named:
        if pattern.match(text):
            return name
    return ""
