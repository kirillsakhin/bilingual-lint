# bilingual-lint v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `bilingual-lint`, a command-line linter that reports where the two language versions of a bilingual contract disagree.

**Architecture:** A pipeline of small modules: load a DOCX into paired segments, extract normalised facts from each side (numbers, money, dates, durations, references, identifiers), compare them with deterministic rules, report. An optional model pass looks only at pairs the rules cannot settle.

**Tech Stack:** Python >= 3.10, typer, rich, pyyaml, python-docx; pytest and ruff for development; litellm as an optional extra.

**Spec:** `docs/superpowers/specs/2026-11-11-bilingual-lint-design.md`

---

## Read this first

**Status of the code in this plan.** Every code block below was run as a prototype before the plan was written: all 208 tests pass, `ruff check .` is clean, each "prove the guard" step was confirmed to turn its test red, and a clean `pip install .` into a fresh environment produced a working command. That was on Windows with Python 3.14. It has not been run on Linux or on Python 3.10 to 3.13; the CI matrix in Task 16 is the first check of those. Follow the steps in order anyway. The failing-test step in each task proves the test can fail, which a copied file alone does not.

**Scope of this plan.** The linter, its examples, its documentation and CI. The benchmark described in section 9 of the spec is a separate plan. It is blocked until the licence terms of the public source texts are confirmed, and it needs working software to measure.

**Where the plan departs from the spec, and why.**

| Spec | Plan | Reason |
|---|---|---|
| Text outside the bilingual table is "reported as unpaired" | Reported once as a BI000 note listing the locations | A title above the table is not a missing translation; one BI007 error per stray paragraph would bury real findings |
| Sentence split when both sides have the same number of sentences | Same, plus a guard: the split is dropped if it would create a digit disagreement the whole pair did not have | Sentences are sometimes reordered in translation; without the guard that produces false errors |
| BI010 fires on a one-sided or contradictory clause | Also an `info` note when no prevailing-language clause exists at all, or when the tool cannot tell which language is named | A missing clause is worth knowing; an unreadable one must not be guessed |
| Model answers are "marked as model suggestions" | They are separate findings with rule id `LLM` | Keeps them visibly apart from rule findings in every report format |
| Length-based pairing between anchors | Same, plus a small cost when the two sides carry different digits | Without it a short heading with no counterpart is absorbed into its neighbour |

**Conventions.**

- Commands are written for a POSIX shell (Git Bash on Windows). The virtual environment's interpreter is `.venv/Scripts/python.exe` on Windows and `.venv/bin/python` elsewhere; the plan writes `PY` for it. Set it once per shell: `PY=.venv/Scripts/python.exe`.
- If `python` is not on your PATH, use the full path to your interpreter in Task 0.
- On a Windows console set `PYTHONIOENCODING=utf-8` before running anything that prints Russian text.
- All example and test data is invented. No real documents enter the repository, ever.
- Create every file with LF line endings and UTF-8 encoding.

## File map

```
pyproject.toml, LICENSE, README.md, CHANGELOG.md, CONTRIBUTING.md
.gitignore, .gitattributes, .github/workflows/ci.yml
src/bilingual_lint/
  __init__.py            version
  __main__.py            python -m bilingual_lint
  models.py              Severity, Segment, Pair, Finding, Document
  text_utils.py          script detection, whitespace cleaning
  wordlists/             neutral.yaml, en.yaml, ru.yaml + loader that compiles them
  facts/
    numbers.py           number tokens, candidate values, matching
    dates.py             date forms, matching
    words.py             numbers in words, "ten (10)" checks
    extract.py           text -> Facts (uses the three above)
  pairing.py             pair paragraphs of two files
  loaders/
    docx_reader.py       DOCX -> ordered blocks, tracked changes read as accepted
    two_column.py        bilingual table -> Document
    two_files.py         two files -> Document
  segment.py             split pairs by line and sentence when safe
  analysis.py            attach Facts to every complete pair
  config.py              .bilingual-lint.yaml, rule defaults
  rules/
    base.py              Rule protocol, shared helpers
    bi001 ... bi011      one file per rule
    __init__.py          registry and run_all
  report/                console.py, json_out.py, markdown.py
  llm/reviewer.py        optional model pass
  cli.py                 check, rules, init
examples/                build_examples.py + four generated .docx files
tests/                   mirrors src; helpers.py builds documents
```

---

### Task 0: Repository skeleton

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.gitattributes`, `LICENSE`, `src/bilingual_lint/__init__.py`, `tests/__init__.py`, `tests/facts/__init__.py`, `tests/rules/__init__.py`

- [ ] **Step 1: Initialise git and check the commit identity**

```bash
cd /path/to/bilingual-lint
git init -b main
git config user.name
git config user.email
```

Expected: the name and e-mail you want in public history. Fix them with `git config user.email ...` now if not; rewriting history later is painful.

- [ ] **Step 2: Create `pyproject.toml`**

````toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bilingual-lint"
dynamic = ["version"]
description = "A linter for bilingual legal documents — find where the two language versions of a contract disagree on numbers, dates, amounts, clauses and the prevailing language"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
authors = [{ name = "Kirill Sakhin" }]
keywords = ["legal", "contracts", "bilingual", "translation", "linter", "legal-tech", "docx"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Environment :: Console",
  "Intended Audience :: Legal Industry",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Topic :: Office/Business",
  "Topic :: Text Processing :: Linguistic",
]
dependencies = ["typer>=0.12", "rich>=13.0", "pyyaml>=6.0", "python-docx>=1.1"]

[project.optional-dependencies]
llm = ["litellm>=1.40"]
dev = ["pytest>=8.0", "ruff>=0.6"]

[project.urls]
Homepage = "https://github.com/kirillsakhin/bilingual-lint"
Issues = "https://github.com/kirillsakhin/bilingual-lint/issues"
Changelog = "https://github.com/kirillsakhin/bilingual-lint/blob/main/CHANGELOG.md"

[project.scripts]
bilingual-lint = "bilingual_lint.cli:app"

[tool.hatch.version]
path = "src/bilingual_lint/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["src/bilingual_lint"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.ruff.lint.per-file-ignores]
# B008/UP045: typer's documented signature idiom (Option/Argument defaults, Optional[X])
"src/bilingual_lint/cli.py" = ["B008", "UP045"]
````

- [ ] **Step 3: Create `.gitignore`**

````text
.venv/
__pycache__/
*.pyc
dist/
build/
*.egg-info/
.pytest_cache/
.ruff_cache/
````

- [ ] **Step 4: Create `.gitattributes`**

````text
* text=auto eol=lf
*.docx binary
*.png binary
````

- [ ] **Step 5: Create `LICENSE`** with the standard MIT licence text, first lines:

```text
MIT License

Copyright (c) 2026 Kirill Sakhin
```

followed by the unmodified MIT permission and warranty paragraphs.

Also create a one-line `README.md` now (`# bilingual-lint`). `pyproject.toml` names it as the readme, and the install in Step 7 fails without it. Task 16 replaces it with the real one.

- [ ] **Step 6: Create the package and test packages**

`src/bilingual_lint/__init__.py`:

````python
__version__ = "0.1.0"
````

Create three empty files: `tests/__init__.py`, `tests/facts/__init__.py`, `tests/rules/__init__.py`.

- [ ] **Step 7: Create the environment and install**

```bash
python -m venv .venv
PY=.venv/Scripts/python.exe        # .venv/bin/python on Linux and macOS
$PY -m pip install -e ".[dev]"
$PY -c "import bilingual_lint, docx, typer; print(bilingual_lint.__version__)"
```

Expected: `0.1.0`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "chore: project skeleton"
```

---

### Task 1: Data model and text utilities

**Files:**
- Create: `src/bilingual_lint/models.py`, `src/bilingual_lint/text_utils.py`
- Test: `tests/test_text_utils.py`

- [ ] **Step 1: Write the failing test** `tests/test_text_utils.py`

````python
from bilingual_lint.text_utils import clean, letters, script_for_lang, script_of


def test_script_of():
    assert script_of("The Buyer shall pay") == "latin"
    assert script_of("Покупатель оплачивает") == "cyrillic"
    assert script_of("ООО «Альфа» и Beta GmbH договорились") == "cyrillic"
    assert script_of("Préstamo en España") == "latin"
    assert script_of("合同") == "other"
    assert script_of("12 345 — 67%") == "none"


def test_script_for_lang():
    assert script_for_lang("ru") == "cyrillic"
    assert script_for_lang("en") == "latin"
    assert script_for_lang("es") == "latin"


def test_letters_counts_only_letters():
    assert letters("No. 15, п. 2") == 3


def test_clean_keeps_line_breaks_and_no_break_spaces():
    assert clean("  a \t b  \n\n  c d ") == "a b\nc d"
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/test_text_utils.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'bilingual_lint.text_utils'`

- [ ] **Step 3: Create `src/bilingual_lint/text_utils.py`**

````python
from __future__ import annotations

import re

CYRILLIC_LANGS = {"ru", "uk", "be", "bg", "sr", "mk", "kk", "ky", "tg", "mn"}
DEFAULT_LANG = {"latin": "en", "cyrillic": "ru"}
_SPACES = re.compile(r"[ \t\r\f\v]+")


def letters(text: str) -> int:
    return sum(1 for ch in text if ch.isalpha())


def script_of(text: str) -> str:
    """'latin', 'cyrillic', 'other' (letters of another script) or 'none'."""
    latin = cyrillic = other = 0
    for ch in text:
        if not ch.isalpha():
            continue
        if "Ѐ" <= ch <= "ԯ":
            cyrillic += 1
        elif ch.isascii() or "À" <= ch <= "ɏ":
            latin += 1
        else:
            other += 1
    if not (latin or cyrillic or other):
        return "none"
    return max((("latin", latin), ("cyrillic", cyrillic), ("other", other)),
               key=lambda item: item[1])[0]


def script_for_lang(lang: str) -> str:
    return "cyrillic" if lang in CYRILLIC_LANGS else "latin"


def clean(text: str) -> str:
    """Collapse runs of spaces and tabs; keep line breaks and no-break spaces."""
    lines = [_SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)
````

- [ ] **Step 4: Create `src/bilingual_lint/models.py`**

````python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .facts.extract import Facts


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"error": 2, "warning": 1, "info": 0}[self.value]


@dataclass
class Segment:
    """One unit of text on one side. location is human-readable, e.g.
    'table 1, row 4' or 'paragraph 17'."""

    text: str
    lang: str
    index: int
    location: str


@dataclass
class Pair:
    pair_no: int
    a: Segment | None
    b: Segment | None
    confidence: float = 1.0
    facts_a: Facts | None = None
    facts_b: Facts | None = None

    @property
    def complete(self) -> bool:
        return bool(self.a and self.b and self.a.text.strip() and self.b.text.strip())


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    message: str
    pair: Pair | None = None
    context: dict = field(default_factory=dict)


@dataclass
class Document:
    pairs: list[Pair]
    lang_a: str
    lang_b: str
    mode: Literal["two-column", "two-files"]
    source_paths: list[Path]
    notes: list[Finding] = field(default_factory=list)  # BI000, set by loaders

    def complete_pairs(self) -> list[Pair]:
        return [p for p in self.pairs if p.complete]

    def side(self, lang: str) -> str | None:
        """'a' or 'b' for the side written in lang, else None."""
        if self.lang_a == lang:
            return "a"
        if self.lang_b == lang:
            return "b"
        return None
````

- [ ] **Step 5: Run the test**

Run: `$PY -m pytest tests/test_text_utils.py -q`
Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: data model and script detection"
```

---

### Task 2: Numbers

The heart of the tool. `1,000` means one thousand in English and one in Russian, so an ambiguous token keeps every value it could mean, and two tokens match when their candidate sets overlap.

**Files:**
- Create: `src/bilingual_lint/facts/__init__.py` (empty), `src/bilingual_lint/facts/numbers.py`
- Test: `tests/facts/test_numbers.py`

- [ ] **Step 1: Write the failing test** `tests/facts/test_numbers.py`

````python
from decimal import Decimal as D

import pytest

from bilingual_lint.facts.numbers import NUM_RE, Quantity, match_quantities, parse_number


def q(raw, lang):
    cands, primary = parse_number(raw, lang)
    return Quantity(raw, cands, primary)


@pytest.mark.parametrize("text, expected", [
    ("pay 1,000,000.50 now", ["1,000,000.50"]),
    ("сумма 1 000 000,50 руб.", ["1 000 000,50"]),
    ("сумма 1 000 руб.", ["1 000"]),
    ("items 10, 20 and 30.", ["10", "20", "30"]),
    ("version A4 and v2", []),
    ("the year 2025.", ["2025"]),
    ("12 345 678", ["12 345 678"]),
])
def test_number_tokens(text, expected):
    assert NUM_RE.findall(text) == expected


@pytest.mark.parametrize("raw, lang, cands, primary", [
    ("1000", "en", {D(1000)}, D(1000)),
    ("1 000 000,50", "ru", {D("1000000.50")}, D("1000000.50")),
    ("1,000,000.50", "en", {D("1000000.50")}, D("1000000.50")),
    ("1.000,00", "ru", {D(1000)}, D(1000)),
    ("1,000,000", "en", {D(1000000)}, D(1000000)),
    ("1,000", "en", {D(1000), D(1)}, D(1000)),
    ("1,000", "ru", {D(1000), D(1)}, D(1)),
    ("1.000", "ru", {D(1000), D(1)}, D(1000)),
    ("0,125", "ru", {D("0.125")}, D("0.125")),
    ("3.5", "en", {D("3.5")}, D("3.5")),
    ("12,5", "ru", {D("12.5")}, D("12.5")),
])
def test_parse_number(raw, lang, cands, primary):
    assert parse_number(raw, lang) == (frozenset(cands), primary)


def test_strict_mode_drops_the_ambiguity():
    assert parse_number("1,000", "en", strict=True) == (frozenset({D(1000)}), D(1000))
    assert parse_number("1,000", "ru", strict=True) == (frozenset({D(1)}), D(1))


def test_same_amount_in_two_conventions_matches():
    matched, only_a, only_b = match_quantities([q("1,000.00", "en")], [q("1 000,00", "ru")])
    assert len(matched) == 1 and only_a == [] and only_b == []


def test_changed_digit_is_reported_on_both_sides():
    matched, only_a, only_b = match_quantities(
        [q("150,000", "en"), q("30", "en")], [q("105 000", "ru"), q("30", "ru")])
    assert [x.raw for x in only_a] == ["150,000"]
    assert [x.raw for x in only_b] == ["105 000"]
    assert len(matched) == 1


def test_ambiguous_token_does_not_steal_an_exact_partner():
    a = [q("1,000", "en"), q("1", "en")]
    b = [q("1", "ru"), q("1000", "ru")]
    matched, only_a, only_b = match_quantities(a, b)
    assert only_a == [] and only_b == [] and len(matched) == 2


def test_repeated_numbers_are_counted():
    _, only_a, only_b = match_quantities([q("5", "en"), q("5", "en")], [q("5", "ru")])
    assert [x.raw for x in only_a] == ["5"] and only_b == []
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/facts/test_numbers.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.facts'`

- [ ] **Step 3: Create the empty `src/bilingual_lint/facts/__init__.py` and `src/bilingual_lint/facts/numbers.py`**

````python
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
````

- [ ] **Step 4: Run the test**

Run: `$PY -m pytest tests/facts/test_numbers.py -q`
Expected: `23 passed`

- [ ] **Step 5: Prove the guard.** In `match_quantities`, temporarily delete the first pass (the loop that matches on `primary`) so every quantity goes straight to the candidate pass. Run the test again.

Expected: `test_ambiguous_token_does_not_steal_an_exact_partner` fails. Restore the code; expected `23 passed`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: number parsing with ambiguous-separator candidates"
```

---

### Task 3: Wordlists and dates

Language data lives in YAML, not in code. Every list entry is a regular-expression fragment. A language without its own file gets the neutral lists only.

**Files:**
- Create: `src/bilingual_lint/wordlists/neutral.yaml`, `en.yaml`, `ru.yaml`, `src/bilingual_lint/wordlists/__init__.py`, `src/bilingual_lint/facts/dates.py`
- Test: `tests/facts/test_dates.py`

- [ ] **Step 1: Write the failing test** `tests/facts/test_dates.py`

````python
import datetime as dt

import pytest

from bilingual_lint.facts.dates import DateFact, find_dates, match_dates
from bilingual_lint.wordlists import load_wordlists


def dates(text, lang):
    return [fact for _, _, fact in find_dates(text, lang, load_wordlists(lang).months)]


@pytest.mark.parametrize("text, lang, value", [
    ("signed on 12 March 2025 in London", "en", dt.date(2025, 3, 12)),
    ("signed on March 12, 2025", "en", dt.date(2025, 3, 12)),
    ("on the 12th day of March 2025", "en", dt.date(2025, 3, 12)),
    ("подписан 12 марта 2025 г.", "ru", dt.date(2025, 3, 12)),
    ("подписан «12» марта 2025 года", "ru", dt.date(2025, 3, 12)),
    ("подписан 12.03.2025", "ru", dt.date(2025, 3, 12)),
    ("подписан 12.03.25", "ru", dt.date(2025, 3, 12)),
    ("effective 2025-03-12", "en", dt.date(2025, 3, 12)),
    ("effective 25/03/2025", "en", dt.date(2025, 3, 25)),
    ("effective 03/25/2025", "en", dt.date(2025, 3, 25)),
])
def test_date_forms(text, lang, value):
    found = dates(text, lang)
    assert [d.value for d in found] == [value]
    assert found[0].alt is None


def test_ambiguous_numeric_date_keeps_both_readings():
    (fact,) = dates("effective 02/03/2025", "en")
    assert fact.value == dt.date(2025, 3, 2)
    assert fact.alt == dt.date(2025, 2, 3)


def test_russian_numeric_date_is_never_ambiguous():
    (fact,) = dates("действует с 02.03.2025", "ru")
    assert fact.value == dt.date(2025, 3, 2) and fact.alt is None


def test_impossible_date_is_not_a_date():
    assert dates("код 45.67.2025", "ru") == []


def test_match_dates_reports_real_difference():
    a = [DateFact("12 March 2025", dt.date(2025, 3, 12))]
    b = [DateFact("21 марта 2025", dt.date(2025, 3, 21))]
    ambiguous, only_a, only_b = match_dates(a, b)
    assert ambiguous == [] and only_a == a and only_b == b


def test_match_dates_flags_agreement_only_under_other_reading():
    a = dates("effective 02/03/2025", "en")
    b = dates("действует с 3 февраля 2025 г.", "ru")
    ambiguous, only_a, only_b = match_dates(a, b)
    assert len(ambiguous) == 1 and only_a == [] and only_b == []


def test_match_dates_clean():
    a = dates("effective 12 March 2025", "en")
    b = dates("действует с 12.03.2025", "ru")
    assert match_dates(a, b) == ([], [], [])
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/facts/test_dates.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.facts.dates'`

- [ ] **Step 3: Create `src/bilingual_lint/wordlists/neutral.yaml`**

````yaml
# Language-neutral data: used for every language pair.
# All list entries are regular-expression fragments, matched case-insensitively.
iso_codes: [USD, EUR, GBP, RUB, CHF, CNY, JPY, AED, KZT, AMD, BYN, UAH, TRY, INR, HKD, SGD, CAD, AUD]
symbols:
  "US$": USD
  "$": USD
  "€": EUR
  "£": GBP
  "₽": RUB
  "¥": JPY
percent: ["%"]
````

- [ ] **Step 4: Create `src/bilingual_lint/wordlists/en.yaml`**

````yaml
# English wordlists. List entries are regular-expression fragments,
# matched case-insensitively. Keep longer alternatives before shorter ones.
currencies:
  USD: ['United\s+States\s+dollars?', 'U\.S\.\s?dollars?', 'US\s?dollars?', 'dollars?']
  EUR: ['euros?']
  GBP: ['pounds?\s+sterling', 'pounds?']
  RUB: ['Russian\s+roubles?', 'Russian\s+rubles?', 'roubles?', 'rubles?']
  CHF: ['Swiss\s+francs?']
  CNY: ['renminbi', 'yuan']
percent: ['per\s?cent', 'percent']
duration_units:
  day: ['days?']
  week: ['weeks?']
  month: ['months?']
  year: ['years?']
  hour: ['hours?']
day_types:
  business: ['business', 'working']
  banking: ['banking', 'bank']
  calendar: ['calendar']
months:
  january: 1
  jan: 1
  february: 2
  feb: 2
  march: 3
  mar: 3
  april: 4
  apr: 4
  may: 5
  june: 6
  jun: 6
  july: 7
  jul: 7
  august: 8
  aug: 8
  september: 9
  sept: 9
  sep: 9
  october: 10
  oct: 10
  november: 11
  nov: 11
  december: 12
  dec: 12
ref_keywords: ['sub-?clauses?', 'clauses?', 'sections?', 'articles?', 'paragraphs?', 'items?']
number_words:
  values:
    zero: 0
    one: 1
    two: 2
    three: 3
    four: 4
    five: 5
    six: 6
    seven: 7
    eight: 8
    nine: 9
    ten: 10
    eleven: 11
    twelve: 12
    thirteen: 13
    fourteen: 14
    fifteen: 15
    sixteen: 16
    seventeen: 17
    eighteen: 18
    nineteen: 19
    twenty: 20
    thirty: 30
    forty: 40
    fifty: 50
    sixty: 60
    seventy: 70
    eighty: 80
    ninety: 90
  hundred: [hundred]
  multipliers:
    thousand: 1000
    million: 1000000
    billion: 1000000000
  fillers: [and]
modality:
  obligation: ['shall', 'must', 'is\s+obliged\s+to', 'are\s+obliged\s+to', 'undertakes?', 'is\s+required\s+to']
  permission: ['may', 'is\s+entitled\s+to', 'are\s+entitled\s+to', 'has\s+the\s+right', 'have\s+the\s+right']
  # "No. 15" is a number sign, not a negation
  negation: ['not', 'no(?!\.\s?\d)', 'never', 'neither', 'nor', 'cannot', 'without']
prevailing:
  cues: ['prevail\w*', 'take\s+precedence', 'takes\s+precedence', 'controlling', 'shall\s+govern', 'shall\s+control']
  equal: ['equal\s+legal\s+force', 'equally\s+authentic', 'equal\s+force', 'equally\s+binding']
  languages:
    en: ['English']
    ru: ['Russian']
definitions:
  inline: '\((?:[^()"“”]{0,60})["“]([^"“”]{2,60})["”]\)'
  leading: '^\s*["“]([^"“”]{2,60})["”]\s+(?:means|shall\s+mean|has\s+the\s+meaning)'
````

- [ ] **Step 5: Create `src/bilingual_lint/wordlists/ru.yaml`**

````yaml
# Russian wordlists. List entries are regular-expression fragments,
# matched case-insensitively. Text and entries are compared with "ё" folded to "е"
# only for number words; other patterns list both spellings where needed.
currencies:
  USD: ['долл(?:ар\w*|\.)(?:\s*США)?']
  EUR: ['евро']
  GBP: ['фунт\w*(?:\s+стерлингов)?']
  RUB: ['(?:российск\w+\s+)?руб(?:л\w+|\.)?']
  CHF: ['швейцарск\w+\s+франк\w*']
  CNY: ['юан\w+']
percent: ['процент\w*']
duration_units:
  day: ['дневн\w+', 'дн(?:я|ей|ю|ями|ях)', 'день', 'сут\w+']
  week: ['недел\w+']
  month: ['месяц\w*']
  year: ['год(?:а|у|ом|ы|ов)?', 'лет']
  hour: ['час(?:а|ов|у)?']
day_types:
  business: ['рабоч\w+']
  banking: ['банковск\w+']
  calendar: ['календарн\w+']
months:
  января: 1
  январь: 1
  февраля: 2
  февраль: 2
  марта: 3
  март: 3
  апреля: 4
  апрель: 4
  мая: 5
  май: 5
  июня: 6
  июнь: 6
  июля: 7
  июль: 7
  августа: 8
  август: 8
  сентября: 9
  сентябрь: 9
  октября: 10
  октябрь: 10
  ноября: 11
  ноябрь: 11
  декабря: 12
  декабрь: 12
ref_keywords: ['подпункт\w*', 'пункт\w*', 'п\.\s?п\.', 'пп\.', 'п\.', 'стать\w+', 'ст\.', 'раздел\w*']
number_words:
  values:
    ноль: 0
    один: 1
    одна: 1
    одно: 1
    одного: 1
    одной: 1
    два: 2
    две: 2
    двух: 2
    три: 3
    трех: 3
    четыре: 4
    четырех: 4
    пять: 5
    пяти: 5
    шесть: 6
    шести: 6
    семь: 7
    семи: 7
    восемь: 8
    восьми: 8
    девять: 9
    девяти: 9
    десять: 10
    десяти: 10
    одиннадцать: 11
    одиннадцати: 11
    двенадцать: 12
    двенадцати: 12
    тринадцать: 13
    тринадцати: 13
    четырнадцать: 14
    четырнадцати: 14
    пятнадцать: 15
    пятнадцати: 15
    шестнадцать: 16
    шестнадцати: 16
    семнадцать: 17
    семнадцати: 17
    восемнадцать: 18
    восемнадцати: 18
    девятнадцать: 19
    девятнадцати: 19
    двадцать: 20
    двадцати: 20
    тридцать: 30
    тридцати: 30
    сорок: 40
    сорока: 40
    пятьдесят: 50
    пятидесяти: 50
    шестьдесят: 60
    шестидесяти: 60
    семьдесят: 70
    семидесяти: 70
    восемьдесят: 80
    восьмидесяти: 80
    девяносто: 90
    девяноста: 90
    сто: 100
    ста: 100
    двести: 200
    двухсот: 200
    триста: 300
    трехсот: 300
    четыреста: 400
    четырехсот: 400
    пятьсот: 500
    пятисот: 500
    шестьсот: 600
    шестисот: 600
    семьсот: 700
    семисот: 700
    восемьсот: 800
    восьмисот: 800
    девятьсот: 900
    девятисот: 900
  hundred: []
  multipliers:
    тысяча: 1000
    тысячи: 1000
    тысяч: 1000
    тысячу: 1000
    миллион: 1000000
    миллиона: 1000000
    миллионов: 1000000
    миллиард: 1000000000
    миллиарда: 1000000000
    миллиардов: 1000000000
  fillers: []
modality:
  obligation: ['обязан\w*', 'обязу\w+', 'должн\w+', 'надлежит']
  permission: ['вправе', 'мо(?:жет|гут)', 'име(?:ет|ют)\s+право']
  negation: ['не', 'ни', 'нет', 'без', 'запрещ\w+']
prevailing:
  cues: ['преимуществ\w+', 'приоритет\w*', 'преобладающ\w+', 'превалир\w+']
  equal: ['равн\w+\s+юридическ\w+\s+сил\w+', 'одинаков\w+\s+юридическ\w+\s+сил\w+', 'равн\w+\s+сил\w+']
  languages:
    en: ['английск\w+']
    ru: ['русск\w+']
definitions:
  inline: '\((?:[^()«»"“”]{0,60})[«"“]([^«»"“”]{2,60})[»"”]\)'
  leading: '^\s*[«"“]([^«»"“”]{2,60})[»"”]\s+(?:означает|значит|имеет\s+значение)'
````

- [ ] **Step 6: Create `src/bilingual_lint/wordlists/__init__.py`**

````python
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
````

- [ ] **Step 7: Create `src/bilingual_lint/facts/dates.py`**

````python
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
````

- [ ] **Step 8: Run the test**

Run: `$PY -m pytest tests/facts/test_dates.py -q`
Expected: `16 passed`

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: wordlists for en and ru, date parsing"
```

---

### Task 4: Numbers in words

**Files:**
- Create: `src/bilingual_lint/facts/words.py`
- Test: `tests/facts/test_words.py`

- [ ] **Step 1: Write the failing test** `tests/facts/test_words.py`

````python
from decimal import Decimal as D

import pytest

from bilingual_lint.facts.words import parse_number_words, word_digit_mismatches, word_values
from bilingual_lint.wordlists import load_wordlists

EN = load_wordlists("en").number_words
RU = load_wordlists("ru").number_words


@pytest.mark.parametrize("words, nw, value", [
    (["ten"], EN, 10),
    (["twenty", "five"], EN, 25),
    (["two", "hundred", "and", "five"], EN, 205),
    (["one", "hundred", "fifty", "thousand"], EN, 150000),
    (["one", "million", "two", "hundred", "thousand"], EN, 1200000),
    (["сто", "тысяч"], RU, 100000),
    (["одна", "тысяча", "пятьсот"], RU, 1500),
    (["тридцати"], RU, 30),
    (["двух", "миллионов", "трехсот", "тысяч"], RU, 2300000),
    (["ten", "apples"], EN, None),
    (["and"], EN, None),
])
def test_parse_number_words(words, nw, value):
    assert parse_number_words(words, nw) == value


def test_word_values_finds_every_spelled_number():
    assert word_values("in two copies, one for each party", EN) == {D(2), D(1)}
    assert word_values("в двух экземплярах", RU) == {D(2)}
    assert word_values("twenty-five days", EN) == {D(25)}
    assert word_values("no numbers here", EN) == set()


def test_separate_numbers_are_not_added_together():
    assert word_values("one, two", EN) == {D(1), D(2)}


@pytest.mark.parametrize("text, lang, nw", [
    ("within ten (10) business days", "en", EN),
    ("the amount of 150,000 (one hundred and fifty thousand) US dollars", "en", EN),
    ("в размере 100 000 (сто тысяч) рублей", "ru", RU),
    ("в течение 10 (десяти) рабочих дней", "ru", RU),
    ("в размере 1 500 (одна тысяча пятьсот рублей)", "ru", RU),
    ("Buyer 1 (the Company) shall pay", "en", EN),
    ("see clause 5 (Payment)", "en", EN),
])
def test_consistent_or_unrelated_brackets_are_clean(text, lang, nw):
    assert word_digit_mismatches(text, lang, nw) == []


@pytest.mark.parametrize("text, lang, nw, expected", [
    ("within ten (15) business days", "en", EN, [("15", "ten")]),
    ("the amount of 150,000 (one hundred and five thousand) US dollars", "en", EN,
     [("150,000", "one hundred and five thousand")]),
    ("в размере 100 000 (сто пятьдесят тысяч) рублей", "ru", RU,
     [("100 000", "сто пятьдесят тысяч")]),
    ("в течение 10 (пяти) рабочих дней", "ru", RU, [("10", "пяти")]),
])
def test_digits_and_words_that_disagree(text, lang, nw, expected):
    assert word_digit_mismatches(text, lang, nw) == expected


def test_no_wordlist_means_no_claim():
    assert word_values("ten", None) == set()
    assert word_digit_mismatches("ten (15)", "xx", None) == []
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/facts/test_words.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.facts.words'`

- [ ] **Step 3: Create `src/bilingual_lint/facts/words.py`**

````python
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
````

- [ ] **Step 4: Run the test**

Run: `$PY -m pytest tests/facts/test_words.py -q`
Expected: `25 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: numbers in words and digit-word consistency"
```

---

### Task 5: Fact extraction

One function turns a segment into `Facts`. Order matters: each step blanks out what it consumed, so an e-mail's digits never become "numbers" and a date's year never becomes a duration.

**Files:**
- Create: `src/bilingual_lint/facts/extract.py`
- Test: `tests/facts/test_extract.py`

- [ ] **Step 1: Write the failing test** `tests/facts/test_extract.py`

````python
import datetime as dt
from decimal import Decimal as D

from bilingual_lint.facts.extract import extract_facts


def kinds(facts):
    return [(x.kind, x.primary, x.unit, x.day_type) for x in facts.quantities]


def test_money_in_both_languages():
    en = extract_facts("The price is USD 150,000.00 payable at once.", "en")
    ru = extract_facts("Цена составляет 150 000,00 (сто пятьдесят тысяч) долларов США.", "ru")
    assert kinds(en) == [("money", D(150000), "USD", "")]
    assert kinds(ru) == [("money", D(150000), "USD", "")]


def test_currency_words_and_symbols():
    assert kinds(extract_facts("pays 500 euros", "en")) == [("money", D(500), "EUR", "")]
    assert kinds(extract_facts("pays €500", "en")) == [("money", D(500), "EUR", "")]
    assert kinds(extract_facts("оплата 500 руб.", "ru")) == [("money", D(500), "RUB", "")]
    assert kinds(extract_facts("оплата 500 рублей", "ru")) == [("money", D(500), "RUB", "")]
    assert kinds(extract_facts("pays 500 RUB", "en")) == [("money", D(500), "RUB", "")]


def test_percent():
    assert kinds(extract_facts("a penalty of 0.1% per day", "en")) == [
        ("percent", D("0.1"), "", "")]
    assert kinds(extract_facts("пеня 0,1 процента в день", "ru")) == [
        ("percent", D("0.1"), "", "")]
    assert kinds(extract_facts("ten (10) per cent", "en")) == [("percent", D(10), "", "")]


def test_durations_with_day_type():
    assert kinds(extract_facts("within 30 business days", "en")) == [
        ("duration", D(30), "day", "business")]
    assert kinds(extract_facts("within thirty (30) calendar days", "en")) == [
        ("duration", D(30), "day", "calendar")]
    assert kinds(extract_facts("в течение 30 (тридцати) рабочих дней", "ru")) == [
        ("duration", D(30), "day", "business")]
    assert kinds(extract_facts("в течение 30 дней", "ru")) == [
        ("duration", D(30), "day", "")]
    assert kinds(extract_facts("a 30-day period", "en")) == [("duration", D(30), "day", "")]
    assert kinds(extract_facts("сроком на 3 года", "ru")) == [("duration", D(3), "year", "")]


def test_leading_number_and_cross_references():
    en = extract_facts("5.2. Subject to clauses 3.1 and 3.4, the Buyer pays 10 units.", "en")
    assert en.leading_number == "5.2"
    assert en.refs == ["3.1", "3.4"]
    assert kinds(en) == [("number", D(10), "", "")]
    ru = extract_facts("5.2. С учётом пп. 3.1 и 3.4 Покупатель оплачивает 10 единиц.", "ru")
    assert ru.leading_number == "5.2"
    assert ru.refs == ["3.1", "3.4"]
    assert kinds(ru) == [("number", D(10), "", "")]


def test_plain_amount_at_start_is_not_a_clause_number():
    facts = extract_facts("100 000 рублей уплачиваются сразу.", "ru")
    assert facts.leading_number is None
    assert kinds(facts) == [("money", D(100000), "RUB", "")]


def test_dates_are_not_numbers():
    facts = extract_facts("Signed on 12 March 2025 for 5 years.", "en")
    assert [d.value for d in facts.dates] == [dt.date(2025, 3, 12)]
    assert kinds(facts) == [("duration", D(5), "year", "")]


def test_identifiers_are_not_numbers():
    facts = extract_facts(
        "INN 7701234567, IBAN DE89 3704 0044 0532 0130 00, write to Info@Example.com "
        "or see https://example.com/terms.", "en")
    assert facts.identifiers == [
        "info@example.com", "https://example.com/terms",
        "DE89370400440532013000", "7701234567"]
    assert facts.quantities == []


def test_word_values_and_mismatches_are_attached():
    facts = extract_facts("in two copies within ten (15) days", "en")
    assert D(2) in facts.word_values
    assert facts.word_digit_mismatches == [("15", "ten")]


def test_unknown_language_still_gets_neutral_facts():
    facts = extract_facts("Preis 1.000,00 EUR, 5 % Rabatt, 2025-03-12", "de")
    assert kinds(facts) == [("money", D(1000), "EUR", ""), ("percent", D(5), "", "")]
    assert [d.value for d in facts.dates] == [dt.date(2025, 3, 12)]
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/facts/test_extract.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.facts.extract'`

- [ ] **Step 3: Create `src/bilingual_lint/facts/extract.py`**

````python
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
````

- [ ] **Step 4: Run the test, then the whole suite**

Run: `$PY -m pytest -q`
Expected: `78 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: fact extraction with masking between steps"
```

---

### Task 6: Pairing two files

Deterministic, in two passes. Anchors first: paragraphs whose clause number or digit set is unique on both sides. Then length-based dynamic programming between anchors, allowing a paragraph to be missing (1-0, 0-1) or split in two (2-1, 1-2).

**Files:**
- Create: `src/bilingual_lint/pairing.py`
- Test: `tests/test_pairing.py`

- [ ] **Step 1: Write the failing test** `tests/test_pairing.py`

````python
from bilingual_lint.models import Segment
from bilingual_lint.pairing import find_anchors, pair_segments


def segs(lang, texts):
    return [Segment(t, lang, i, f"paragraph {i + 1}") for i, t in enumerate(texts)]


EN = [
    "1. Subject",
    "The Seller shall deliver the goods to the Buyer within the agreed time.",
    "2. Price",
    "The price of the goods is 150,000 US dollars, payable within 30 days.",
    "3. Liability",
    "Each party is liable for its own breach of this agreement.",
]
RU = [
    "1. Предмет",
    "Продавец обязуется поставить товар Покупателю в согласованный срок.",
    "2. Цена",
    "Цена товара составляет 150 000 долларов США и уплачивается в течение 30 дней.",
    "3. Ответственность",
    "Каждая сторона отвечает за собственное нарушение настоящего договора.",
]


def shape(pairs):
    return [(p.a.index if p.a else None, p.b.index if p.b else None) for p in pairs]


def test_identical_structure_pairs_one_to_one():
    pairs = pair_segments(segs("en", EN), segs("ru", RU))
    assert shape(pairs) == [(i, i) for i in range(6)]
    assert [p.pair_no for p in pairs] == [1, 2, 3, 4, 5, 6]
    assert all(p.confidence >= 0.5 for p in pairs)


def test_anchors_use_clause_numbers_and_digit_signatures():
    anchors = find_anchors(segs("en", EN), segs("ru", RU))
    assert anchors == [(0, 0), (2, 2), (3, 3), (4, 4)]


def test_missing_paragraph_becomes_an_unpaired_segment():
    extra = "This additional sentence exists only in the English version of the text."
    en = EN[:2] + [extra] + EN[2:]
    pairs = pair_segments(segs("en", en), segs("ru", RU))
    assert shape(pairs) == [(0, 0), (1, 1), (2, None), (3, 2), (4, 3), (5, 4), (6, 5)]


def test_paragraph_split_in_two_is_merged():
    first = "The Seller shall deliver the goods to the Buyer"
    second = "within the agreed time and at the agreed place."
    en = [EN[0], first, second] + EN[2:]
    ru = list(RU)
    ru[1] = "Продавец обязуется поставить товар Покупателю в согласованный срок и в месте."
    pairs = pair_segments(segs("en", en), segs("ru", ru))
    assert shape(pairs)[:3] == [(0, 0), (1, 1), (3, 2)]
    assert pairs[1].a.text == first + " " + second
    assert pairs[1].a.location == "paragraph 2–paragraph 3"


def test_no_anchors_still_aligns_by_length():
    en = ["Short title", "A considerably longer paragraph of contract text goes here."]
    ru = ["Заголовок", "Здесь находится значительно более длинный абзац текста договора."]
    assert shape(pair_segments(segs("en", en), segs("ru", ru))) == [(0, 0), (1, 1)]


def test_empty_side_returns_everything_unpaired():
    pairs = pair_segments(segs("en", EN[:2]), [])
    assert shape(pairs) == [(0, None), (1, None)]
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/test_pairing.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.pairing'`

- [ ] **Step 3: Create `src/bilingual_lint/pairing.py`**

````python
"""Pair the paragraphs of two separate files, deterministically.

Pass 1 pins the texts together at anchors: paragraphs whose clause number or
set of digits is unique on both sides. Pass 2 aligns what lies between two
anchors by length, allowing a paragraph to be missing or split in two."""
from __future__ import annotations

import math
import re
from collections import Counter

from .models import Pair, Segment

LEADING_RE = re.compile(r"^\s*((?:\d{1,3}\.)+\d{0,3}|\d{1,3}[.)])(?=\s)")
SKIP_COST = 1.0    # a paragraph with no partner
MERGE_COST = 0.5   # two paragraphs facing one
DIGIT_COST = 0.4   # the two sides do not carry the same digits
MIN_ANCHOR_CHARS = 50
MOVES = ((1, 1), (1, 0), (0, 1), (2, 1), (1, 2))


def _leading(text: str) -> str | None:
    m = LEADING_RE.match(text)
    return m.group(1).rstrip(".)") if m else None


def _signature(text: str) -> tuple | None:
    digits = re.findall(r"\d+", text)
    return tuple(digits) if len("".join(digits)) >= 4 else None


def _unique_matches(keys_a: list, keys_b: list) -> dict:
    count_a = Counter(k for k in keys_a if k)
    count_b = Counter(k for k in keys_b if k)
    position_b = {k: j for j, k in enumerate(keys_b) if k and count_b[k] == 1}
    return {i: position_b[k] for i, k in enumerate(keys_a)
            if k and count_a[k] == 1 and k in position_b}


def find_anchors(a: list, b: list) -> list:
    """Return [(i, j)] strictly increasing in both i and j."""
    texts_a = [s.text for s in a]
    texts_b = [s.text for s in b]
    by_signature = _unique_matches([_signature(t) for t in texts_a],
                                   [_signature(t) for t in texts_b])
    by_leading = _unique_matches([_leading(t) for t in texts_a],
                                 [_leading(t) for t in texts_b])
    merged = {**by_signature, **by_leading}  # a clause number wins a conflict
    used = Counter(merged.values())
    candidates = sorted((i, j) for i, j in merged.items() if used[j] == 1)
    # longest chain that also increases in j
    best = [1] * len(candidates)
    previous = [-1] * len(candidates)
    for x in range(len(candidates)):
        for y in range(x):
            if candidates[y][1] < candidates[x][1] and best[y] + 1 > best[x]:
                best[x], previous[x] = best[y] + 1, y
    if not candidates:
        return []
    x = max(range(len(candidates)), key=best.__getitem__)
    chain = []
    while x != -1:
        chain.append(candidates[x])
        x = previous[x]
    return chain[::-1]


def _digits(segments: list) -> Counter:
    return Counter(d for s in segments for d in re.findall(r"\d+", s.text))


def _length_cost(len_a: int, len_b: int, ratio: float) -> float:
    return abs(math.log((len_b + 5) / (len_a * ratio + 5)))


def _join(segments: list) -> Segment:
    if len(segments) == 1:
        return segments[0]
    return Segment(" ".join(s.text for s in segments), segments[0].lang,
                   segments[0].index,
                   f"{segments[0].location}–{segments[-1].location}")


def _align_block(a: list, b: list, ratio: float) -> list:
    """Length-based alignment. Returns [(Segment|None, Segment|None, confidence)]."""
    n, m = len(a), len(b)
    inf = float("inf")
    cost = [[inf] * (m + 1) for _ in range(n + 1)]
    back: list = [[None] * (m + 1) for _ in range(n + 1)]
    cost[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if cost[i][j] == inf:
                continue
            for da, db in MOVES:
                if i + da > n or j + db > m:
                    continue
                if da == 0 or db == 0:
                    step = SKIP_COST
                else:
                    step = _length_cost(sum(len(s.text) for s in a[i:i + da]),
                                        sum(len(s.text) for s in b[j:j + db]), ratio)
                    if da + db > 2:
                        step += MERGE_COST
                    if _digits(a[i:i + da]) != _digits(b[j:j + db]):
                        step += DIGIT_COST
                if cost[i][j] + step < cost[i + da][j + db]:
                    cost[i + da][j + db] = cost[i][j] + step
                    back[i + da][j + db] = (da, db)
    rows: list = []
    i, j = n, m
    while (i, j) != (0, 0):
        da, db = back[i][j]
        seg_a = _join(a[i - da:i]) if da else None
        seg_b = _join(b[j - db:j]) if db else None
        if seg_a and seg_b:
            confidence = math.exp(-_length_cost(len(seg_a.text), len(seg_b.text), ratio))
            if da + db > 2:
                confidence *= 0.8
        else:
            confidence = 1.0
        rows.append((seg_a, seg_b, round(confidence, 3)))
        i, j = i - da, j - db
    return rows[::-1]


def pair_segments(a: list, b: list) -> list:
    """Pair two ordered lists of Segments. Nothing is dropped: a segment with
    no partner comes back in a Pair whose other side is None."""
    anchors = find_anchors(a, b)
    # Expected length ratio b/a. Anchored paragraphs are known to correspond,
    # so they give a cleaner estimate than whole-file totals, which a missing
    # paragraph would distort.
    total_a = sum(len(a[i].text) for i, _ in anchors)
    total_b = sum(len(b[j].text) for _, j in anchors)
    if total_a < MIN_ANCHOR_CHARS:
        total_a = sum(len(s.text) for s in a)
        total_b = sum(len(s.text) for s in b)
    ratio = (total_b / total_a) if total_a and total_b else 1.0
    rows: list = []
    i0 = j0 = 0
    for i, j in anchors + [(len(a), len(b))]:
        rows.extend(_align_block(a[i0:i], b[j0:j], ratio))
        if i < len(a):
            rows.append((a[i], b[j], 1.0))
        i0, j0 = i + 1, j + 1
    return [Pair(pair_no=n, a=seg_a, b=seg_b, confidence=confidence)
            for n, (seg_a, seg_b, confidence) in enumerate(rows, start=1)]
````

- [ ] **Step 4: Run the test**

Run: `$PY -m pytest tests/test_pairing.py -q`
Expected: `6 passed`

- [ ] **Step 5: Prove the guard.** Change `SKIP_COST = 1.0` to `SKIP_COST = 3.0` and run again.

Expected: `test_missing_paragraph_becomes_an_unpaired_segment` fails, because a missing paragraph is now merged into its neighbour instead of being reported. Restore `1.0`; expected `6 passed`.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: deterministic paragraph pairing"
```

---

### Task 7: Reading DOCX files

`docx_reader` walks the XML itself so that tracked insertions are included and tracked deletions are not, which is what "read as if all changes were accepted" means. Table cells are read from the raw rows, so a merged cell is not repeated.

**Files:**
- Create: `src/bilingual_lint/loaders/docx_reader.py`, `two_column.py`, `two_files.py`, `__init__.py`, `tests/helpers.py`
- Test: `tests/test_loaders.py`

- [ ] **Step 1: Create `tests/helpers.py`** (extended in Task 10)

````python
"""Shared test helpers: build DOCX files on disk."""
from __future__ import annotations

from pathlib import Path

from docx import Document as new_docx


def write_two_column(path: Path, rows, intro: str | None = None) -> Path:
    document = new_docx()
    if intro:
        document.add_paragraph(intro)
    table = document.add_table(rows=0, cols=2)
    for a, b in rows:
        cells = table.add_row().cells
        cells[0].text = a
        cells[1].text = b
    document.save(str(path))
    return path


def write_plain(path: Path, paragraphs) -> Path:
    document = new_docx()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(str(path))
    return path
````

- [ ] **Step 2: Write the failing test** `tests/test_loaders.py`

````python
import copy

import pytest
from docx import Document as new_docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from bilingual_lint.loaders import LoaderError, load
from bilingual_lint.loaders.docx_reader import read_docx
from bilingual_lint.loaders.two_column import pick_columns

from .helpers import write_plain, write_two_column

ROWS = [
    ("1. Subject", "1. Предмет"),
    ("The Seller shall deliver the goods.", "Продавец обязуется поставить товар."),
]


def _run(text: str):
    run = OxmlElement("w:r")
    node = OxmlElement("w:t")
    node.text = text
    run.append(node)
    return run


def _tracked(paragraph, tag: str, text: str) -> None:
    """Append a tracked insertion (w:ins) or deletion (w:del) to a paragraph."""
    wrapper = OxmlElement(tag)
    wrapper.set(qn("w:id"), "1")
    wrapper.set(qn("w:author"), "Reviewer")
    run = _run(text)
    if tag == "w:del":
        run[0].tag = qn("w:delText")
    wrapper.append(run)
    paragraph._p.append(wrapper)


# --- docx_reader -----------------------------------------------------------

def test_blocks_come_back_in_document_order(tmp_path):
    path = write_two_column(tmp_path / "a.docx", ROWS, intro="SUPPLY AGREEMENT")
    blocks, notes = read_docx(path)
    assert [b.kind for b in blocks] == ["paragraph", "table"]
    assert blocks[0].text == "SUPPLY AGREEMENT" and blocks[0].location == "paragraph 1"
    assert blocks[1].rows == [{0: a, 1: b} for a, b in ROWS]
    assert notes == []


def test_tracked_changes_are_read_as_accepted(tmp_path):
    document = new_docx()
    paragraph = document.add_paragraph("The price is ")
    _tracked(paragraph, "w:del", "100")
    _tracked(paragraph, "w:ins", "200")
    paragraph._p.append(_run(" dollars."))
    path = tmp_path / "tracked.docx"
    document.save(str(path))
    blocks, notes = read_docx(path)
    assert blocks[0].text == "The price is 200 dollars."
    assert len(notes) == 1 and "tracked changes" in notes[0]


def test_merged_cell_keeps_its_grid_column(tmp_path):
    document = new_docx()
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "Heading across both columns"
    table.cell(1, 0).text, table.cell(1, 1).text = "Left", "Правый"
    path = tmp_path / "merged.docx"
    document.save(str(path))
    blocks, _ = read_docx(path)
    assert blocks[0].rows == [{0: "Heading across both columns"}, {0: "Left", 1: "Правый"}]


def test_multi_paragraph_cell_keeps_line_breaks(tmp_path):
    document = new_docx()
    cell = document.add_table(rows=1, cols=2).cell(0, 0)
    cell.text = "First line"
    cell.add_paragraph("Second line")
    path = tmp_path / "lines.docx"
    document.save(str(path))
    blocks, _ = read_docx(path)
    assert blocks[0].rows[0][0] == "First line\nSecond line"


@pytest.mark.parametrize("content, fragment", [
    (bytes.fromhex("d0cf11e0a1b11ae1") + b"x" * 64, "password-protected"),
    (b"just some text", "not a DOCX"),
    (b"PK\x03\x04 broken zip", "cannot read"),
])
def test_unreadable_files_are_refused_with_a_reason(tmp_path, content, fragment):
    path = tmp_path / "bad.docx"
    path.write_bytes(content)
    with pytest.raises(LoaderError, match=fragment):
        read_docx(path)


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(LoaderError, match="file not found"):
        read_docx(tmp_path / "nope.docx")


# --- two-column ------------------------------------------------------------

def test_pick_columns_by_script():
    rows = [{0: "1.", 1: "The Seller delivers", 2: "Продавец поставляет"}]
    assert pick_columns(rows, None) == (1, 2, "en", "ru")
    flipped = [{0: "Продавец поставляет", 1: "The Seller delivers"}]
    assert pick_columns(flipped, None) == (0, 1, "ru", "en")


def test_pick_columns_same_script_needs_langs():
    rows = [{0: "The Seller delivers", 1: "El Vendedor entrega"}]
    assert pick_columns(rows, None) is None
    assert pick_columns(rows, ("en", "es")) == (0, 1, "en", "es")


def test_pick_columns_rejects_single_language_table():
    assert pick_columns([{0: "Item", 1: "Price"}], None) is None


def test_two_column_document(tmp_path):
    path = write_two_column(tmp_path / "c.docx", ROWS, intro="Title outside the table")
    doc = load([path])
    assert (doc.lang_a, doc.lang_b, doc.mode) == ("en", "ru", "two-column")
    assert [(p.a.text, p.b.text) for p in doc.pairs] == ROWS
    assert doc.pairs[1].a.location == "table 1, row 2"
    assert [n.rule_id for n in doc.notes] == ["BI000"]
    assert "1 block(s) of text outside" in doc.notes[0].message


def test_empty_cell_is_kept_as_a_pair(tmp_path):
    path = write_two_column(tmp_path / "e.docx", ROWS + [("3. Signatures", "")])
    doc = load([path])
    assert doc.pairs[2].a.text == "3. Signatures" and doc.pairs[2].b.text == ""
    assert not doc.pairs[2].complete


def test_file_without_bilingual_table_is_refused(tmp_path):
    path = write_plain(tmp_path / "p.docx", ["Only English text here."])
    with pytest.raises(LoaderError, match="no two-language table"):
        load([path])


# --- two files -------------------------------------------------------------

def test_two_files_are_paired(tmp_path):
    en = write_plain(tmp_path / "en.docx", [a for a, _ in ROWS])
    ru = write_plain(tmp_path / "ru.docx", [b for _, b in ROWS])
    doc = load([en, ru])
    assert (doc.lang_a, doc.lang_b, doc.mode) == ("en", "ru", "two-files")
    assert [(p.a.text, p.b.text) for p in doc.pairs] == ROWS


def test_two_files_same_script_need_langs(tmp_path):
    en = write_plain(tmp_path / "en.docx", ["The Seller delivers the goods."])
    es = write_plain(tmp_path / "es.docx", ["El Vendedor entrega los bienes."])
    with pytest.raises(LoaderError, match="--langs"):
        load([en, es])
    doc = load([en, es], ("en", "es"))
    assert (doc.lang_a, doc.lang_b) == ("en", "es")


def test_langs_given_in_the_wrong_order_follow_the_script(tmp_path):
    en = write_plain(tmp_path / "en.docx", ["The Seller delivers the goods."])
    ru = write_plain(tmp_path / "ru.docx", ["Продавец поставляет товар."])
    doc = load([en, ru], ("ru", "en"))
    assert (doc.lang_a, doc.lang_b) == ("en", "ru")


def test_empty_file_is_refused(tmp_path):
    en = write_plain(tmp_path / "en.docx", ["Some text."])
    empty = write_plain(tmp_path / "empty.docx", [])
    with pytest.raises(LoaderError, match="contains no text"):
        load([en, empty])


def test_three_paths_are_refused(tmp_path):
    with pytest.raises(LoaderError, match="one bilingual DOCX"):
        load([tmp_path / "a", tmp_path / "b", tmp_path / "c"])


def test_helpers_do_not_share_state():
    assert copy.deepcopy(ROWS) == ROWS
````

- [ ] **Step 3: Run it and watch it fail**

Run: `$PY -m pytest tests/test_loaders.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.loaders'`

- [ ] **Step 4: Create `src/bilingual_lint/loaders/docx_reader.py`**

````python
"""Read a DOCX into ordered blocks of text, as if tracked changes were accepted."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from docx import Document as open_docx
from docx.oxml.ns import qn
from docx.table import Table

from ..text_utils import clean

OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
# Deleted and moved-away text is not part of the accepted document.
SKIPPED = {qn("w:del"), qn("w:moveFrom"), MC_FALLBACK}
TRACKED = [qn("w:ins"), qn("w:del"), qn("w:moveFrom"), qn("w:moveTo")]
COMMENTED = [qn("w:commentRangeStart"), qn("w:commentReference")]
TEXT, TAB, HYPHEN = qn("w:t"), qn("w:tab"), qn("w:noBreakHyphen")
BREAKS = {qn("w:br"), qn("w:cr")}
PARAGRAPH = qn("w:p")


class LoaderError(Exception):
    pass


@dataclass
class Block:
    kind: str  # "paragraph" | "table"
    location: str
    text: str = ""
    rows: list = field(default_factory=list)  # table: one {grid column: text} per row


def element_text(element) -> str:
    out: list = []

    def walk(node) -> None:
        for child in node:
            tag = child.tag
            if tag in SKIPPED:
                continue
            if tag == TEXT:
                out.append(child.text or "")
            elif tag == TAB:
                out.append("\t")
            elif tag in BREAKS:
                out.append("\n")
            elif tag == HYPHEN:
                out.append("-")
            else:
                walk(child)

    walk(element)
    return "".join(out)


def _cell_text(tc) -> str:
    parts = [clean(element_text(p)) for p in tc.iter(PARAGRAPH)]
    return "\n".join(part for part in parts if part)


def _table_rows(table: Table) -> list:
    rows = []
    for tr in table._tbl.tr_lst:
        row: dict = {}
        column = 0
        for tc in tr.tc_lst:
            row[column] = _cell_text(tc)
            column += tc.grid_span
        rows.append(row)
    return rows


def read_docx(path: Path) -> tuple[list, list]:
    """Return (blocks in document order, notes about the file)."""
    path = Path(path)
    if not path.is_file():
        raise LoaderError(f"file not found: {path}")
    head = path.read_bytes()[:8]
    if head == OLE_MAGIC:
        raise LoaderError(
            f"{path.name} is password-protected or an old .doc file; "
            "save it as an unprotected .docx first")
    if not head.startswith(b"PK"):
        raise LoaderError(f"{path.name} is not a DOCX file")
    try:
        document = open_docx(str(path))
    except Exception as exc:  # python-docx raises several unrelated types
        raise LoaderError(f"cannot read {path.name}: {exc}") from exc

    body = document.element.body
    notes = []
    if next(body.iter(*TRACKED), None) is not None:
        notes.append(f"{path.name} has tracked changes; "
                     "the text was read as if all changes were accepted")
    if next(body.iter(*COMMENTED), None) is not None:
        notes.append(f"{path.name} has comments; comments were not checked")

    blocks = []
    paragraphs = tables = 0
    for item in document.iter_inner_content():
        if isinstance(item, Table):
            tables += 1
            blocks.append(Block("table", f"table {tables}", rows=_table_rows(item)))
            continue
        text = clean(element_text(item._p))
        if text:
            paragraphs += 1
            blocks.append(Block("paragraph", f"paragraph {paragraphs}", text=text))
    return blocks, notes
````

- [ ] **Step 5: Create `src/bilingual_lint/loaders/two_column.py`**

````python
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
````

- [ ] **Step 6: Create `src/bilingual_lint/loaders/two_files.py`**

````python
"""Load a source file and its translation as two separate DOCX files."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..models import Document, Finding, Segment, Severity
from ..pairing import pair_segments
from ..text_utils import DEFAULT_LANG, letters, script_for_lang, script_of
from .docx_reader import LoaderError, read_docx


def _texts(blocks: list) -> list:
    """[(text, location)] for every paragraph and every non-empty table cell."""
    out = []
    for block in blocks:
        if block.kind == "paragraph":
            out.append((block.text, block.location))
            continue
        for number, row in enumerate(block.rows, start=1):
            for position, column in enumerate(sorted(row), start=1):
                if row[column].strip():
                    out.append((row[column],
                                f"{block.location}, row {number}, cell {position}"))
    return out


def _main_script(texts: list) -> str:
    weight: Counter = Counter()
    for text, _ in texts:
        weight[script_of(text)] += letters(text)
    weight.pop("none", None)
    return weight.most_common(1)[0][0] if weight else "none"


def load_two_files(path_a: Path, path_b: Path, langs: tuple | None = None) -> Document:
    blocks_a, notes_a = read_docx(path_a)
    blocks_b, notes_b = read_docx(path_b)
    texts_a, texts_b = _texts(blocks_a), _texts(blocks_b)
    for path, texts in ((path_a, texts_a), (path_b, texts_b)):
        if not texts:
            raise LoaderError(f"{Path(path).name} contains no text")
    script_a, script_b = _main_script(texts_a), _main_script(texts_b)
    if langs is None:
        if {script_a, script_b} != {"latin", "cyrillic"}:
            raise LoaderError(
                "cannot tell the two languages apart by script; pass --langs, "
                "for example --langs en,es (first file, second file)")
        lang_a, lang_b = DEFAULT_LANG[script_a], DEFAULT_LANG[script_b]
    else:
        lang_a, lang_b = langs
        swapped = (script_for_lang(lang_a) != script_for_lang(lang_b)
                   and script_a == script_for_lang(lang_b))
        if swapped:
            lang_a, lang_b = lang_b, lang_a
    segments_a = [Segment(text, lang_a, i, where) for i, (text, where) in enumerate(texts_a)]
    segments_b = [Segment(text, lang_b, i, where) for i, (text, where) in enumerate(texts_b)]
    findings = [Finding("BI000", Severity.INFO, note) for note in notes_a + notes_b]
    return Document(pair_segments(segments_a, segments_b), lang_a, lang_b, "two-files",
                    [Path(path_a), Path(path_b)], findings)
````

- [ ] **Step 7: Create `src/bilingual_lint/loaders/__init__.py`**

````python
from __future__ import annotations

from pathlib import Path

from ..models import Document
from .docx_reader import LoaderError
from .two_column import load_two_column
from .two_files import load_two_files


def load(paths: list, langs: tuple | None = None) -> Document:
    """One path: a two-column bilingual DOCX. Two paths: source and translation."""
    if len(paths) == 1:
        return load_two_column(Path(paths[0]), langs)
    if len(paths) == 2:
        return load_two_files(Path(paths[0]), Path(paths[1]), langs)
    raise LoaderError("pass one bilingual DOCX, or two DOCX files")


__all__ = ["LoaderError", "load", "load_two_column", "load_two_files"]
````

- [ ] **Step 8: Run the test**

Run: `$PY -m pytest tests/test_loaders.py -q`
Expected: `20 passed`

- [ ] **Step 9: Prove the guard.** In `read_docx`, replace `clean(element_text(item._p))` with `clean(item.text)`, which is python-docx's own text property. Run again.

Expected: `test_tracked_changes_are_read_as_accepted` fails, because the library's property does not return tracked insertions. Restore; expected `20 passed`.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: DOCX loaders for two-column and two-file input"
```

---

### Task 8: Refining pairs

**Files:**
- Create: `src/bilingual_lint/segment.py`
- Test: `tests/test_segment.py`

- [ ] **Step 1: Write the failing test** `tests/test_segment.py`

````python
from bilingual_lint.models import Document, Pair, Segment
from bilingual_lint.segment import refine, split_sentences


def doc_of(a: str, b: str) -> Document:
    pair = Pair(1, Segment(a, "en", 0, "row 1"), Segment(b, "ru", 0, "row 1"))
    return Document([pair], "en", "ru", "two-column", [])


def texts(doc):
    return [(p.a.text, p.b.text) for p in doc.pairs]


def test_split_sentences_basic():
    assert split_sentences("First one. Second one! Third?") == [
        "First one.", "Second one!", "Third?"]


def test_abbreviations_numbers_and_initials_do_not_split():
    for text in ("Agreement No. 15 of the parties", "5.1. The Seller delivers",
                 "см. п. 5 Договора", "signed by I. I. Ivanov today",
                 "в размере 100 руб. Покупателю"):
        assert split_sentences(text) == [text]


def test_equal_sentence_counts_are_split():
    doc = refine(doc_of("The price is 100. Payment is due in 5 days.",
                        "Цена составляет 100. Оплата производится в течение 5 дней."))
    assert texts(doc) == [
        ("The price is 100.", "Цена составляет 100."),
        ("Payment is due in 5 days.", "Оплата производится в течение 5 дней."),
    ]
    assert [p.pair_no for p in doc.pairs] == [1, 2]
    assert doc.pairs[1].a.location == "row 1, part 2"


def test_unequal_sentence_counts_stay_whole():
    a, b = "One sentence. And another.", "Одно предложение и ещё одно."
    assert texts(refine(doc_of(a, b))) == [(a, b)]


def test_reordered_sentences_stay_whole():
    # Same digits overall, but splitting would set 100 against 5.
    a = "The price is 100. Payment is due in 5 days."
    b = "Оплата производится в течение 5 дней. Цена составляет 100."
    assert texts(refine(doc_of(a, b))) == [(a, b)]


def test_a_real_difference_survives_the_split():
    doc = refine(doc_of("The price is 100. Payment is due in 5 days.",
                        "Цена составляет 100. Оплата производится в течение 7 дней."))
    assert len(doc.pairs) == 2


def test_lines_of_a_cell_are_split_when_counts_match():
    doc = refine(doc_of("Line one\nLine two", "Строка один\nСтрока два"))
    assert texts(doc) == [("Line one", "Строка один"), ("Line two", "Строка два")]


def test_incomplete_pairs_pass_through():
    pair = Pair(1, Segment("Only here.", "en", 0, "row 1"), None)
    doc = refine(Document([pair], "en", "ru", "two-files", []))
    assert doc.pairs == [pair]
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/test_segment.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.segment'`

- [ ] **Step 3: Create `src/bilingual_lint/segment.py`**

````python
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
````

- [ ] **Step 4: Run the test, then the whole suite**

Run: `$PY -m pytest -q`
Expected: `112 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: safe line and sentence refinement of pairs"
```

---

### Task 9: Configuration

**Files:**
- Create: `src/bilingual_lint/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test** `tests/test_config.py`

````python
import pytest

from bilingual_lint.config import RULE_DEFAULTS, Config, ConfigError, parse_langs


def write(tmp_path, text):
    path = tmp_path / ".bilingual-lint.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_defaults_without_a_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = Config.load(None)
    assert config.fail_on == "error" and config.langs is None
    assert config.rules == RULE_DEFAULTS and config.rules is not RULE_DEFAULTS


def test_file_overrides(tmp_path):
    (tmp_path / "terms.yaml").write_text("- {en: Buyer, ru: Покупатель}\n", encoding="utf-8")
    config = Config.load(write(tmp_path, (
        "langs: en,es\nfail_on: warning\nglossary: terms.yaml\nlow_confidence: 0.7\n"
        "rules:\n  BI011: {enabled: false}\n  BI006: {severity: error}\n"
        "llm: {max_pairs: 5}\n")))
    assert config.langs == ("en", "es") and config.fail_on == "warning"
    assert config.glossary == [{"en": "Buyer", "ru": "Покупатель"}]
    assert config.low_confidence == 0.7
    assert config.rules["BI011"]["enabled"] is False
    assert config.rules["BI006"]["severity"] == "error"
    assert config.llm["max_pairs"] == 5 and config.llm["timeout_seconds"] == 60


@pytest.mark.parametrize("text", [
    "unknown_key: 1", "fail_on: info", "langs: english", "langs: en,en",
    "low_confidence: 3", "rules: {BI999: {enabled: false}}",
    "rules: {BI001: {nope: 1}}", "rules: {BI001: {severity: fatal}}",
    "llm: {temperature: 1}", "glossary: missing.yaml", "- a list",
])
def test_bad_config_is_rejected(tmp_path, text):
    with pytest.raises(ConfigError):
        Config.load(write(tmp_path, text))


def test_parse_langs():
    assert parse_langs("EN, ru") == ("en", "ru")
    assert parse_langs(["en", "es"]) == ("en", "es")
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/test_config.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.config'`

- [ ] **Step 3: Create `src/bilingual_lint/config.py`**

````python
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import Severity


class ConfigError(Exception):
    pass


RULE_DEFAULTS: dict = {
    "BI000": {"enabled": True, "severity": "info"},
    "BI001": {"enabled": True, "severity": "error", "strict_separators": False},
    "BI002": {"enabled": True, "severity": "error", "missing_currency": True},
    "BI003": {"enabled": True, "severity": "error"},
    "BI004": {"enabled": True, "severity": "error"},
    "BI005": {"enabled": True, "severity": "error"},
    "BI006": {"enabled": True, "severity": "warning"},
    "BI007": {"enabled": True, "severity": "error", "min_ratio": 0.4, "max_ratio": 2.5,
              "min_chars": 80, "untranslated_min_letters": 20},
    "BI008": {"enabled": True, "severity": "warning"},
    "BI009": {"enabled": True, "severity": "error"},
    "BI010": {"enabled": True, "severity": "error"},
    "BI011": {"enabled": True, "severity": "info"},
}
LLM_DEFAULTS = {"model": "anthropic/claude-sonnet-5", "max_pairs": 50,
                "timeout_seconds": 60}
TOP_KEYS = {"langs", "fail_on", "glossary", "low_confidence", "rules", "llm"}
SEVERITY_VALUES = {s.value for s in Severity}
LANG_RE = re.compile(r"[a-z]{2,3}\Z")


def parse_langs(value) -> tuple:
    """'en,ru' or ['en', 'ru'] -> ('en', 'ru')."""
    items = value.split(",") if isinstance(value, str) else list(value or [])
    items = [str(item).strip().lower() for item in items]
    if len(items) != 2 or not all(LANG_RE.match(item) for item in items):
        raise ConfigError(f"langs must be two language codes such as en,ru; got {value!r}")
    if items[0] == items[1]:
        raise ConfigError("langs must name two different languages")
    return items[0], items[1]


def load_glossary(path: Path) -> list:
    """A YAML list of term entries: - {en: Buyer, ru: Покупатель}."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"glossary file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise ConfigError("glossary must be a list of mappings like {en: Buyer, ru: ...}")
    return [{str(k): str(v) for k, v in item.items()} for item in raw]


@dataclass
class Config:
    langs: tuple | None = None
    fail_on: str = "error"
    glossary: list = field(default_factory=list)
    low_confidence: float = 0.5
    rules: dict = field(default_factory=lambda: copy.deepcopy(RULE_DEFAULTS))
    llm: dict = field(default_factory=lambda: dict(LLM_DEFAULTS))

    @classmethod
    def load(cls, path: Path | str | None) -> Config:
        cfg = cls()
        if path is None:
            default = Path(".bilingual-lint.yaml")
            path = default if default.is_file() else None
        if path is None:
            return cfg
        path = Path(path)
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ConfigError("config root must be a mapping")
        unknown = set(raw) - TOP_KEYS
        if unknown:
            raise ConfigError(f"unknown config keys: {sorted(unknown)}")
        if raw.get("langs") is not None:
            cfg.langs = parse_langs(raw["langs"])
        if "fail_on" in raw:
            if raw["fail_on"] not in ("error", "warning"):
                raise ConfigError(f"fail_on must be error or warning, got {raw['fail_on']!r}")
            cfg.fail_on = raw["fail_on"]
        if raw.get("glossary"):
            cfg.glossary = load_glossary(path.parent / str(raw["glossary"]))
        if "low_confidence" in raw:
            value = raw["low_confidence"]
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ConfigError("low_confidence must be a number between 0 and 1")
            cfg.low_confidence = float(value)
        for rule_id, user_rule in (raw.get("rules") or {}).items():
            if rule_id not in RULE_DEFAULTS:
                raise ConfigError(f"unknown rule id: {rule_id}")
            if not isinstance(user_rule, dict):
                raise ConfigError(f"rules.{rule_id} must be a mapping")
            bad = set(user_rule) - set(RULE_DEFAULTS[rule_id])
            if bad:
                raise ConfigError(f"unknown keys for {rule_id}: {sorted(bad)}")
            if "severity" in user_rule and user_rule["severity"] not in SEVERITY_VALUES:
                raise ConfigError(
                    f"rules.{rule_id}.severity must be one of {sorted(SEVERITY_VALUES)}")
            cfg.rules[rule_id].update(user_rule)
        llm = raw.get("llm") or {}
        bad = set(llm) - set(LLM_DEFAULTS)
        if bad:
            raise ConfigError(f"unknown llm keys: {sorted(bad)}")
        cfg.llm.update(llm)
        return cfg
````

- [ ] **Step 4: Run the test**

Run: `$PY -m pytest tests/test_config.py -q`
Expected: `14 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: configuration file and rule defaults"
```

---

### Task 10: Value rules (BI001 to BI005, BI009)

All six compare extracted facts. `BI001`, `BI002` and `BI005` share one matching step: quantities are matched by value across the whole pair, whatever their kind; each rule then reports the unmatched quantities of its own kind, and the attribute differences (currency, unit, day type) of matched ones.

**Files:**
- Create: `src/bilingual_lint/analysis.py`, `src/bilingual_lint/rules/base.py`, `bi001_numbers.py`, `bi002_money.py`, `bi003_dates.py`, `bi004_words.py`, `bi005_durations.py`, `bi009_identifiers.py`
- Modify: `tests/helpers.py` (replace with the full version)
- Test: `tests/rules/test_value_rules.py`

- [ ] **Step 1: Replace `tests/helpers.py`** with the full version

````python
"""Shared test helpers: build Documents in memory and DOCX files on disk."""
from __future__ import annotations

from pathlib import Path

from docx import Document as new_docx

from bilingual_lint.analysis import analyse
from bilingual_lint.config import RULE_DEFAULTS
from bilingual_lint.models import Document, Pair, Segment


def make_doc(rows, lang_a="en", lang_b="ru", mode="two-column") -> Document:
    """rows: [(text_a, text_b)]; None on a side means no segment there."""
    pairs = []
    for i, (a, b) in enumerate(rows):
        pairs.append(Pair(
            i + 1,
            None if a is None else Segment(a, lang_a, i, f"row {i + 1}"),
            None if b is None else Segment(b, lang_b, i, f"row {i + 1}")))
    return analyse(Document(pairs, lang_a, lang_b, mode, []))


def check(rule_cls, rows, lang_a="en", lang_b="ru", **overrides) -> list:
    cfg = dict(RULE_DEFAULTS[rule_cls.id], glossary=[])
    cfg.update(overrides)
    return rule_cls().check(make_doc(rows, lang_a, lang_b), cfg)


def write_two_column(path: Path, rows, intro: str | None = None) -> Path:
    document = new_docx()
    if intro:
        document.add_paragraph(intro)
    table = document.add_table(rows=0, cols=2)
    for a, b in rows:
        cells = table.add_row().cells
        cells[0].text = a
        cells[1].text = b
    document.save(str(path))
    return path


def write_plain(path: Path, paragraphs) -> Path:
    document = new_docx()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(str(path))
    return path
````

- [ ] **Step 2: Write the failing test** `tests/rules/test_value_rules.py`

````python
"""BI001 numbers, BI002 amounts, BI003 dates, BI004 digits-vs-words,
BI005 durations, BI009 identifiers. Each rule has a clean case and a defect."""
from bilingual_lint.models import Severity
from bilingual_lint.rules.bi001_numbers import NumbersDiffer
from bilingual_lint.rules.bi002_money import AmountsDiffer
from bilingual_lint.rules.bi003_dates import DatesDiffer
from bilingual_lint.rules.bi004_words import DigitsAndWordsDisagree
from bilingual_lint.rules.bi005_durations import DurationsDiffer
from bilingual_lint.rules.bi009_identifiers import IdentifiersDiffer

from ..helpers import check

# --- BI001 -----------------------------------------------------------------

def test_bi001_clean_across_number_formats():
    rows = [("The lot is 1,500.5 kg in 3 boxes at 12%.",
             "Партия составляет 1 500,5 кг в 3 коробках под 12%.")]
    assert check(NumbersDiffer, rows) == []


def test_bi001_changed_number():
    rows = [("The lot is 1,500 kg in 3 boxes.", "Партия составляет 1 500 кг в 4 коробках.")]
    (finding,) = check(NumbersDiffer, rows)
    assert finding.rule_id == "BI001" and finding.severity is Severity.ERROR
    assert finding.context == {"only_a": ["3"], "only_b": ["4"]}
    assert finding.message == "numbers differ — en only: 3 · ru only: 4"


def test_bi001_number_spelled_out_on_the_other_side_is_not_a_defect():
    rows = [("Made in two copies.", "Составлен в 2 экземплярах.")]
    assert check(NumbersDiffer, rows) == []


def test_bi001_ignores_money_and_durations():
    rows = [("Pay USD 100 within 5 days.", "Оплатить 200 долларов США в течение 7 дней.")]
    assert check(NumbersDiffer, rows) == []


# --- BI002 -----------------------------------------------------------------

def test_bi002_clean():
    rows = [("The price is USD 150,000.00.", "Цена составляет 150 000,00 долларов США.")]
    assert check(AmountsDiffer, rows) == []


def test_bi002_amount_differs():
    rows = [("The price is USD 150,000.", "Цена составляет 105 000 долларов США.")]
    (finding,) = check(AmountsDiffer, rows)
    assert finding.severity is Severity.ERROR
    assert finding.message == "amounts differ — en only: 150,000 · ru only: 105 000"


def test_bi002_currency_differs():
    rows = [("The price is USD 150,000.", "Цена составляет 150 000 евро.")]
    (finding,) = check(AmountsDiffer, rows)
    assert finding.severity is Severity.ERROR
    assert finding.context == {"a": "USD", "b": "EUR"}


def test_bi002_currency_on_one_side_only_is_a_warning_and_can_be_turned_off():
    rows = [("The price is USD 150,000.", "Цена составляет 150 000.")]
    (finding,) = check(AmountsDiffer, rows)
    assert finding.severity is Severity.WARNING
    assert "currency stated on the en side only" in finding.message
    assert check(AmountsDiffer, rows, missing_currency=False) == []


# --- BI003 -----------------------------------------------------------------

def test_bi003_clean():
    rows = [("Signed on 12 March 2025.", "Подписан 12.03.2025.")]
    assert check(DatesDiffer, rows) == []


def test_bi003_date_differs():
    rows = [("Signed on 12 March 2025.", "Подписан 21 марта 2025 г.")]
    (finding,) = check(DatesDiffer, rows)
    assert finding.severity is Severity.ERROR
    assert finding.context == {"only_a": ["12 March 2025"], "only_b": ["21 марта 2025"]}


def test_bi003_ambiguous_order_is_a_warning():
    rows = [("Effective 02/03/2025.", "Действует с 3 февраля 2025 г.")]
    (finding,) = check(DatesDiffer, rows)
    assert finding.severity is Severity.WARNING
    assert "ambiguous day/month order" in finding.message


# --- BI004 -----------------------------------------------------------------

def test_bi004_clean():
    rows = [("Within ten (10) days.", "В течение 10 (десяти) дней.")]
    assert check(DigitsAndWordsDisagree, rows) == []


def test_bi004_digits_and_words_disagree_on_one_side():
    rows = [("Within ten (10) days.", "В течение 10 (пяти) дней.")]
    (finding,) = check(DigitsAndWordsDisagree, rows)
    assert finding.context == {"lang": "ru", "digits": "10", "words": "пяти"}
    assert finding.message == 'digits and words disagree on the ru side — 10 against "пяти"'


# --- BI005 -----------------------------------------------------------------

def test_bi005_clean_and_bare_days_mean_calendar_days():
    rows = [("Within 30 calendar days and 2 years.", "В течение 30 дней и 2 лет.")]
    assert check(DurationsDiffer, rows) == []


def test_bi005_day_type_differs():
    rows = [("Within 10 business days.", "В течение 10 дней.")]
    (finding,) = check(DurationsDiffer, rows)
    assert finding.severity is Severity.ERROR
    assert "day type differs — business against calendar days" in finding.message


def test_bi005_unit_differs():
    rows = [("Within 3 months.", "В течение 3 лет.")]
    (finding,) = check(DurationsDiffer, rows)
    assert "unit differs — month against year" in finding.message


def test_bi005_length_differs():
    rows = [("Within 10 business days.", "В течение 15 рабочих дней.")]
    (finding,) = check(DurationsDiffer, rows)
    assert finding.message == "durations differ — en only: 10 · ru only: 15"


# --- BI009 -----------------------------------------------------------------

def test_bi009_clean():
    rows = [("INN 7701234567, mail info@example.com", "ИНН 7701234567, почта info@example.com")]
    assert check(IdentifiersDiffer, rows) == []


def test_bi009_identifier_differs():
    rows = [("IBAN DE89 3704 0044 0532 0130 00", "IBAN DE89 3704 0044 0532 0130 01")]
    (finding,) = check(IdentifiersDiffer, rows)
    assert finding.severity is Severity.ERROR
    assert finding.context == {"only_a": ["DE89370400440532013000"],
                               "only_b": ["DE89370400440532013001"]}
````

- [ ] **Step 3: Run it and watch it fail**

Run: `$PY -m pytest tests/rules/test_value_rules.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.analysis'`

- [ ] **Step 4: Create `src/bilingual_lint/analysis.py`**

````python
from __future__ import annotations

from .facts.extract import extract_facts
from .models import Document


def analyse(doc: Document, strict: bool = False) -> Document:
    """Extract the facts of every complete pair. Rules read these facts; they
    never parse numbers out of raw text themselves."""
    for pair in doc.complete_pairs():
        pair.facts_a = extract_facts(pair.a.text, doc.lang_a, strict)
        pair.facts_b = extract_facts(pair.b.text, doc.lang_b, strict)
    return doc
````

- [ ] **Step 5: Create an empty `src/bilingual_lint/rules/__init__.py`** (Task 12 fills it) **and `src/bilingual_lint/rules/base.py`**

````python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..facts.numbers import match_quantities
from ..models import Document, Finding, Pair, Severity
from ..wordlists import load_wordlists


@runtime_checkable
class Rule(Protocol):
    id: str
    name: str
    description: str
    default_severity: Severity
    needs_wordlists: bool  # True: runs only when both languages have a wordlist

    def check(self, doc: Document, cfg: dict) -> list[Finding]: ...


def supported(rule: Rule, doc: Document) -> bool:
    if not rule.needs_wordlists:
        return True
    return all(load_wordlists(lang).has_language_rules
               for lang in (doc.lang_a, doc.lang_b))


def severity_of(cfg: dict) -> Severity:
    return Severity(cfg["severity"])


def soften(severity: Severity) -> Severity:
    """One step down, for the less certain findings of a rule."""
    return Severity.WARNING if severity is Severity.ERROR else severity


def unmatched_quantities(pair: Pair) -> tuple[list, list, list]:
    """(matched pairs, only on side a, only on side b). A number that the other
    side spells out in words ('2' against 'two') is not counted as unmatched."""
    matched, only_a, only_b = match_quantities(
        pair.facts_a.quantities, pair.facts_b.quantities)
    only_a = [q for q in only_a if not (q.cands & pair.facts_b.word_values)]
    only_b = [q for q in only_b if not (q.cands & pair.facts_a.word_values)]
    return matched, only_a, only_b


def describe(doc: Document, items_a: list, items_b: list) -> str:
    parts = []
    if items_a:
        parts.append(f"{doc.lang_a} only: {', '.join(items_a)}")
    if items_b:
        parts.append(f"{doc.lang_b} only: {', '.join(items_b)}")
    return " · ".join(parts)


def value_findings(doc: Document, cfg: dict, rule_id: str, kinds: tuple,
                   label: str) -> list[Finding]:
    """One finding per pair whose quantities of the given kinds do not match."""
    out = []
    for pair in doc.complete_pairs():
        _, only_a, only_b = unmatched_quantities(pair)
        raw_a = [q.raw for q in only_a if q.kind in kinds]
        raw_b = [q.raw for q in only_b if q.kind in kinds]
        if raw_a or raw_b:
            out.append(Finding(
                rule_id, severity_of(cfg),
                f"{label} differ — {describe(doc, raw_a, raw_b)}", pair,
                {"only_a": raw_a, "only_b": raw_b}))
    return out
````

- [ ] **Step 6: Create `src/bilingual_lint/rules/bi001_numbers.py`**

````python
from __future__ import annotations

from ..models import Document, Finding, Severity
from .base import value_findings


class NumbersDiffer:
    id = "BI001"
    name = "numbers"
    description = "a number or percentage appears on one side only"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        return value_findings(doc, cfg, self.id, ("number", "percent"), "numbers")
````

- [ ] **Step 7: Create `src/bilingual_lint/rules/bi002_money.py`**

````python
from __future__ import annotations

from ..models import Document, Finding, Severity
from .base import severity_of, soften, unmatched_quantities, value_findings


class AmountsDiffer:
    id = "BI002"
    name = "amounts"
    description = "a money amount or its currency differs"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = value_findings(doc, cfg, self.id, ("money",), "amounts")
        severity = severity_of(cfg)
        for pair in doc.complete_pairs():
            matched, _, _ = unmatched_quantities(pair)
            for qa, qb in matched:
                if qa.kind == "money" and qb.kind == "money":
                    if qa.unit != qb.unit:
                        out.append(Finding(
                            self.id, severity,
                            f"currency differs — {doc.lang_a}: {qa.raw} {qa.unit} · "
                            f"{doc.lang_b}: {qb.raw} {qb.unit}", pair,
                            {"a": qa.unit, "b": qb.unit}))
                elif cfg["missing_currency"] and "money" in (qa.kind, qb.kind):
                    money, lang = (qa, doc.lang_a) if qa.kind == "money" else (qb, doc.lang_b)
                    out.append(Finding(
                        self.id, soften(severity),
                        f"currency stated on the {lang} side only — {money.raw} {money.unit}",
                        pair, {"currency": money.unit}))
        return out
````

- [ ] **Step 8: Create `src/bilingual_lint/rules/bi003_dates.py`**

````python
from __future__ import annotations

from ..facts.dates import match_dates
from ..models import Document, Finding, Severity
from .base import describe, severity_of, soften


class DatesDiffer:
    id = "BI003"
    name = "dates"
    description = "a date differs, or agrees only under one day/month reading"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        severity = severity_of(cfg)
        for pair in doc.complete_pairs():
            ambiguous, only_a, only_b = match_dates(pair.facts_a.dates, pair.facts_b.dates)
            if only_a or only_b:
                raw_a, raw_b = [d.raw for d in only_a], [d.raw for d in only_b]
                out.append(Finding(
                    self.id, severity, f"dates differ — {describe(doc, raw_a, raw_b)}",
                    pair, {"only_a": raw_a, "only_b": raw_b}))
            for da, db in ambiguous:
                out.append(Finding(
                    self.id, soften(severity),
                    f"ambiguous day/month order — {da.raw} against {db.raw} agree "
                    "only under one reading; write the month in words", pair,
                    {"a": da.raw, "b": db.raw}))
        return out
````

- [ ] **Step 9: Create `src/bilingual_lint/rules/bi004_words.py`**

````python
from __future__ import annotations

from ..models import Document, Finding, Severity
from .base import severity_of


class DigitsAndWordsDisagree:
    id = "BI004"
    name = "digits-vs-words"
    description = "digits and the number in words disagree on the same side"
    default_severity = Severity.ERROR
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        for pair in doc.complete_pairs():
            for lang, facts in ((doc.lang_a, pair.facts_a), (doc.lang_b, pair.facts_b)):
                for digits, words in facts.word_digit_mismatches:
                    out.append(Finding(
                        self.id, severity_of(cfg),
                        f"digits and words disagree on the {lang} side — "
                        f"{digits} against \"{words}\"", pair,
                        {"lang": lang, "digits": digits, "words": words}))
        return out
````

- [ ] **Step 10: Create `src/bilingual_lint/rules/bi005_durations.py`**

````python
from __future__ import annotations

from ..models import Document, Finding, Severity
from .base import severity_of, unmatched_quantities, value_findings


def _day_type(quantity) -> str:
    # A bare "30 days" means calendar days.
    return quantity.day_type or "calendar"


class DurationsDiffer:
    id = "BI005"
    name = "durations"
    description = "a time period differs in length, unit or day type"
    default_severity = Severity.ERROR
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = value_findings(doc, cfg, self.id, ("duration",), "durations")
        for pair in doc.complete_pairs():
            matched, _, _ = unmatched_quantities(pair)
            for qa, qb in matched:
                if qa.kind != "duration" or qb.kind != "duration":
                    continue
                if qa.unit != qb.unit:
                    what = f"unit differs — {qa.unit} against {qb.unit}"
                elif qa.unit == "day" and _day_type(qa) != _day_type(qb):
                    what = f"day type differs — {_day_type(qa)} against {_day_type(qb)} days"
                else:
                    continue
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"duration {what} ({doc.lang_a}: {qa.raw}, {doc.lang_b}: {qb.raw})",
                    pair, {"a": [qa.unit, _day_type(qa)], "b": [qb.unit, _day_type(qb)]}))
        return out
````

- [ ] **Step 11: Create `src/bilingual_lint/rules/bi009_identifiers.py`**

````python
from __future__ import annotations

from collections import Counter

from ..models import Document, Finding, Severity
from .base import describe, severity_of


class IdentifiersDiffer:
    id = "BI009"
    name = "identifiers"
    description = "a registration number, IBAN, e-mail or URL differs"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        for pair in doc.complete_pairs():
            ids_a = Counter(pair.facts_a.identifiers)
            ids_b = Counter(pair.facts_b.identifiers)
            if ids_a == ids_b:
                continue
            only_a = sorted((ids_a - ids_b).elements())
            only_b = sorted((ids_b - ids_a).elements())
            out.append(Finding(
                self.id, severity_of(cfg),
                f"identifiers differ — {describe(doc, only_a, only_b)}", pair,
                {"only_a": only_a, "only_b": only_b}))
        return out
````

- [ ] **Step 12: Run the test**

Run: `$PY -m pytest tests/rules/test_value_rules.py -q`
Expected: `19 passed`

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "feat: value rules BI001-BI005 and BI009"
```

---

### Task 11: Text rules (BI006, BI007, BI008, BI010, BI011)

**Files:**
- Create: `src/bilingual_lint/rules/bi006_refs.py`, `bi007_structure.py`, `bi008_terms.py`, `bi010_prevailing.py`, `bi011_modality.py`
- Test: `tests/rules/test_text_rules.py`

- [ ] **Step 1: Write the failing test** `tests/rules/test_text_rules.py`

````python
"""BI006 references, BI007 missing text, BI008 terms, BI010 prevailing
language, BI011 obligation cues. Each rule has a clean case and a defect."""
import pytest

from bilingual_lint.models import Severity
from bilingual_lint.rules.bi006_refs import ReferencesDiffer
from bilingual_lint.rules.bi007_structure import SegmentsDiffer
from bilingual_lint.rules.bi008_terms import TermsDiffer, definitions, learn_terms
from bilingual_lint.rules.bi010_prevailing import PrevailingLanguage, prevailing
from bilingual_lint.rules.bi011_modality import ModalityDiffers, cues

from ..helpers import check, make_doc

# --- BI006 -----------------------------------------------------------------

def test_bi006_clean():
    rows = [("5.2. As provided in clauses 3.1 and 3.4.", "5.2. Как указано в пп. 3.1 и 3.4.")]
    assert check(ReferencesDiffer, rows) == []


def test_bi006_cross_reference_differs():
    rows = [("5.2. As provided in clause 3.1.", "5.2. Как указано в п. 3.4.")]
    (finding,) = check(ReferencesDiffer, rows)
    assert finding.severity is Severity.WARNING
    assert finding.message == "cross-references differ — en only: 3.1 · ru only: 3.4"


def test_bi006_clause_number_differs():
    rows = [("5.2. The Buyer pays.", "5.3. Покупатель платит.")]
    (finding,) = check(ReferencesDiffer, rows)
    assert finding.message == "clause number differs — en: 5.2 · ru: 5.3"


# --- BI007 -----------------------------------------------------------------

LONG_EN = "The Seller shall deliver the goods to the warehouse of the Buyer in good order."
LONG_RU = "Продавец обязуется доставить товар на склад Покупателя в надлежащем состоянии."


def test_bi007_clean():
    assert check(SegmentsDiffer, [(LONG_EN, LONG_RU), ("Title", "Заголовок")]) == []


def test_bi007_missing_counterpart_and_empty_cell():
    findings = check(SegmentsDiffer, [(LONG_EN, None), ("Signatures", "  ")])
    assert [f.message for f in findings] == [
        "segment has no counterpart on the ru side", "empty on the ru side"]
    assert all(f.severity is Severity.ERROR for f in findings)


def test_bi007_untranslated_text():
    (finding,) = check(SegmentsDiffer, [(LONG_EN, LONG_EN)])
    assert finding.severity is Severity.WARNING
    assert finding.message.startswith("text on the ru side does not look like ru")


def test_bi007_short_identical_text_is_not_flagged():
    assert check(SegmentsDiffer, [("Beta GmbH", "Beta GmbH")]) == []


def test_bi007_length_far_off():
    rows = [(LONG_EN, LONG_RU)] * 3 + [(LONG_EN + " " + LONG_EN + " " + LONG_EN, LONG_RU)]
    (finding,) = check(SegmentsDiffer, rows)
    assert finding.severity is Severity.WARNING and "length is far off" in finding.message


def test_bi007_identical_text_in_same_script_pair():
    text = "The Seller shall deliver the goods to the Buyer."
    (finding,) = check(SegmentsDiffer, [(text, text)], lang_a="en", lang_b="es")
    assert finding.message.startswith("both sides are identical")


# --- BI008 -----------------------------------------------------------------

DEFINING = ('Alpha LLC (the "Seller") and Beta GmbH (the "Buyer") agree as follows.',
            "ООО «Альфа» (далее – «Продавец») и Beta GmbH (далее – «Покупатель») "
            "договорились о нижеследующем.")


def test_definitions_are_found_in_order():
    assert definitions(DEFINING[0], "en") == ["Seller", "Buyer"]
    assert definitions(DEFINING[1], "ru") == ["Продавец", "Покупатель"]
    assert definitions('"Goods" means the equipment.', "en") == ["Goods"]
    assert definitions("«Товар» означает оборудование.", "ru") == ["Товар"]


def test_terms_are_learned_from_the_document():
    assert learn_terms(make_doc([DEFINING])) == [
        ("Seller", "Продавец"), ("Buyer", "Покупатель")]


def test_bi008_clean_with_inflected_forms():
    rows = [DEFINING, ("The Buyer's goods go to the Seller.",
                       "Товар Покупателя передаётся Продавцу.")]
    assert check(TermsDiffer, rows) == []


def test_bi008_term_rendered_differently():
    rows = [DEFINING, ("The Buyer shall inspect the goods.", "Заказчик осматривает товар.")]
    (finding,) = check(TermsDiffer, rows)
    assert finding.severity is Severity.WARNING
    assert finding.pair.pair_no == 2
    assert finding.message == 'term "Buyer" is used, but "Покупатель" is not on the ru side'


def test_bi008_glossary_terms():
    rows = [("The Goods are delivered.", "Продукция поставляется.")]
    assert check(TermsDiffer, rows) == []
    (finding,) = check(TermsDiffer, rows, glossary=[{"en": "Goods", "ru": "Товар"}])
    assert finding.context == {"term_a": "Goods", "term_b": "Товар"}


# --- BI010 -----------------------------------------------------------------

@pytest.mark.parametrize("text, lang, expected", [
    ("In case of discrepancy the English text shall prevail.", "en", "en"),
    ("In case of discrepancy between the English and Russian versions, "
     "the Russian version shall prevail.", "en", "ru"),
    ("The English version prevails over the Russian version.", "en", "en"),
    ("Both the English and Russian texts have equal legal force.", "en", "equal"),
    ("This Agreement shall prevail over its annexes.", "en", None),
    ("Made in English and Russian.", "en", None),
    ("В случае расхождений преимущество имеет текст на русском языке.", "ru", "ru"),
    ("В случае расхождений между русским и английским текстами преимущество "
     "имеет текст на английском языке.", "ru", "en"),
    ("В случае расхождений между русским и английским текстами преимущество "
     "имеет русский текст.", "ru", "ru"),
    ("Русская версия имеет преимущественную силу перед английской.", "ru", "ru"),
    ("Тексты на русском и английском языках имеют равную юридическую силу.", "ru", "equal"),
])
def test_prevailing_reading(text, lang, expected):
    assert prevailing(text, lang) == expected


def test_bi010_clean():
    rows = [("In case of discrepancy the English text shall prevail.",
             "В случае расхождений преимущество имеет текст на английском языке.")]
    assert check(PrevailingLanguage, rows) == []


def test_bi010_each_side_names_a_different_language():
    rows = [("In case of discrepancy the English text shall prevail.",
             "В случае расхождений преимущество имеет текст на русском языке.")]
    (finding,) = check(PrevailingLanguage, rows)
    assert finding.severity is Severity.ERROR
    assert finding.context == {"a": "en", "b": "ru"}
    assert finding.message == ("the two sides disagree on which language prevails — "
                               "en side: en · ru side: ru")


def test_bi010_clause_on_one_side_only():
    rows = [("In case of discrepancy the English text shall prevail.",
             "Договор составлен в двух экземплярах.")]
    (finding,) = check(PrevailingLanguage, rows)
    assert finding.message == "prevailing-language clause found on the en side only"


def test_bi010_equal_force_against_one_language():
    rows = [("Both the English and Russian texts have equal legal force.",
             "В случае расхождений преимущество имеет текст на русском языке.")]
    (finding,) = check(PrevailingLanguage, rows)
    assert "en side: both languages equally · ru side: ru" in finding.message


def test_bi010_no_clause_at_all_is_reported_as_information():
    (finding,) = check(PrevailingLanguage, [("The Buyer pays.", "Покупатель платит.")])
    assert finding.severity is Severity.INFO and finding.pair is None
    assert finding.message == "no prevailing-language clause found"


# --- BI011 -----------------------------------------------------------------

def test_cues():
    assert cues("The Seller may not assign its rights.", "en") == {
        "obligation": False, "permission": True, "negation": True}
    assert cues("Продавец обязан поставить товар.", "ru") == {
        "obligation": True, "permission": False, "negation": False}
    assert cues("Agreement No. 15", "en")["negation"] is False


def test_bi011_clean():
    rows = [("The Seller may not assign its rights.", "Продавец не вправе уступать права."),
            ("The Buyer shall pay.", "Покупатель обязан оплатить.")]
    assert check(ModalityDiffers, rows) == []


def test_bi011_dropped_negation():
    rows = [("The Seller may not assign its rights.", "Продавец вправе уступать права.")]
    (finding,) = check(ModalityDiffers, rows)
    assert finding.severity is Severity.INFO
    assert finding.message == "negation on the en side only — check the meaning"


def test_bi011_obligation_against_permission():
    rows = [("The Buyer shall inspect the goods.", "Покупатель вправе осмотреть товар.")]
    (finding,) = check(ModalityDiffers, rows)
    assert finding.message == ("an obligation on the en side reads as a permission on "
                               "the ru side — check the meaning")
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/rules/test_text_rules.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.rules.bi006_refs'`

- [ ] **Step 3: Create `src/bilingual_lint/rules/bi006_refs.py`**

````python
from __future__ import annotations

from collections import Counter

from ..models import Document, Finding, Severity
from .base import describe, severity_of


class ReferencesDiffer:
    id = "BI006"
    name = "clause-references"
    description = "a clause number or cross-reference differs"
    default_severity = Severity.WARNING
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        for pair in doc.complete_pairs():
            lead_a, lead_b = pair.facts_a.leading_number, pair.facts_b.leading_number
            if lead_a != lead_b:
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"clause number differs — {doc.lang_a}: {lead_a or 'none'} · "
                    f"{doc.lang_b}: {lead_b or 'none'}", pair, {"a": lead_a, "b": lead_b}))
            refs_a, refs_b = Counter(pair.facts_a.refs), Counter(pair.facts_b.refs)
            if refs_a != refs_b:
                only_a = sorted((refs_a - refs_b).elements())
                only_b = sorted((refs_b - refs_a).elements())
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"cross-references differ — {describe(doc, only_a, only_b)}", pair,
                    {"only_a": only_a, "only_b": only_b}))
        return out
````

- [ ] **Step 4: Create `src/bilingual_lint/rules/bi007_structure.py`**

````python
from __future__ import annotations

from statistics import median

from ..models import Document, Finding, Severity
from ..text_utils import letters, script_for_lang, script_of
from .base import severity_of, soften


class SegmentsDiffer:
    id = "BI007"
    name = "missing-text"
    description = "a segment is missing, empty, untranslated or far off in length"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        severity = severity_of(cfg)
        complete = doc.complete_pairs()
        ratios = [len(p.b.text) / len(p.a.text) for p in complete if len(p.a.text) >= 20]
        typical = median(ratios) if ratios else 1.0
        scripts = (script_for_lang(doc.lang_a), script_for_lang(doc.lang_b))
        for pair in doc.pairs:
            if pair.a is None or pair.b is None:
                missing = doc.lang_a if pair.a is None else doc.lang_b
                out.append(Finding(self.id, severity,
                                   f"segment has no counterpart on the {missing} side",
                                   pair, {"missing": missing}))
                continue
            if not pair.complete:
                empty = doc.lang_a if not pair.a.text.strip() else doc.lang_b
                out.append(Finding(self.id, severity, f"empty on the {empty} side",
                                   pair, {"missing": empty}))
                continue
            text_a, text_b = pair.a.text, pair.b.text
            enough = min(letters(text_a), letters(text_b)) >= cfg["untranslated_min_letters"]
            if enough and scripts[0] != scripts[1]:
                for lang, text, want in ((doc.lang_a, text_a, scripts[0]),
                                         (doc.lang_b, text_b, scripts[1])):
                    if script_of(text) != want:
                        out.append(Finding(
                            self.id, soften(severity),
                            f"text on the {lang} side does not look like {lang} — "
                            "possibly left untranslated", pair, {"lang": lang}))
            elif enough and text_a.strip() == text_b.strip():
                out.append(Finding(self.id, soften(severity),
                                   "both sides are identical — possibly left untranslated",
                                   pair, {}))
            if max(len(text_a), len(text_b)) >= cfg["min_chars"]:
                relative = (len(text_b) / len(text_a)) / typical
                if not cfg["min_ratio"] <= relative <= cfg["max_ratio"]:
                    out.append(Finding(
                        self.id, soften(severity),
                        f"length is far off — {len(text_a)} characters against "
                        f"{len(text_b)}; text may be missing", pair,
                        {"relative_ratio": round(relative, 2)}))
        return out
````

- [ ] **Step 5: Create `src/bilingual_lint/rules/bi008_terms.py`**

````python
from __future__ import annotations

import re

from ..models import Document, Finding, Severity
from ..wordlists import load_wordlists
from .base import severity_of

FLAGS = re.IGNORECASE | re.UNICODE
INFLECTED = {"ru"}  # languages where a term changes its ending


def definitions(text: str, lang: str) -> list:
    """Defined terms introduced in this text, in order of appearance."""
    patterns = load_wordlists(lang).raw.get("definitions") or {}
    found = []
    for key in ("inline", "leading"):
        if key in patterns:
            found.extend((m.start(), m.group(1).strip())
                         for m in re.finditer(patterns[key], text, FLAGS))
    return [term for _, term in sorted(found)]


def term_pattern(term: str, lang: str) -> re.Pattern:
    pieces = []
    for word in term.split():
        if lang in INFLECTED and len(word) >= 5:
            pieces.append(re.escape(word[:-2]) + r"\w*")
        else:
            pieces.append(re.escape(word) + r"(?:s|'s|’s)?")
    return re.compile(r"(?<!\w)" + r"\s+".join(pieces) + r"(?!\w)", FLAGS)


def learn_terms(doc: Document) -> list:
    """Term pairs taken from the document's own definitions."""
    learned = []
    for pair in doc.complete_pairs():
        terms_a = definitions(pair.a.text, doc.lang_a)
        terms_b = definitions(pair.b.text, doc.lang_b)
        if terms_a and len(terms_a) == len(terms_b):
            learned.extend(zip(terms_a, terms_b, strict=True))
    return learned


class TermsDiffer:
    id = "BI008"
    name = "terms"
    description = "a defined term or glossary term is rendered inconsistently"
    default_severity = Severity.WARNING
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        terms = learn_terms(doc)
        for entry in cfg.get("glossary") or []:
            if doc.lang_a in entry and doc.lang_b in entry:
                terms.append((entry[doc.lang_a], entry[doc.lang_b]))
        out = []
        for term_a, term_b in dict.fromkeys(terms):
            pattern_a = term_pattern(term_a, doc.lang_a)
            pattern_b = term_pattern(term_b, doc.lang_b)
            for pair in doc.complete_pairs():
                in_a = bool(pattern_a.search(pair.a.text))
                in_b = bool(pattern_b.search(pair.b.text))
                if in_a == in_b:
                    continue
                present, absent = (term_a, term_b) if in_a else (term_b, term_a)
                side = doc.lang_b if in_a else doc.lang_a
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"term \"{present}\" is used, but \"{absent}\" is not on the {side} side",
                    pair, {"term_a": term_a, "term_b": term_b}))
        return out
````

- [ ] **Step 6: Create `src/bilingual_lint/rules/bi010_prevailing.py`**

How the prevailing language is read: a clause normally names the prevailing language once more than the other ("between the English and Russian texts, the English text prevails"), so the most-mentioned language wins. On a tie, the language named nearest before the cue word wins. A cue word with no language named is not a language clause and is ignored. Anything else is reported as unclear, never guessed.

````python
from __future__ import annotations

import re

from ..models import Document, Finding, Severity
from ..wordlists import load_wordlists
from .base import severity_of

FLAGS = re.IGNORECASE | re.UNICODE
WORDS = {"equal": "both languages equally", "unclear": "unclear"}


def _spans(patterns: list, text: str) -> list:
    return [m.start() for p in patterns
            for m in re.finditer(r"(?<!\w)(?:" + p + r")(?!\w)", text, FLAGS)]


def prevailing(text: str, lang: str) -> str | None:
    """Which language this text says prevails: a language code, 'equal',
    'unclear', or None when it is not a prevailing-language clause."""
    data = load_wordlists(lang).raw.get("prevailing") or {}
    mentions = {code: _spans(patterns, text)
                for code, patterns in (data.get("languages") or {}).items()}
    mentions = {code: spans for code, spans in mentions.items() if spans}
    if not mentions:
        return None
    if _spans(data.get("equal") or [], text):
        return "equal"
    cues = _spans(data.get("cues") or [], text)
    if not cues:
        return None
    # The prevailing language is normally named once more than the other
    # ("between the English and Russian texts, the English text prevails").
    most = max(len(spans) for spans in mentions.values())
    leaders = [code for code, spans in mentions.items() if len(spans) == most]
    if len(leaders) == 1:
        return leaders[0]
    cue = cues[0]
    before = {code: max((s for s in mentions[code] if s < cue), default=None)
              for code in leaders}
    before = {code: pos for code, pos in before.items() if pos is not None}
    if before:
        return max(before, key=before.get)
    after = {code: min(mentions[code]) for code in leaders}
    nearest = min(after.values())
    winners = [code for code, pos in after.items() if pos == nearest]
    return winners[0] if len(winners) == 1 else "unclear"


class PrevailingLanguage:
    id = "BI010"
    name = "prevailing-language"
    description = "the prevailing-language clause is one-sided or contradicts itself"
    default_severity = Severity.ERROR
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        seen = False
        for pair in doc.complete_pairs():
            says_a = prevailing(pair.a.text, doc.lang_a)
            says_b = prevailing(pair.b.text, doc.lang_b)
            if says_a is None and says_b is None:
                continue
            seen = True
            context = {"a": says_a, "b": says_b}
            if says_a is None or says_b is None:
                side = doc.lang_a if says_b is None else doc.lang_b
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"prevailing-language clause found on the {side} side only", pair,
                    context))
            elif "unclear" in (says_a, says_b):
                out.append(Finding(
                    self.id, Severity.INFO,
                    "prevailing-language clause found, but the tool could not tell "
                    "which language it names — check by hand", pair, context))
            elif says_a != says_b:
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"the two sides disagree on which language prevails — "
                    f"{doc.lang_a} side: {WORDS.get(says_a, says_a)} · "
                    f"{doc.lang_b} side: {WORDS.get(says_b, says_b)}", pair, context))
        if not seen:
            out.append(Finding(self.id, Severity.INFO,
                               "no prevailing-language clause found"))
        return out
````

- [ ] **Step 7: Create `src/bilingual_lint/rules/bi011_modality.py`**

````python
from __future__ import annotations

import re

from ..models import Document, Finding, Severity
from ..wordlists import load_wordlists
from .base import severity_of

FLAGS = re.IGNORECASE | re.UNICODE


def cues(text: str, lang: str) -> dict:
    """{'obligation': bool, 'permission': bool, 'negation': bool} for a text."""
    data = load_wordlists(lang).raw.get("modality") or {}
    return {kind: any(re.search(r"(?<!\w)(?:" + p + r")(?!\w)", text, FLAGS)
                      for p in data.get(kind) or [])
            for kind in ("obligation", "permission", "negation")}


class ModalityDiffers:
    id = "BI011"
    name = "obligation-cues"
    description = "obligation, permission or negation wording differs (heuristic)"
    default_severity = Severity.INFO
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        for pair in doc.complete_pairs():
            a, b = cues(pair.a.text, doc.lang_a), cues(pair.b.text, doc.lang_b)
            if a["negation"] != b["negation"]:
                side = doc.lang_a if a["negation"] else doc.lang_b
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"negation on the {side} side only — check the meaning", pair,
                    {"a": a, "b": b}))
            for must, may in ((a, b), (b, a)):
                if (must["obligation"] and not must["permission"]
                        and may["permission"] and not may["obligation"]):
                    strong = doc.lang_a if must is a else doc.lang_b
                    weak = doc.lang_b if must is a else doc.lang_a
                    out.append(Finding(
                        self.id, severity_of(cfg),
                        f"an obligation on the {strong} side reads as a permission on "
                        f"the {weak} side — check the meaning", pair, {"a": a, "b": b}))
        return out
````

- [ ] **Step 8: Run the test**

Run: `$PY -m pytest tests/rules/test_text_rules.py -q`
Expected: `34 passed`

- [ ] **Step 9: Prove the guard.** In `en.yaml`, change the negation entry `'no(?!\.\s?\d)'` to `'no'`. Run again.

Expected: `test_cues` fails on `Agreement No. 15`, which would be read as a negation. Restore; expected `34 passed`.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: text rules BI006-BI008, BI010, BI011"
```

---

### Task 12: Rule registry and `run_all`

**Files:**
- Modify: `src/bilingual_lint/rules/__init__.py` (replace the empty file)
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write the failing test** `tests/test_registry.py`

````python
from bilingual_lint.config import RULE_DEFAULTS, Config
from bilingual_lint.models import Severity
from bilingual_lint.rules import ALL_RULES, run_all
from bilingual_lint.rules.base import Rule

from .helpers import make_doc


def test_every_rule_is_registered_once_and_has_defaults():
    ids = [rule.id for rule in ALL_RULES]
    assert ids == [f"BI{n:03d}" for n in range(1, 12)]
    assert set(ids) | {"BI000"} == set(RULE_DEFAULTS)
    for rule in ALL_RULES:
        assert isinstance(rule, Rule)
        assert RULE_DEFAULTS[rule.id]["severity"] == rule.default_severity.value


def test_run_all_sorts_and_reports_what_ran():
    doc = make_doc([("See clause 3.1.", "См. п. 3.4."), ("Pay 5 units.", "Оплатить 6 единиц.")])
    findings, ran, disabled, skipped = run_all(doc, Config())
    assert [f.rule_id for f in findings] == ["BI001", "BI006", "BI010"]
    assert ran == [f"BI{n:03d}" for n in range(12)] and disabled == [] and skipped == []


def test_run_all_respects_disabled_and_only():
    doc = make_doc([("Pay 5 units.", "Оплатить 6 единиц.")])
    config = Config()
    config.rules["BI001"]["enabled"] = False
    findings, ran, disabled, _ = run_all(doc, config, only={"BI001", "BI002"})
    assert findings == [] and ran == ["BI002"] and "BI001" in disabled


def test_low_confidence_pairs_are_downgraded():
    doc = make_doc([("Pay 5 units.", "Оплатить 6 единиц.")], mode="two-files")
    doc.pairs[0].confidence = 0.3
    (finding,) = run_all(doc, Config(), only={"BI001"})[0]
    assert finding.severity is Severity.WARNING
    assert finding.context["pairing"] == "low confidence — check the pairing first"


def test_rules_needing_wordlists_are_skipped_for_other_pairs():
    doc = make_doc([("Pay 5 units.", "Pagar 6 unidades.")], lang_a="en", lang_b="es")
    findings, ran, _, skipped = run_all(doc, Config())
    assert skipped == ["BI004", "BI005", "BI008", "BI010", "BI011"]
    assert [f.rule_id for f in findings] == ["BI001"]


def test_strict_separators_expose_a_convention_mix_up():
    rows = [("A fee of 1,000 units.", "Плата в размере 1,000 единиц.")]
    assert run_all(make_doc(rows), Config(), only={"BI001"})[0] == []
    config = Config()
    config.rules["BI001"]["strict_separators"] = True
    findings, *_ = run_all(make_doc(rows), config, only={"BI001"})
    assert [f.rule_id for f in findings] == ["BI001"]
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/test_registry.py -q`
Expected: `ImportError: cannot import name 'ALL_RULES' from 'bilingual_lint.rules'`

- [ ] **Step 3: Write `src/bilingual_lint/rules/__init__.py`**

````python
from __future__ import annotations

from ..analysis import analyse
from ..config import Config
from ..models import Document, Finding, Severity
from .base import Rule, supported
from .bi001_numbers import NumbersDiffer
from .bi002_money import AmountsDiffer
from .bi003_dates import DatesDiffer
from .bi004_words import DigitsAndWordsDisagree
from .bi005_durations import DurationsDiffer
from .bi006_refs import ReferencesDiffer
from .bi007_structure import SegmentsDiffer
from .bi008_terms import TermsDiffer
from .bi009_identifiers import IdentifiersDiffer
from .bi010_prevailing import PrevailingLanguage
from .bi011_modality import ModalityDiffers

ALL_RULES: list[Rule] = [
    NumbersDiffer(),
    AmountsDiffer(),
    DatesDiffer(),
    DigitsAndWordsDisagree(),
    DurationsDiffer(),
    ReferencesDiffer(),
    SegmentsDiffer(),
    TermsDiffer(),
    IdentifiersDiffer(),
    PrevailingLanguage(),
    ModalityDiffers(),
]


def sort_key(finding: Finding) -> tuple:
    return (-finding.severity.rank, finding.pair.pair_no if finding.pair else 0,
            finding.rule_id)


def run_all(doc: Document, config: Config,
            only: set | None = None) -> tuple[list, list, list, list]:
    """Returns (findings, ran, disabled, skipped). 'skipped' lists rules that
    need wordlists this language pair does not have."""
    analyse(doc, strict=config.rules["BI001"]["strict_separators"])
    findings: list = []
    ran: list = []
    disabled: list = []
    skipped: list = []

    def wanted(rule_id: str) -> bool:
        return config.rules[rule_id]["enabled"] and (only is None or rule_id in only)

    if wanted("BI000"):
        ran.append("BI000")
        findings.extend(doc.notes)
    else:
        disabled.append("BI000")
    for rule in ALL_RULES:
        if not wanted(rule.id):
            disabled.append(rule.id)
        elif not supported(rule, doc):
            skipped.append(rule.id)
        else:
            ran.append(rule.id)
            cfg = dict(config.rules[rule.id], glossary=config.glossary)
            findings.extend(rule.check(doc, cfg))
    for finding in findings:
        pair = finding.pair
        if pair is not None and pair.complete and pair.confidence < config.low_confidence:
            finding.context["pairing"] = "low confidence — check the pairing first"
            if finding.severity is Severity.ERROR:
                finding.severity = Severity.WARNING
    findings.sort(key=sort_key)
    return findings, ran, disabled, skipped
````

- [ ] **Step 4: Run the whole suite**

Run: `$PY -m pytest -q`
Expected: `185 passed`

- [ ] **Step 5: Lint**

Run: `$PY -m ruff check .`
Expected: `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: rule registry, run_all, low-confidence downgrade"
```

---

### Task 13: Reports and the command line

Every string that comes from the document is passed through `rich.markup.escape` before it reaches the console. Without that, rich reads `[client name]` as markup and silently removes it; one of the tests below exists to catch exactly that.

**Files:**
- Create: `src/bilingual_lint/report/__init__.py` (empty), `json_out.py`, `markdown.py`, `console.py`, `src/bilingual_lint/cli.py`, `src/bilingual_lint/__main__.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test** `tests/test_cli.py`

````python
import json

from typer.testing import CliRunner

from bilingual_lint.cli import app

from .helpers import write_plain, write_two_column

runner = CliRunner()
CLEAN = [("2.1. The price is USD 150,000.", "2.1. Цена составляет 150 000 долларов США.")]
DEFECT = [("2.1. The price is USD 150,000.", "2.1. Цена составляет 105 000 долларов США.")]


def report(tmp_path, rows, *args):
    source = write_two_column(tmp_path / "doc.docx", rows)
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["check", str(source), "--format", "json",
                                 "--output", str(out), *args])
    return result, json.loads(out.read_text(encoding="utf-8")) if out.exists() else None


def test_clean_document_exits_zero(tmp_path):
    result, data = report(tmp_path, CLEAN)
    assert result.exit_code == 0, result.output
    assert data["summary"]["by_severity"].get("error") is None
    assert data["source"] == {"paths": [str(tmp_path / "doc.docx")], "mode": "two-column",
                              "lang_a": "en", "lang_b": "ru", "pairs": 1, "unpaired": 0}


def test_defect_exits_one_and_is_reported(tmp_path):
    result, data = report(tmp_path, DEFECT)
    assert result.exit_code == 1
    (finding,) = [f for f in data["findings"] if f["rule_id"] == "BI002"]
    assert finding["severity"] == "error" and finding["pair_no"] == 1
    assert finding["text_a"] == DEFECT[0][0] and finding["text_b"] == DEFECT[0][1]
    assert finding["location_a"] == "table 1, row 1"


def test_rules_filter_and_fail_on(tmp_path):
    result, data = report(tmp_path, DEFECT, "--rules", "BI010")
    assert result.exit_code == 0
    assert data["rules"]["ran"] == ["BI010"]
    assert "BI002" in data["rules"]["disabled"]
    warning_only = [("5.2. See clause 3.1.", "5.2. См. п. 3.4.")]
    assert report(tmp_path, warning_only)[0].exit_code == 0
    assert report(tmp_path, warning_only, "--fail-on", "warning")[0].exit_code == 1


def test_two_files_mode(tmp_path):
    en = write_plain(tmp_path / "en.docx", [a for a, _ in DEFECT])
    ru = write_plain(tmp_path / "ru.docx", [b for _, b in DEFECT])
    out = tmp_path / "r.json"
    result = runner.invoke(app, ["check", str(en), str(ru), "--format", "json",
                                 "--output", str(out)])
    assert result.exit_code == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source"]["mode"] == "two-files"
    assert data["summary"]["by_rule"]["BI002"] == 1


def test_language_pair_without_wordlists_runs_neutral_rules_only(tmp_path):
    rows = [("The price is 1,500 EUR.", "El precio es de 1.700 EUR.")]
    result, data = report(tmp_path, rows, "--langs", "en,es")
    assert result.exit_code == 1
    assert data["summary"]["by_rule"] == {"BI002": 1}
    assert data["rules"]["skipped"] == ["BI004", "BI005", "BI008", "BI010", "BI011"]


def test_glossary_option(tmp_path):
    glossary = tmp_path / "glossary.yaml"
    glossary.write_text("- {en: Goods, ru: Товар}\n", encoding="utf-8")
    rows = [("The Goods are delivered.", "Продукция поставляется.")]
    result, data = report(tmp_path, rows, "--glossary", str(glossary),
                          "--fail-on", "warning")
    assert result.exit_code == 1 and data["summary"]["by_rule"]["BI008"] == 1


def test_usage_errors_exit_two(tmp_path):
    source = write_two_column(tmp_path / "doc.docx", CLEAN)
    cases = [
        ["check", str(tmp_path / "missing.docx")],
        ["check", str(source), "--format", "xml"],
        ["check", str(source), "--fail-on", "info"],
        ["check", str(source), "--rules", "BI999"],
        ["check", str(source), "--langs", "english"],
        ["check", str(source), "--output", str(tmp_path / "x.txt")],
        ["check", str(source), str(source), str(source)],
        ["check", str(source), "--config", str(tmp_path / "none.yaml")],
    ]
    for args in cases:
        result = runner.invoke(app, args)
        assert result.exit_code == 2, (args, result.output)


def test_console_output_keeps_square_brackets(tmp_path):
    rows = [("Pay 5 units to [client name].", "Оплатить 6 единиц [имя клиента].")]
    source = write_two_column(tmp_path / "doc.docx", rows)
    result = runner.invoke(app, ["check", str(source)])
    assert result.exit_code == 1
    assert "[client name]" in result.output and "BI001" in result.output


def test_markdown_report(tmp_path):
    source = write_two_column(tmp_path / "doc.docx", DEFECT)
    result = runner.invoke(app, ["check", str(source), "--format", "md"])
    assert result.exit_code == 1
    assert "## BI002 · error · pair 1" in result.output
    assert "| en (table 1, row 1) | ru (table 1, row 1) |" in result.output


def test_version_rules_and_init(tmp_path, monkeypatch):
    assert runner.invoke(app, ["--version"]).output.startswith("bilingual-lint ")
    listing = runner.invoke(app, ["rules"]).output
    assert all(f"BI{n:03d}" in listing for n in range(12))
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert (tmp_path / ".bilingual-lint.yaml").is_file()
    assert runner.invoke(app, ["init"]).exit_code == 2
    source = write_two_column(tmp_path / "doc.docx", CLEAN)
    assert runner.invoke(app, ["check", str(source)]).exit_code == 0
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/test_cli.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.cli'`

- [ ] **Step 3: Create the empty `src/bilingual_lint/report/__init__.py` and `src/bilingual_lint/report/json_out.py`**

````python
from __future__ import annotations

import json

from .. import __version__
from ..models import Document, Finding


def _finding_dict(finding: Finding) -> dict:
    pair = finding.pair
    a = pair.a if pair else None
    b = pair.b if pair else None
    return {
        "rule_id": finding.rule_id,
        "severity": finding.severity.value,
        "message": finding.message,
        "pair_no": pair.pair_no if pair else None,
        "confidence": pair.confidence if pair else None,
        "location_a": a.location if a else None,
        "location_b": b.location if b else None,
        "text_a": a.text if a else None,
        "text_b": b.text if b else None,
        "context": finding.context,
    }


def build_report(doc: Document, findings: list, ran: list, disabled: list,
                 skipped: list, llm_status: dict | None = None) -> dict:
    by_severity: dict = {}
    by_rule: dict = {}
    for finding in findings:
        by_severity[finding.severity.value] = by_severity.get(finding.severity.value, 0) + 1
        by_rule[finding.rule_id] = by_rule.get(finding.rule_id, 0) + 1
    return {
        "tool": "bilingual-lint",
        "version": __version__,
        "source": {
            "paths": [str(path) for path in doc.source_paths],
            "mode": doc.mode,
            "lang_a": doc.lang_a,
            "lang_b": doc.lang_b,
            "pairs": len(doc.pairs),
            "unpaired": sum(1 for pair in doc.pairs if pair.a is None or pair.b is None),
        },
        "summary": {"total": len(findings), "by_severity": by_severity,
                    "by_rule": by_rule},
        "rules": {"ran": ran, "disabled": disabled, "skipped": skipped},
        "findings": [_finding_dict(finding) for finding in findings],
        "llm_pass": llm_status or {"requested": False},
    }


def to_json(doc: Document, findings: list, ran: list, disabled: list, skipped: list,
            llm_status: dict | None = None) -> str:
    return json.dumps(build_report(doc, findings, ran, disabled, skipped, llm_status),
                      indent=2, ensure_ascii=False)
````

- [ ] **Step 4: Create `src/bilingual_lint/report/markdown.py`**

````python
from __future__ import annotations

from ..models import Document
from .json_out import build_report


def _cell(text: str | None) -> str:
    if not text:
        return "—"
    return text.replace("|", "\\|").replace("\n", "<br>")


def to_markdown(doc: Document, findings: list, ran: list, disabled: list,
                skipped: list, llm_status: dict | None = None) -> str:
    report = build_report(doc, findings, ran, disabled, skipped, llm_status)
    source, summary = report["source"], report["summary"]
    names = ", ".join(f"`{path}`" for path in source["paths"])
    lines = [
        "# bilingual-lint report",
        "",
        f"- Source: {names}",
        f"- Mode: {source['mode']}, {source['lang_a']} / {source['lang_b']}",
        f"- Pairs checked: {source['pairs']} ({source['unpaired']} without a counterpart)",
        f"- Findings: {summary['total']}"
        + "".join(f", {count} {name}" for name, count in summary["by_severity"].items()),
    ]
    if skipped:
        lines.append(f"- Not run for this language pair: {', '.join(skipped)}")
    if disabled:
        lines.append(f"- Disabled: {', '.join(disabled)}")
    llm = report["llm_pass"]
    if llm.get("requested"):
        lines.append(f"- Model pass: {llm['model']}, {llm['completed']} pair(s) reviewed, "
                     f"{llm['failed']} failed")
    lines.append("")
    if not report["findings"]:
        lines.append("No findings.")
    for item in report["findings"]:
        where = f"pair {item['pair_no']}" if item["pair_no"] else "document"
        lines.append(f"## {item['rule_id']} · {item['severity']} · {where}")
        lines.append("")
        lines.append(item["message"])
        if item["context"].get("pairing"):
            lines.append("")
            lines.append(f"_Pairing: {item['context']['pairing']}_")
        if item["pair_no"]:
            lines += [
                "",
                f"| {source['lang_a']} ({_cell(item['location_a'])}) "
                f"| {source['lang_b']} ({_cell(item['location_b'])}) |",
                "|---|---|",
                f"| {_cell(item['text_a'])} | {_cell(item['text_b'])} |",
            ]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
````

- [ ] **Step 5: Create `src/bilingual_lint/report/console.py`**

````python
from __future__ import annotations

from rich.console import Console
from rich.markup import escape

from ..models import Document

STYLES = {"error": "bold red", "warning": "yellow", "info": "cyan"}
PREVIEW = 160


def _preview(text: str | None) -> str:
    if not text:
        return "—"
    flat = " ".join(text.split())
    return flat if len(flat) <= PREVIEW else flat[:PREVIEW - 1] + "…"


def render_console(doc: Document, findings: list, ran: list, disabled: list,
                   skipped: list, llm_status: dict | None = None,
                   console: Console | None = None) -> None:
    """Every string that comes from the document goes through escape():
    rich would otherwise read '[client name]' as markup and swallow it."""
    console = console or Console()
    names = ", ".join(str(path) for path in doc.source_paths)
    console.print(f"[bold]bilingual-lint[/bold] — {escape(names)}")
    console.print(f"mode={doc.mode} languages={escape(doc.lang_a)}/{escape(doc.lang_b)} "
                  f"pairs={len(doc.pairs)}")
    if skipped:
        console.print(f"not run for this language pair: {', '.join(skipped)}")
    console.print()
    for finding in findings:
        pair = finding.pair
        where = f"pair {pair.pair_no}" if pair else "document"
        style = STYLES[finding.severity.value]
        console.print(f"[{style}]{finding.severity.value:<7}[/{style}] "
                      f"{finding.rule_id}  {where}  {escape(finding.message)}")
        if finding.context.get("pairing"):
            console.print(f"         {escape(finding.context['pairing'])}", style="dim")
        if pair:
            a = pair.a.text if pair.a else None
            b = pair.b.text if pair.b else None
            console.print(f"         {escape(doc.lang_a)}: {escape(_preview(a))}", style="dim")
            console.print(f"         {escape(doc.lang_b)}: {escape(_preview(b))}", style="dim")
    counts: dict = {}
    for finding in findings:
        counts[finding.severity.value] = counts.get(finding.severity.value, 0) + 1
    summary = ", ".join(f"{count} {name}" for name, count in counts.items()) or "no findings"
    console.print()
    console.print(f"[bold]{summary}[/bold]")
    if llm_status and llm_status.get("requested"):
        console.print(f"model pass: {escape(str(llm_status['model']))}, "
                      f"{llm_status['completed']} reviewed, {llm_status['failed']} failed")
````

- [ ] **Step 6: Create `src/bilingual_lint/cli.py`**

````python
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .config import RULE_DEFAULTS, Config, ConfigError, load_glossary, parse_langs
from .loaders import LoaderError, load
from .models import Severity
from .report.console import render_console
from .report.json_out import to_json
from .report.markdown import to_markdown
from .rules import ALL_RULES, run_all, sort_key
from .segment import refine

app = typer.Typer(add_completion=False,
                  help="A linter for bilingual legal documents.")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"bilingual-lint {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """bilingual-lint: find where two language versions of a contract disagree."""


def _fail(message: str) -> typer.Exit:
    typer.secho(f"error: {message}", err=True, fg=typer.colors.RED)
    return typer.Exit(2)


@app.command()
def check(
    files: list[Path] = typer.Argument(
        ..., help="One two-column bilingual DOCX, or two DOCX files (source, translation)"),
    langs: Optional[str] = typer.Option(
        None, "--langs", help="Two language codes, e.g. en,ru (left,right or first,second)"),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Path to .bilingual-lint.yaml"),
    glossary: Optional[Path] = typer.Option(
        None, "--glossary", help="YAML glossary of term pairs"),
    output_format: str = typer.Option("console", "--format", help="console | json | md"),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Write the report to a file (json/md only)"),
    fail_on: Optional[str] = typer.Option(
        None, "--fail-on", help="error | warning (default from config)"),
    rules_filter: Optional[str] = typer.Option(
        None, "--rules", help="Comma-separated rule IDs to run (e.g. BI001,BI010)"),
    llm: Optional[str] = typer.Option(
        None, "--llm",
        help='Run the model pass: a litellm model string, or "default" for the '
             "configured llm.model. Sends flagged text to that model's provider."),
    llm_gate: bool = typer.Option(
        False, "--llm-gate", help="Treat a model answer of 'differs' as an error"),
) -> None:
    """Lint a bilingual document and report findings."""
    if output_format not in ("console", "json", "md"):
        raise _fail(f"unknown --format {output_format!r} (use console, json or md)")
    if fail_on not in (None, "error", "warning"):
        raise _fail("--fail-on must be error or warning")
    if output_format == "console" and output:
        raise _fail("--output requires --format json or --format md")
    if len(files) > 2:
        raise _fail("pass one bilingual DOCX, or two DOCX files")
    try:
        config = Config.load(config_path)
        if langs:
            config.langs = parse_langs(langs)
        if glossary:
            config.glossary = load_glossary(glossary)
    except ConfigError as exc:
        raise _fail(str(exc)) from exc
    only: Optional[set] = None
    if rules_filter:
        only = {r.strip().upper() for r in rules_filter.split(",") if r.strip()}
        unknown = only - set(RULE_DEFAULTS)
        if unknown:
            raise _fail(f"unknown rule ids: {', '.join(sorted(unknown))}")
    try:
        doc = refine(load(files, config.langs))
    except LoaderError as exc:
        raise _fail(str(exc)) from exc

    findings, ran, disabled, skipped = run_all(doc, config, only=only)

    llm_status: dict = {"requested": False}
    if llm is not None:
        from .llm.reviewer import LlmUnavailable, run_llm_pass

        model = config.llm["model"] if llm in ("default", "") else llm
        try:
            llm_status = run_llm_pass(doc, findings, config.llm, model, gate=llm_gate)
        except LlmUnavailable as exc:
            raise _fail(str(exc)) from exc
        findings.sort(key=sort_key)

    if output_format == "json":
        text = to_json(doc, findings, ran, disabled, skipped, llm_status)
    elif output_format == "md":
        text = to_markdown(doc, findings, ran, disabled, skipped, llm_status)
    else:
        text = None
    if text is not None and output:
        output.write_text(text, encoding="utf-8")
    elif text is not None:
        typer.echo(text)
    else:
        render_console(doc, findings, ran, disabled, skipped, llm_status)

    threshold = Severity(fail_on or config.fail_on).rank
    if any(f.severity.rank >= threshold for f in findings):
        raise typer.Exit(1)


@app.command("rules")
def rules_command() -> None:
    """List all rules with their default severities."""
    typer.echo("BI000  file-structure       info     any    notes about the file: "
               "tracked changes, comments, text outside the bilingual table")
    for rule in ALL_RULES:
        scope = "en/ru" if rule.needs_wordlists else "any"
        typer.echo(f"{rule.id}  {rule.name:<20} {rule.default_severity.value:<8} "
                   f"{scope:<6} {rule.description}")


STARTER_CONFIG = """\
# bilingual-lint configuration. Every key is optional; delete what you don't need.

# langs: en,ru          # needed only when the two languages share a script
fail_on: error          # exit 1 at or above this severity: error | warning
# glossary: glossary.yaml   # list of term pairs: - {en: Buyer, ru: Покупатель}
low_confidence: 0.5     # two-file mode: below this, findings say "check pairing first"

rules:
  # BI001:
  #   strict_separators: true   # read 1,000 by each language's own convention only
  # BI011:
  #   enabled: false

llm:
  model: anthropic/claude-sonnet-5
  max_pairs: 50
  timeout_seconds: 60
"""


@app.command()
def init() -> None:
    """Write a starter .bilingual-lint.yaml into the current directory."""
    target = Path(".bilingual-lint.yaml")
    if target.exists():
        raise _fail(f"{target} already exists — not overwriting")
    target.write_text(STARTER_CONFIG, encoding="utf-8")
    typer.echo(f"wrote {target}")
````

- [ ] **Step 7: Create `src/bilingual_lint/__main__.py`**

````python
from .cli import app

app()
````

- [ ] **Step 8: Run the test**

Run: `$PY -m pytest tests/test_cli.py -q`
Expected: `10 passed`

- [ ] **Step 9: Prove the guard.** In `console.py`, replace `escape(_preview(a))` with `_preview(a)`. Run again.

Expected: `test_console_output_keeps_square_brackets` fails, `[client name]` is missing from the output. Restore; expected `10 passed`.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: console, JSON and Markdown reports; CLI"
```

---

### Task 14: Optional model pass

The model sees only pairs that the rules flagged but could not settle: BI011 findings and low-confidence pairs. A failed call is counted and reported, never hidden. Tests use a fake `litellm` module; no network call is made.

**Files:**
- Create: `src/bilingual_lint/llm/__init__.py` (empty), `src/bilingual_lint/llm/reviewer.py`
- Test: `tests/test_llm.py`

- [ ] **Step 1: Write the failing test** `tests/test_llm.py`

````python
import sys
import types

import pytest

from bilingual_lint.config import LLM_DEFAULTS, Config
from bilingual_lint.llm.reviewer import LlmUnavailable, run_llm_pass, unsettled_pairs
from bilingual_lint.models import Severity
from bilingual_lint.rules import run_all

from .helpers import make_doc

ROWS = [
    ("The Seller may not assign its rights.", "Продавец вправе уступать права."),
    ("Pay 5 units.", "Оплатить 6 единиц."),
]


def fake_litellm(monkeypatch, answers):
    calls = []

    def completion(model, messages, timeout):
        calls.append(messages[1]["content"])
        content = answers[len(calls) - 1]
        if isinstance(content, Exception):
            raise content
        message = types.SimpleNamespace(content=content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])

    monkeypatch.setitem(sys.modules, "litellm", types.SimpleNamespace(completion=completion))
    return calls


def prepared():
    doc = make_doc(ROWS)
    findings, *_ = run_all(doc, Config())
    return doc, findings


def test_only_unsettled_pairs_are_sent(monkeypatch):
    doc, findings = prepared()
    assert [p.pair_no for p in unsettled_pairs(findings)] == [1]
    calls = fake_litellm(monkeypatch, ['{"label": "differs", "reason": "negation lost"}'])
    status = run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model")
    assert len(calls) == 1 and "may not assign" in calls[0] and "5 units" not in calls[0]
    assert status == {"requested": True, "model": "test/model", "completed": 1,
                      "failed": 0, "capped": False}
    (suggestion,) = [f for f in findings if f.rule_id == "LLM"]
    assert suggestion.severity is Severity.INFO
    assert suggestion.message == "model suggestion: meaning differs — negation lost"
    bi011 = next(f for f in findings if f.rule_id == "BI011")
    assert bi011.context["llm"] == {"label": "differs", "reason": "negation lost"}


def test_gate_turns_differs_into_an_error(monkeypatch):
    doc, findings = prepared()
    fake_litellm(monkeypatch, ['{"label": "differs", "reason": "x"}'])
    run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model", gate=True)
    assert next(f for f in findings if f.rule_id == "LLM").severity is Severity.ERROR


def test_same_adds_no_finding_and_unclear_is_kept(monkeypatch):
    doc, findings = prepared()
    fake_litellm(monkeypatch, ['Sure: {"label": "same", "reason": "equivalent"}'])
    run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model")
    assert not [f for f in findings if f.rule_id == "LLM"]
    doc, findings = prepared()
    fake_litellm(monkeypatch, ['{"label": "unclear", "reason": "cannot tell"}'])
    run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model", gate=True)
    assert next(f for f in findings if f.rule_id == "LLM").severity is Severity.INFO


def test_failures_are_counted_not_hidden(monkeypatch):
    for bad in (RuntimeError("boom"), "no json here", '{"label": "maybe"}'):
        doc, findings = prepared()
        fake_litellm(monkeypatch, [bad])
        status = run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model")
        assert (status["completed"], status["failed"]) == (0, 1)
        assert not [f for f in findings if f.rule_id == "LLM"]


def test_cap_is_reported(monkeypatch):
    doc, findings = prepared()
    calls = fake_litellm(monkeypatch, [])
    status = run_llm_pass(doc, findings, dict(LLM_DEFAULTS, max_pairs=0), "test/model")
    assert calls == [] and status["capped"] is True


def test_missing_extra_gives_a_clear_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "litellm", None)
    doc, findings = prepared()
    with pytest.raises(LlmUnavailable, match=r"bilingual-lint\[llm\]"):
        run_llm_pass(doc, findings, dict(LLM_DEFAULTS), "test/model")
````

- [ ] **Step 2: Run it and watch it fail**

Run: `$PY -m pytest tests/test_llm.py -q`
Expected: `ModuleNotFoundError: No module named 'bilingual_lint.llm'`

- [ ] **Step 3: Create the empty `src/bilingual_lint/llm/__init__.py` and `src/bilingual_lint/llm/reviewer.py`**

````python
"""Optional model pass. It only sees pairs the rules could not settle, and its
answers are marked as suggestions."""
from __future__ import annotations

import json
import re

from ..models import Document, Finding, Severity

SYSTEM_PROMPT = """\
You compare two versions of the same contract clause written in two languages.
Decide whether they say the same thing in legal effect: the same obligations,
permissions, prohibitions, conditions, parties and scope. Ignore style and
word order. Do not guess: if you cannot tell, say so.
Respond with ONLY a JSON object:
{"label": "same" | "differs" | "unclear", "reason": "<one sentence>"}"""
LABELS = {"same", "differs", "unclear"}
UNSETTLED_RULES = {"BI011"}


class LlmUnavailable(Exception):
    pass


def _parse_payload(content: str) -> dict:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in response")
    payload = json.loads(match.group(0))
    if payload.get("label") not in LABELS:
        raise ValueError(f"unknown label {payload.get('label')!r}")
    return payload


def unsettled_pairs(findings: list) -> list:
    """Pairs the rules flagged but could not settle, in document order."""
    pairs: dict = {}
    for finding in findings:
        pair = finding.pair
        if pair is None or not pair.complete:
            continue
        if finding.rule_id in UNSETTLED_RULES or finding.context.get("pairing"):
            pairs.setdefault(pair.pair_no, pair)
    return [pairs[number] for number in sorted(pairs)]


def run_llm_pass(doc: Document, findings: list, llm_cfg: dict, model: str,
                 gate: bool = False) -> dict:
    """Review unsettled pairs. Appends 'LLM' findings in place and returns the
    status dict for the report. With gate=True a 'differs' answer is an error."""
    try:
        import litellm
    except ImportError as exc:
        raise LlmUnavailable(
            'the model pass requires the extra: pip install "bilingual-lint[llm]"') from exc

    pairs = unsettled_pairs(findings)
    capped = len(pairs) > llm_cfg["max_pairs"]
    pairs = pairs[: llm_cfg["max_pairs"]]
    completed = failed = 0
    for pair in pairs:
        try:
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",
                     "content": f"Version in {doc.lang_a}:\n{pair.a.text}\n\n"
                                f"Version in {doc.lang_b}:\n{pair.b.text}"},
                ],
                timeout=llm_cfg["timeout_seconds"],
            )
            payload = _parse_payload(response.choices[0].message.content)
        except Exception:
            failed += 1
            continue
        completed += 1
        label = payload["label"]
        reason = str(payload.get("reason", "")).strip()
        for finding in findings:
            if finding.pair is pair:
                finding.context["llm"] = {"label": label, "reason": reason}
        if label != "same":
            severity = Severity.ERROR if gate and label == "differs" else Severity.INFO
            findings.append(Finding(
                "LLM", severity,
                f"model suggestion: meaning {label} — {reason}", pair,
                {"model": model, "label": label}))
    return {"requested": True, "model": model, "completed": completed,
            "failed": failed, "capped": capped}
````

- [ ] **Step 4: Run the test, then the whole suite**

Run: `$PY -m pytest -q`
Expected: `201 passed`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: optional model pass for unsettled pairs"
```

---

### Task 15: Example documents and golden reports

The sample contract is invented. Each planted defect is listed next to its row together with the rule it must trigger, so the expected report is known before the tool runs.

**Files:**
- Create: `examples/build_examples.py`, generated `examples/sample_en_ru.docx`, `clean_en_ru.docx`, `sample_en.docx`, `sample_ru.docx`, `tests/golden/sample_en_ru.json`, `tests/golden/sample_en_ru.md`
- Test: `tests/test_examples.py`

- [ ] **Step 1: Create `examples/build_examples.py`**

````python
"""Rebuild the example documents: python examples/build_examples.py

The sample contract is invented. Every defect in it is planted on purpose and
listed next to the row, so the expected report is known in advance."""
from __future__ import annotations

from pathlib import Path

from docx import Document as new_docx

HERE = Path(__file__).resolve().parent

# (English, Russian with the defect, Russian without it, rule the defect triggers)
ROWS = [
    ("SUPPLY AGREEMENT No. 15", "ДОГОВОР ПОСТАВКИ № 15", None, None),
    ("Moscow, 12 March 2025", "г. Москва, 21 марта 2025 г.",
     "г. Москва, 12 марта 2025 г.", "BI003"),
    ('Alpha LLC (the "Seller") and Beta GmbH (the "Buyer") have agreed as follows.',
     "ООО «Альфа» (далее – «Продавец») и Beta GmbH (далее – «Покупатель») "
     "договорились о нижеследующем.", None, None),
    ("2.1. The price of the goods is USD 150,000 (one hundred and fifty thousand "
     "US dollars).",
     "2.1. Цена товара составляет 105 000 (сто пять тысяч) долларов США.",
     "2.1. Цена товара составляет 150 000 (сто пятьдесят тысяч) долларов США.", "BI002"),
    ("2.2. The Buyer shall pay for the goods within 10 (ten) business days.",
     "2.2. Покупатель обязан оплатить товар в течение 10 (десяти) дней.",
     "2.2. Покупатель обязан оплатить товар в течение 10 (десяти) рабочих дней.",
     "BI005"),
    ("3.1. The penalty is 0.1% of the price per day of delay, as provided in clause 2.2.",
     "3.1. Неустойка составляет 0,1% от цены за каждый день просрочки согласно п. 2.1.",
     "3.1. Неустойка составляет 0,1% от цены за каждый день просрочки согласно п. 2.2.",
     "BI006"),
    ("3.2. The Seller may not assign its rights under this Agreement.",
     "3.2. Продавец вправе уступать свои права по Договору.",
     "3.2. Продавец не вправе уступать свои права по Договору.", "BI011"),
    ("4.1. Bank details: IBAN DE89 3704 0044 0532 0130 00, e-mail: sales@alpha.example",
     "4.1. Банковские реквизиты: IBAN DE89 3704 0044 0532 0130 01, "
     "эл. почта: sales@alpha.example",
     "4.1. Банковские реквизиты: IBAN DE89 3704 0044 0532 0130 00, "
     "эл. почта: sales@alpha.example", "BI009"),
    ("5.1. In case of discrepancy between the English and Russian texts, "
     "the English text shall prevail.",
     "5.1. В случае расхождений между английским и русским текстами "
     "преимущество имеет текст на русском языке.",
     "5.1. В случае расхождений между английским и русским текстами "
     "преимущество имеет текст на английском языке.", "BI010"),
    ("5.2. This Agreement is made in 2 (two) copies.",
     "5.2. Договор составлен в 3 (двух) экземплярах.",
     "5.2. Договор составлен в 2 (двух) экземплярах.", "BI004"),
    ("6.1. The Buyer shall inspect the goods on delivery.",
     "6.1. Заказчик обязан осмотреть товар при поставке.",
     "6.1. Покупатель обязан осмотреть товар при поставке.", "BI008"),
    ("7. Signatures of the parties", "", "7. Подписи сторон", "BI007"),
    ("This page is intentionally left blank for signatures.",
     "This page is intentionally left blank for signatures.",
     "Эта страница намеренно оставлена пустой для подписей.", "BI007"),
]

SAMPLE = [(en, ru) for en, ru, _, _ in ROWS]
CLEAN = [(en, fixed if fixed is not None else ru) for en, ru, fixed, _ in ROWS]
PLANTED = [rule for _, _, _, rule in ROWS if rule]


def write_two_column(path: Path, rows: list) -> None:
    document = new_docx()
    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    for left, right in rows:
        cells = table.add_row().cells
        cells[0].text = left
        cells[1].text = right
    document.save(str(path))


def write_plain(path: Path, paragraphs: list) -> None:
    document = new_docx()
    for text in paragraphs:
        if text:
            document.add_paragraph(text)
    document.save(str(path))


def main() -> None:
    write_two_column(HERE / "sample_en_ru.docx", SAMPLE)
    write_two_column(HERE / "clean_en_ru.docx", CLEAN)
    write_plain(HERE / "sample_en.docx", [en for en, _ in SAMPLE])
    write_plain(HERE / "sample_ru.docx", [ru for _, ru in SAMPLE])
    print(f"wrote 4 example files to {HERE}")


if __name__ == "__main__":
    main()
````

- [ ] **Step 2: Build the examples**

Run: `$PY examples/build_examples.py`
Expected: `wrote 4 example files to .../examples`

- [ ] **Step 3: Write the test** `tests/test_examples.py`

````python
"""The bundled examples: every planted defect is found, the clean file is clean."""
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

from typer.testing import CliRunner

from bilingual_lint.cli import app

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

spec = importlib.util.spec_from_file_location("build_examples", EXAMPLES / "build_examples.py")
build_examples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_examples)


def norm(text: str) -> str:
    text = text.replace("\r\n", "\n").strip()
    text = re.sub(r'"version": "[^"]+"', '"version": "X"', text)
    # Paths vary by invocation directory and OS separator.
    return re.sub(r'"paths": \[[^\]]*\]', '"paths": "X"', text, flags=re.DOTALL)


def run(tmp_path, *files, fmt="json"):
    out = tmp_path / f"report.{fmt}"
    result = runner.invoke(app, ["check", *[str(EXAMPLES / f) for f in files],
                                 "--format", fmt, "--output", str(out)])
    return result, out.read_text(encoding="utf-8")


def test_committed_examples_match_the_builder(tmp_path):
    from bilingual_lint.loaders import load
    doc = load([EXAMPLES / "sample_en_ru.docx"])
    assert [(p.a.text, p.b.text) for p in doc.pairs] == build_examples.SAMPLE


def test_clean_example_has_no_findings_that_fail(tmp_path):
    result, text = run(tmp_path, "clean_en_ru.docx")
    assert result.exit_code == 0, text
    assert json.loads(text)["summary"]["total"] == 0


def test_every_planted_defect_is_found(tmp_path):
    result, text = run(tmp_path, "sample_en_ru.docx")
    assert result.exit_code == 1
    by_rule = json.loads(text)["summary"]["by_rule"]
    for rule, count in Counter(build_examples.PLANTED).items():
        assert by_rule.get(rule, 0) >= count, (rule, by_rule)
    # the '3 (двух)' row also shows up as a plain number difference
    assert by_rule.get("BI001") == 1
    assert set(by_rule) == set(build_examples.PLANTED) | {"BI001"}


def test_sample_json_golden(tmp_path):
    _, text = run(tmp_path, "sample_en_ru.docx")
    golden = (ROOT / "tests" / "golden" / "sample_en_ru.json").read_text(encoding="utf-8")
    assert norm(text) == norm(golden)


def test_sample_md_golden(tmp_path):
    _, text = run(tmp_path, "sample_en_ru.docx", fmt="md")
    golden = (ROOT / "tests" / "golden" / "sample_en_ru.md").read_text(encoding="utf-8")
    assert re.sub(r"Source: .*", "Source: X", text.strip()) == \
        re.sub(r"Source: .*", "Source: X", golden.replace("\r\n", "\n").strip())


def test_two_file_example_finds_the_same_fact_defects(tmp_path):
    result, text = run(tmp_path, "sample_en.docx", "sample_ru.docx")
    assert result.exit_code == 1
    data = json.loads(text)
    assert data["source"]["mode"] == "two-files"
    for rule in ("BI002", "BI003", "BI004", "BI005", "BI009", "BI010"):
        assert data["summary"]["by_rule"].get(rule, 0) >= 1, (rule, data["summary"])
    assert data["source"]["unpaired"] == 1  # the heading with no Russian counterpart
````

- [ ] **Step 4: Run it; the two golden tests fail**

Run: `$PY -m pytest tests/test_examples.py -q`
Expected: `2 failed, 4 passed`. The failures are `test_sample_json_golden` and `test_sample_md_golden` with `FileNotFoundError`. The other four must pass: they check the planted defects by rule, without a golden file.

- [ ] **Step 5: Read the report before freezing it**

```bash
mkdir -p tests/golden
$PY -m bilingual_lint check examples/sample_en_ru.docx --format md --output tests/golden/sample_en_ru.md
$PY -m bilingual_lint check examples/sample_en_ru.docx --format json --output tests/golden/sample_en_ru.json
```

Open `tests/golden/sample_en_ru.md` and check it against this list, one finding per line, nothing else:

| Pair | Rule | Severity | What it says |
|---|---|---|---|
| 2 | BI003 | error | dates differ, 12 March 2025 against 21 марта 2025 |
| 4 | BI002 | error | amounts differ, 150,000 against 105 000 |
| 5 | BI005 | error | business days against calendar days |
| 8 | BI009 | error | the two IBANs differ in the last digit |
| 9 | BI010 | error | en side says en prevails, ru side says ru |
| 10 | BI001 | error | ru only: 3 |
| 10 | BI004 | error | 3 against "двух" on the ru side |
| 12 | BI007 | error | empty on the ru side |
| 6 | BI006 | warning | cross-references 2.2 against 2.1 |
| 11 | BI008 | warning | "Buyer" used, "Покупатель" not on the ru side |
| 13 | BI007 | warning | ru side does not look like ru |
| 7 | BI011 | info | negation on the en side only |

Twelve findings: 8 errors, 3 warnings, 1 info. If the file shows anything else, stop and find out why before committing a golden file. A golden file frozen from wrong output protects the wrong behaviour.

- [ ] **Step 6: Run the tests**

Run: `$PY -m pytest tests/test_examples.py -q`
Expected: `6 passed`

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: example documents and golden reports"
```

---

### Task 16: Guard test, CI and documentation

**Files:**
- Create: `tests/test_no_internal_terms.py`, `.github/workflows/ci.yml`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`

- [ ] **Step 1: Create `tests/test_no_internal_terms.py`**

The term list is built by concatenation so that no fragment of this file, of the plan or of the spec ever contains a full term.

````python
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
````

- [ ] **Step 2: Run it**

Run: `$PY -m pytest tests/test_no_internal_terms.py -q`
Expected: `1 passed`. It reads `git ls-files`, so it only sees committed and staged files; run `git add -A` first.

- [ ] **Step 3: Prove the guard.** Create a tracked file `scratch.txt` containing the second forbidden term (join the two halves of the second tuple), `git add scratch.txt`, and run the test.

Expected: fails, naming `scratch.txt`. Then `git rm -f scratch.txt`; expected `1 passed`.

- [ ] **Step 4: Create `.github/workflows/ci.yml`**

````yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python-version: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest -q
````

- [ ] **Step 5: Create `CHANGELOG.md`**

````markdown
# Changelog

## 0.1.0 — unreleased

First version.

- Input: two-column bilingual DOCX, or two separate DOCX files paired by
  clause numbers, digit signatures and length.
- Twelve rules, BI000 to BI011: numbers, amounts and currency, dates,
  digits against words, durations and day types, clause references, missing or
  untranslated text, defined terms and glossary, identifiers, the
  prevailing-language clause, obligation and negation cues.
- Language-neutral rules for any pair; word-based rules for English and Russian.
- Console, JSON and Markdown reports; exit codes for use as a pipeline gate.
- Optional model pass (`--llm`) for pairs the rules cannot settle. Off by default.
````

- [ ] **Step 6: Create `CONTRIBUTING.md`**

````markdown
# Contributing

Thanks for taking a look.

## Setup

```
pip install -e ".[dev]"
pytest -q
ruff check .
```

## Ground rules

- **Rules first.** A check that can be done deterministically is done
  deterministically. The model pass is for what rules cannot settle.
- **Every rule has two tests:** a clean case that must stay silent and a defect
  that must be found. A rule that cannot be made to fail is not a rule.
- **No real documents.** Examples and fixtures are invented. Do not add client,
  firm or personal data to the repository, in any form.
- **Say what you could not read.** If the tool cannot determine something, it
  reports that or stays silent. It does not guess.

## Adding a language

Add `src/bilingual_lint/wordlists/<code>.yaml` with the same keys as `en.yaml`.
Entries are regular-expression fragments. The word-based rules pick the language
up automatically once both languages of a pair have a wordlist. Add tests next
to the existing English and Russian ones.

## Adding a rule

One file in `src/bilingual_lint/rules/`, one entry in `ALL_RULES`, one entry in
`RULE_DEFAULTS`, one row in the README table, and tests.
````

- [ ] **Step 7: Replace the stub `README.md`**

````markdown
# bilingual-lint

[![CI](https://github.com/kirillsakhin/bilingual-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/kirillsakhin/bilingual-lint/actions/workflows/ci.yml)

A linter for bilingual legal documents. Give it a contract in two languages and it
reports where the two versions disagree: a different amount, a different date, a
missing paragraph, a clause that makes English prevail on the left and Russian on
the right. Deterministically, offline, the same way every time.

## Why

A bilingual contract is one deal written twice. Every number, date, deadline and
party name has to be the same in both columns, and nobody enjoys checking that by
eye on page 40.

The obvious 2026 answer is "have an LLM compare the two versions". It helps with
meaning, but it is the wrong tool for facts: it can pass a changed digit in one
clause and flag the same thing in another, and two runs disagree with each other.

So bilingual-lint does it the other way around. Rules check the facts: they catch
the same defect every time, need no API key and send nothing anywhere. A model
comes second, optionally, and only for the pairs the rules cannot settle.

It does not judge translation style or quality. It checks what must be identical.

## Install

From a clone of this repository:

```
pip install -e .
```

Python 3.10 or newer. The optional model pass needs `pip install -e ".[llm]"`.

## Quickstart

A two-column bilingual DOCX:

```
bilingual-lint check contract.docx
```

A source file and its translation:

```
bilingual-lint check contract_en.docx contract_ru.docx
```

Against the bundled sample ([`examples/sample_en_ru.docx`](examples/sample_en_ru.docx),
an invented contract with twelve planted defects), `--format md` gives, in part:

```
# bilingual-lint report

- Mode: two-column, en / ru
- Pairs checked: 13 (0 without a counterpart)
- Findings: 12, 8 error, 3 warning, 1 info

## BI002 · error · pair 4

amounts differ — en only: 150,000 · ru only: 105 000

## BI005 · error · pair 5

duration day type differs — business against calendar days (en: 10, ru: 10)

## BI010 · error · pair 9

the two sides disagree on which language prevails — en side: en · ru side: ru

## BI004 · error · pair 10

digits and words disagree on the ru side — 3 against "двух"
```

The clean copy of the same contract ([`examples/clean_en_ru.docx`](examples/clean_en_ru.docx))
produces no findings.

Exit codes: `0` nothing at or above the threshold, `1` findings, `2` the input
could not be read or the command was wrong. That makes it usable as a gate after
a translation step.

## Rules

| Code | Checks | Default | Languages |
|---|---|---|---|
| BI000 | Notes about the file: tracked changes, comments, text outside the bilingual table | info | any |
| BI001 | A number or percentage appears on one side only | error | any |
| BI002 | A money amount or its currency differs | error | any |
| BI003 | A date differs, or agrees only under one day/month reading (`02/03/2025`) | error | any |
| BI004 | Digits and words disagree on the same side: `ten (15)` | error | en, ru |
| BI005 | A time period differs in length, unit or day type (30 days vs 30 business days) | error | en, ru |
| BI006 | A clause number or cross-reference differs | warning | any |
| BI007 | A segment is missing, empty, untranslated or far off in length | error | any |
| BI008 | A defined term or glossary term is rendered inconsistently | warning | en, ru |
| BI009 | A registration number, IBAN, e-mail or URL differs | error | any |
| BI010 | The prevailing-language clause is one-sided or contradicts itself | error | en, ru |
| BI011 | Obligation, permission or negation wording differs (heuristic) | info | en, ru |

"any" rules work for every language pair. The others need a wordlist and currently
ship for English and Russian; for other pairs they are skipped, and the report
says which.

### How numbers are compared

`1,000` is one thousand in English and exactly one in Russian. bilingual-lint does
not guess: an ambiguous number keeps both readings and matches if either agrees
with the other side. Set `strict_separators: true` to read each language by its
own convention only.

A number spelled out on one side (`two copies` / `2 экземпляра`) is not a defect.

## Two separate files

Paragraphs are paired deterministically: first at anchors (clause numbers and
paragraphs with a unique set of digits), then by length between anchors. A
paragraph with no partner becomes a finding. Each pair has a confidence value; for
low-confidence pairs the report says "check the pairing first" and errors are
shown as warnings.

## Options

```
bilingual-lint check FILE [FILE]
  --langs en,es         name the two languages (needed when they share a script)
  --glossary terms.yaml term pairs to enforce:  - {en: Buyer, ru: Покупатель}
  --config FILE         use this config file instead of ./.bilingual-lint.yaml
  --format console|json|md
  --output report.json
  --fail-on error|warning
  --rules BI001,BI010   run only these rules
  --llm MODEL           optional model pass (see below)
  --llm-gate            treat a model answer of "differs" as an error
bilingual-lint rules    list the rules
bilingual-lint init     write a starter .bilingual-lint.yaml
```

## Optional model pass

`--llm` sends only the pairs the rules flagged but could not settle (BI011 and
low-confidence pairs) to a model through [litellm](https://github.com/BerriAI/litellm)
and asks one question: do these two texts say the same thing? Answers are marked
as model suggestions and do not change the exit code unless you pass `--llm-gate`.

**Without `--llm`, no text leaves your machine.** With it, the flagged pairs go to
the provider of the model you chose. Decide whether that is acceptable for the
document in front of you.

## Limits

- DOCX only. No PDF, no scanned documents.
- Headers, footers, footnotes and text boxes anchored outside the body are not read.
- Tracked changes are read as if accepted; the report says when a file has them.
- Word-based rules exist for English and Russian only.
- BI011 is a wordlist heuristic and will produce false flags; it is `info` for that reason.
- In two-file mode a short missing paragraph next to a long one can be absorbed
  into its neighbour instead of being reported as missing.
- No accuracy figures are published yet. A benchmark on public bilingual texts
  with planted defects is the next milestone; until then, treat the tool as a
  second pair of eyes, not as proof that a document is clean.

## Development

```
pip install -e ".[dev]"
pytest -q
ruff check .
python examples/build_examples.py   # rebuild the example documents
```

## Licence

MIT. See [LICENSE](LICENSE).
````

- [ ] **Step 8: Check every claim in the README against reality**

```bash
$PY -m bilingual_lint check examples/sample_en_ru.docx --format md
$PY -m bilingual_lint check examples/clean_en_ru.docx; echo "exit=$?"
$PY -m bilingual_lint rules
$PY -m bilingual_lint check --help
```

Compare, line by line: the report excerpt in the Quickstart, the finding counts, `exit=0` for the clean file, the rule table against `rules`, the option list against `--help`. Fix the README wherever it differs from the output. Do not fix the output to match the README.

- [ ] **Step 9: Full check**

```bash
git add -A
$PY -m pytest -q
$PY -m ruff check .
```

Expected: `208 passed` and `All checks passed!`

- [ ] **Step 10: Commit**

```bash
git commit -m "docs: README, changelog, contributing; CI and confidentiality guard"
```

---

### Task 17: Release checks

Nothing here is published. These checks decide whether v0.1.0 is ready to be published when the owner chooses to.

- [ ] **Step 1: Open every example in Word.** Open `examples/sample_en_ru.docx`, `clean_en_ru.docx`, `sample_en.docx` and `sample_ru.docx` in Microsoft Word.

Pass: each opens with no repair prompt and no error. A repair prompt is a failure, even if the content then looks right. A text or PDF check is not a substitute for this.

- [ ] **Step 2: Run on a document that python-docx did not write.** Create a short two-column bilingual table by hand in Word (five or six rows, one wrong number, one tracked change), save it, and run:

```bash
$PY -m bilingual_lint check path/to/handmade.docx
```

Pass: the wrong number is reported, the tracked-changes note appears, and the text matches what Word shows with all changes accepted. Every test so far used files written by the same library that reads them; this is the first check that does not.

- [ ] **Step 3: Clean install**

```bash
python -m venv /tmp/bl-clean
/tmp/bl-clean/Scripts/python.exe -m pip install .
/tmp/bl-clean/Scripts/bilingual-lint.exe check examples/sample_en_ru.docx; echo "exit=$?"
```

Pass: the report prints and `exit=1`. This proves the wordlist YAML files are inside the built package.

- [ ] **Step 4: Push to a private repository and watch CI.** Only when the owner asks for it. Pass: all eight jobs green (two operating systems, four Python versions). This is the first run on Linux and on Python 3.10 to 3.13.

- [ ] **Step 5: Tag** `v0.1.0` only after steps 1 to 4 pass and the owner approves publication.

---

## What comes after this plan

1. **Benchmark plan** (spec section 9): mutation tool, pinned holdout, clean arm, whole-document model comparison, published recall and false-flag rates. Blocked on confirming the licence terms of the public source texts.
2. PDF input, comments written back into Word, more languages.
