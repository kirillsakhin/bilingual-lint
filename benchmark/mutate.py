"""Plant one known defect in one row of a bilingual document.

This file is the benchmark's source of truth for what counts as a defect, so
it shares no code with the linter: standard library only, its own patterns.
It was written and frozen before any rule was tuned against the benchmark.

A document here is a list of (text_a, text_b) rows. Every operator changes
exactly one side of exactly one row and returns a Mutation, or None when the
row gives it nothing to change."""
from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass

# Rules that may legitimately report a changed figure: which one fires depends
# on what the figure was part of (an amount, a date, a period, a reference).
FIGURE_RULES = ("BI001", "BI002", "BI003", "BI004", "BI005", "BI006", "BI009")


@dataclass(frozen=True)
class Mutation:
    operator: str
    row: int          # 0-based row index
    side: str         # "a" or "b"
    before: str       # the fragment that was changed
    after: str        # what it became ("" when text was removed)
    expected: tuple   # rule ids that count as catching it

    def as_dict(self) -> dict:
        return asdict(self)


def _replace(text: str, match: re.Match, new: str) -> str:
    return text[:match.start()] + new + text[match.end():]


def _pick(rng: random.Random, items: list):
    return items[rng.randrange(len(items))] if items else None


# --- figures -----------------------------------------------------------------

# Not a group of thousands: neither "000" in "100 000" nor "100" before it.
NUMBER = re.compile(r"(?<![\w.,/-])(?<!\d[ \u00a0])\d{2,}(?![\w/-])(?![.,]\d)"
                    r"(?![ \u00a0]\d{3}\b)")


def op_digit(text: str, rng: random.Random):
    """Change one digit of a whole number of two or more digits."""
    match = _pick(rng, list(NUMBER.finditer(text)))
    if match is None:
        return None
    digits = list(match.group())
    at = rng.randrange(len(digits))
    choices = [d for d in "123456789" if d != digits[at]]
    digits[at] = choices[rng.randrange(len(choices))]
    return match, "".join(digits), FIGURE_RULES


EN_MONTHS = ("January|February|March|April|May|June|July|August|September|October|"
             "November|December")
RU_MONTHS = ("января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|"
             "ноября|декабря")
DAY_IN_DATE = re.compile(
    rf"(?<!\d)(\d{{1,2}})(?=\s+(?:{EN_MONTHS}|{RU_MONTHS})\s+\d{{4}})")


def op_date(text: str, rng: random.Random):
    """Change the day of a written-out date: 12 March 2025 -> 19 March 2025."""
    match = _pick(rng, list(DAY_IN_DATE.finditer(text)))
    if match is None:
        return None
    day = int(match.group(1))
    choices = [d for d in range(1, 29) if d != day]
    return match, str(choices[rng.randrange(len(choices))]), ("BI003", "BI001")


REFERENCE = re.compile(
    r"(?i)\b(?:clauses?|paragraphs?|articles?|sections?|п\.|пп\.|пункт\w*|стать\w+|"
    r"раздел\w*)\s+(\d+)(?:\.(\d+))?")


def op_reference(text: str, rng: random.Random):
    """Change the last number of a clause reference: clause 2.2 -> clause 2.5."""
    match = _pick(rng, list(REFERENCE.finditer(text)))
    if match is None:
        return None
    group = 2 if match.group(2) else 1
    old = int(match.group(group))
    choices = [n for n in range(1, 10) if n != old]
    new = str(choices[rng.randrange(len(choices))])
    start, end = match.span(group)
    full = text[match.start():start] + new + text[end:match.end()]
    return match, full, ("BI006", "BI001")


# --- wording -----------------------------------------------------------------

CURRENCY_SWAPS = [
    (r"\bUSD\b", "EUR"), (r"\bEUR\b", "USD"),
    (r"\bUS dollars\b", "euros"), (r"\beuros\b", "US dollars"),
    (r"долларов США", "евро"), (r"\bевро\b", "долларов США"),
    (r"\bрублей\b", "долларов США"), (r"\broubles\b", "US dollars"),
    (r"\$", "€"), (r"€", "$"),
]


def op_currency(text: str, rng: random.Random):
    """Name a different currency: USD 150,000 -> EUR 150,000."""
    found = [(m, new) for pattern, new in CURRENCY_SWAPS
             for m in re.finditer(pattern, text)]
    hit = _pick(rng, found)
    return None if hit is None else (hit[0], hit[1], ("BI002",))


DAY_TYPE = re.compile(r"(?i)\b(?:business|working|banking) (?=days?\b)|"
                      r"\b(?:рабочих|рабочего|банковских|банковского) (?=дн)")


def op_day_type(text: str, rng: random.Random):
    """Drop the day type: 10 business days -> 10 days."""
    match = _pick(rng, list(DAY_TYPE.finditer(text)))
    return None if match is None else (match, "", ("BI005",))


NEGATION = re.compile(r"(?i)(?<=\bmay) not\b|(?<=\bshall) not\b|(?<=\bmust) not\b|"
                      r"\bне (?=вправе|должен|должна|должны|может|могут|обязан)")


def op_negation(text: str, rng: random.Random):
    """Drop a negation: may not assign -> may assign."""
    match = _pick(rng, list(NEGATION.finditer(text)))
    return None if match is None else (match, "", ("BI011",))


PREVAILING = [
    (r"(?i)\bEnglish(?= (?:text|version)\b[^.]*\bprevail)", "Russian"),
    (r"(?i)\bRussian(?= (?:text|version)\b[^.]*\bprevail)", "English"),
    (r"(?i)(?<=преимущество имеет текст на )русском", "английском"),
    (r"(?i)(?<=преимущество имеет текст на )английском", "русском"),
]


def op_prevailing(text: str, rng: random.Random):
    """Flip which language prevails, on one side only."""
    found = [(m, new) for pattern, new in PREVAILING for m in re.finditer(pattern, text)]
    hit = _pick(rng, found)
    return None if hit is None else (hit[0], hit[1], ("BI010",))


IDENTIFIER = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b|"
                        r"\b\d{10,15}\b")


def op_identifier(text: str, rng: random.Random):
    """Change the last digit of an IBAN or a long registration number."""
    match = _pick(rng, list(IDENTIFIER.finditer(text)))
    if match is None or not match.group()[-1].isdigit():
        return None
    last = match.group()[-1]
    choices = [d for d in "0123456789" if d != last]
    return match, match.group()[:-1] + choices[rng.randrange(len(choices))], ("BI009",)


def op_party(text: str, rng: random.Random, parties: list):
    """Swap a party's defined name for the other party's, where only one is
    named. parties: the two names used on this side, e.g. ["Seller", "Buyer"]."""
    if len(parties) != 2:
        return None
    present = [name for name in parties if re.search(rf"\b{re.escape(name)}\b", text)]
    if len(present) != 1:
        return None
    other = parties[1] if present[0] == parties[0] else parties[0]
    match = _pick(rng, list(re.finditer(rf"\b{re.escape(present[0])}\b", text)))
    return match, other, ("BI008",)


TEXT_OPERATORS = {
    "digit": op_digit, "date": op_date, "reference": op_reference,
    "currency": op_currency, "day_type": op_day_type, "negation": op_negation,
    "prevailing": op_prevailing, "identifier": op_identifier,
}
OPERATORS = (*TEXT_OPERATORS, "party", "drop")
MIN_DROP_CHARS = 40   # dropping a three-word heading is not the defect we mean


def mutate(rows: list, operator: str, row: int, side: str, rng: random.Random,
           parties: dict | None = None):
    """Return (new_rows, Mutation), or None if the operator has nothing to
    change in that cell. rows is not modified."""
    index = 0 if side == "a" else 1
    text = rows[row][index]
    if operator == "drop":
        if len(text) < MIN_DROP_CHARS:
            return None
        before, new_text, after, expected = text, "", "", ("BI007",)
    else:
        if operator == "party":
            result = op_party(text, rng, (parties or {}).get(side, []))
        else:
            result = TEXT_OPERATORS[operator](text, rng)
        if result is None:
            return None
        match, after, expected = result
        before, new_text = match.group(), _replace(text, match, after)
        if new_text == text:
            return None
    new_rows = [list(r) for r in rows]
    new_rows[row][index] = new_text
    return ([tuple(r) for r in new_rows],
            Mutation(operator, row, side, before, after, tuple(expected)))


def all_mutations(rows: list, seed: int, parties: dict | None = None,
                  operators: tuple = OPERATORS, per_operator: int | None = None) -> list:
    """Every (operator, row, side) that yields a mutation, in a fixed order.
    With per_operator, keep at most that many per operator, chosen by seed."""
    out = []
    for operator in operators:
        found = []
        for row in range(len(rows)):
            for side in ("a", "b"):
                rng = random.Random(f"{seed}:{operator}:{row}:{side}")
                result = mutate(rows, operator, row, side, rng, parties)
                if result is not None:
                    found.append(result)
        if per_operator is not None and len(found) > per_operator:
            random.Random(f"{seed}:{operator}:pick").shuffle(found)
            found = sorted(found[:per_operator], key=lambda r: (r[1].row, r[1].side))
        out.extend(found)
    return out
