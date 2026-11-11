"""Dates: numeric, ISO and written-month forms, normalised to datetime.date."""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

ISO_RE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
NUMERIC_RE = re.compile(r"(?<![\d.,/-])(\d{1,2})([./-])(\d{1,2})\2(\d{4}|\d{2})(?!\d)")
# Languages whose numeric dates are always day-month-year.
DAY_FIRST = {"ru"}


@dataclass(frozen=True)
class DateFact:
    raw: str
    value: dt.date
    alt: dt.date | None = None  # the other reading of an ambiguous 02/03/2025


def _year(text: str) -> int:
    year = int(text)
    if year >= 100:
        return year
    return 2000 + year if year < 70 else 1900 + year


def _make(year: int, month: int, day: int) -> dt.date | None:
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def _written_patterns(months: dict) -> list:
    if not months:
        return []
    names = "|".join(sorted((re.escape(m) for m in months), key=len, reverse=True))
    flags = re.IGNORECASE | re.UNICODE
    day_month_year = re.compile(
        r"(?<!\d)[«\"“]?(\d{1,2})[»\"”]?(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?"
        r"(" + names + r")\.?,?\s+(\d{4})(?!\d)", flags)
    month_day_year = re.compile(
        r"(?<!\w)(" + names + r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})(?!\d)",
        flags)
    return [("dmy", day_month_year), ("mdy", month_day_year)]


def find_dates(text: str, lang: str, months: dict) -> list:
    """Return [(start, end, DateFact)] sorted by position, never overlapping."""
    found: list = []
    work = text

    def take(match: re.Match, fact: DateFact | None) -> None:
        nonlocal work
        if fact is None:
            return
        found.append((match.start(), match.end(), fact))
        work = work[:match.start()] + " " * (match.end() - match.start()) \
            + work[match.end():]

    for order, pattern in _written_patterns(months):
        for m in list(pattern.finditer(work)):
            if order == "dmy":
                day, month, year = int(m.group(1)), months[m.group(2).lower()], m.group(3)
            else:
                month, day, year = months[m.group(1).lower()], int(m.group(2)), m.group(3)
            value = _make(int(year), month, day)
            take(m, DateFact(m.group(), value) if value else None)
    for m in list(ISO_RE.finditer(work)):
        value = _make(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        take(m, DateFact(m.group(), value) if value else None)
    for m in list(NUMERIC_RE.finditer(work)):
        first, second, year = int(m.group(1)), int(m.group(3)), _year(m.group(4))
        day_first = _make(year, second, first)
        month_first = _make(year, first, second)
        if lang in DAY_FIRST or month_first is None or first == second:
            take(m, DateFact(m.group(), day_first) if day_first else None)
        elif day_first is None:
            take(m, DateFact(m.group(), month_first))
        else:
            take(m, DateFact(m.group(), day_first, alt=month_first))
    found.sort(key=lambda item: item[0])
    return found


def match_dates(a: list, b: list) -> tuple[list, list, list]:
    """Returns (ambiguous matches, only in a, only in b). An ambiguous match
    agrees only under the alternative day/month reading."""
    rest_a: list = []
    rest_b = list(b)
    for da in a:
        hit = next((db for db in rest_b if db.value == da.value), None)
        if hit is None:
            rest_a.append(da)
        else:
            rest_b.remove(hit)
    ambiguous: list = []
    only_a: list = []
    for da in rest_a:
        mine = {da.value, da.alt} - {None}
        hit = next((db for db in rest_b if mine & ({db.value, db.alt} - {None})), None)
        if hit is None:
            only_a.append(da)
        else:
            rest_b.remove(hit)
            ambiguous.append((da, hit))
    return ambiguous, only_a, rest_b
