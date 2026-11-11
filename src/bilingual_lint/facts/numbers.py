"""Numbers: find them, normalise them, compare them across two languages.

"1,000" is one thousand in English and exactly one in Russian. Instead of
guessing, an ambiguous token keeps every value it could mean; two tokens
match when their candidate sets overlap."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

THIN = "    "
# digits, optional groups of exactly three after a space or apostrophe,
# optional groups after a dot or comma
NUM_PATTERN = (r"(?<![\w.,])\d+(?:[" + THIN + r"'](?=\d{3}(?!\d))\d{3})*"
               r"(?:[.,]\d+)*")
NUM_RE = re.compile(NUM_PATTERN)
DECIMAL_SEP = {"en": ".", "ru": ","}


@dataclass(frozen=True)
class Quantity:
    raw: str
    cands: frozenset
    primary: Decimal
    kind: str = "number"  # number | money | percent | duration
    unit: str = ""        # ISO currency code, or day/week/month/year/hour
    day_type: str = ""    # "", calendar, business, banking


def parse_number(raw: str, lang: str | None = None,
                 strict: bool = False) -> tuple[frozenset, Decimal]:
    """Return (candidate values, most likely value) for a number token."""
    s = re.sub("[" + THIN + "']", "", raw)
    dots, commas = s.count("."), s.count(",")
    if not dots and not commas:
        value = Decimal(s)
        return frozenset({value}), value
    if dots and commas:
        last = max(s.rfind("."), s.rfind(","))
        whole = re.sub(r"[.,]", "", s[:last])
        value = Decimal(f"{whole}.{s[last + 1:]}")
        return frozenset({value}), value
    sep = "." if dots else ","
    parts = s.split(sep)
    if len(parts) > 2:
        # 1,000,000 is thousands grouping; anything else (1.2.3) is kept as
        # an opaque digit string so both sides still have to agree.
        value = Decimal("".join(parts))
        return frozenset({value}), value
    whole, frac = parts
    as_decimal = Decimal(f"{whole}.{frac}")
    if len(frac) == 3 and 1 <= len(whole) <= 3 and whole != "0":
        as_thousands = Decimal(whole + frac)
        convention = DECIMAL_SEP.get(lang or "")
        if convention is None:
            primary = as_decimal
        else:
            primary = as_decimal if convention == sep else as_thousands
        if strict and convention is not None:
            return frozenset({primary}), primary
        return frozenset({as_decimal, as_thousands}), primary
    return frozenset({as_decimal}), as_decimal


def match_quantities(a: list, b: list) -> tuple[list, list, list]:
    """Pair quantities by value. Returns (matched pairs, only in a, only in b).

    Two passes: exact most-likely value first, then any overlapping candidate.
    This keeps an ambiguous "1,000" from stealing the partner of a plain "1"."""
    matched: list = []
    rest_a: list = []
    rest_b = list(b)
    for qa in a:
        hit = next((qb for qb in rest_b if qb.primary == qa.primary), None)
        if hit is None:
            rest_a.append(qa)
        else:
            rest_b.remove(hit)
            matched.append((qa, hit))
    only_a: list = []
    for qa in rest_a:
        hit = next((qb for qb in rest_b if qa.cands & qb.cands), None)
        if hit is None:
            only_a.append(qa)
        else:
            rest_b.remove(hit)
            matched.append((qa, hit))
    return matched, only_a, rest_b
