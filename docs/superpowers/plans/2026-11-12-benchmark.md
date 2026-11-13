# Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a reproducible benchmark that measures how many planted defects bilingual-lint catches and how often it flags clean text, on public United Nations EN/RU text and on invented contracts, with a whole-document model review as the comparison.

**Architecture:** A `benchmark/` package at the repository root, outside the installed wheel. A defect-planting tool (`mutate.py`, standard library only, frozen by hash before any rule is tuned) changes one cell of one row; the scorer writes each clean and mutated document to a real DOCX, runs the linter's own loader and rules on it, and counts new findings on the changed row. The UN development set is for tuning; the UN test set is the hold-out, pinned by hash and scored once.

**Tech Stack:** Python 3.10+, pytest, ruff, python-docx (already a dependency), litellm (already the optional `llm` extra) for the comparison arm. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-11-bilingual-lint-design.md`, section 9.

---

## What is already known

All code in this plan was prototyped and run before the plan was written: 65 tests pass and ruff is clean with the repository's settings. Copy the code blocks as they are.

**Data.** `UNv1.0.testsets.tar.gz` from the United Nations Parallel Corpus v1.0 (3,620,708 bytes, SHA-256 `0b4040d723eab132fadc7809a329a4787b338a424ef23bfe3e029d41b7e0153d`). The UN server answers automated downloads with 403, so the file is fetched by hand in a browser from
`https://www.un.org/dgacm/sites/www.un.org.dgacm/files/files/UNCORPUS/UNv1.0.testsets.tar.gz`.
It unpacks to `testsets/devset/` and `testsets/testset/`, each with one UTF-8 file per language (`UNv1.0.devset.en`, `.ru`, ...) and an `.ids` file, 4,000 lines each, LF line endings, one sentence per line, aligned line to line. An ids line looks like `2015/a/69/767 ar:3:1 en:2:1 es:2:1 fr:3:1 ru:2:1 zh:3:1`: the first field is the source document. The sentences are a sample (1 to 12 per source document, about 730 documents per set), not whole documents, so a benchmark document is a block of 40 consecutive lines: 100 documents per set.

**Licence.** The archive's own `DISCLAIMER` file says no restrictions apply beyond the disclaimer: acknowledge the United Nations as the source, cite Ziemski, Junczys-Dowmunt and Pouliquen (LREC 2016), no warranty. The data is not committed to this repository; anyone can fetch the same file and check it against the pinned hash.

**What the UN text can and cannot test.** Counted on the development set: 1,318 of 4,000 English lines carry a number of two or more digits, 312 a written-out date, 105 a paragraph or article reference, 30 a currency, 10 a "shall/may/must not", 1 a "business/working days", none a bank or registration number. There are no defined party names and no prevailing-language clauses. So the UN text carries the digit, date, reference and dropped-paragraph defects and the false-flag measure. Currency, day type, identifier, party and prevailing-language defects are measured on three invented contracts, and those results are reported separately.

**First numbers** (five development documents, 200 pairs, version 0.1.1; a trial, not a result):

| Planted defect | Planted | Caught |
|---|---|---|
| digit | 103 | 103 |
| date | 34 | 34 |
| reference | 16 | 16 |
| negation | 7 | 4 |
| dropped paragraph | 349 | 349 |

Clean text drew 13 error-level findings in 200 pairs, 6.5 per 100 against a target of 3. They fall into three kinds: clock times written differently ("11 a.m." against "11 ч. 00 м.", "12.40" against "12 ч. 40 м."), a year or day that Russian repeats and English states once in a date range, and real differences between the two UN versions (one line reads "100,000" in English and "10 000" in Russian). Two-file pairing was 100% on equal files and 98.3% with one paragraph missing from one side.

**Disclosure for the README.** While the archive's format was being inspected, six sentences of the test set were printed and seven pattern counts were taken over its English file. No linter was run on the test set and no code was changed afterwards because of what was seen. The README states this.

**Rules for the executor.**

- Work on a branch named `benchmark`. Do not push and do not tag; the maintainer decides both.
- The downloaded archive is untrusted input: unpack it only into `benchmark/data/`, never run anything from that folder.
- After Task 7, `benchmark/mutate.py` must not change. If it has to, the freeze and the hold-out are void and the maintainer decides what happens next.
- Do not read `benchmark/data/testsets/testset/` and do not run anything on it before Task 13.
- No firm names or internal terms anywhere; `tests/test_no_internal_terms.py` enforces it.
- On Windows the repository's interpreter is `.venv/Scripts/python.exe`. The commands below write `python`; use that interpreter.

## File structure

| File | Responsibility |
|---|---|
| `benchmark/__init__.py` | Empty; makes the folder a package. |
| `benchmark/mutate.py` | Plant one defect in one cell. Standard library only. Frozen. |
| `benchmark/un.py` | Read the UN test-set files, cut them into documents, hash them. |
| `benchmark/contracts.py` | Three invented contracts with their party names. |
| `benchmark/score.py` | Write DOCX, run the linter, count catches, false flags, pairing; targets. |
| `benchmark/adjudicate.py` | Hand verdicts on findings in clean text. |
| `benchmark/freeze.py` | Write and check `FROZEN.json`. |
| `benchmark/llm_arm.py` | Whole-document model review of the same mutated copies. |
| `benchmark/run.py` | Command line: `dev`, `contracts`, `worksheet`, `llm`, `holdout`. |
| `benchmark/FROZEN.json` | Hashes of `mutate.py`, the archive and both sets. |
| `benchmark/adjudication/*.json` | The verdicts. |
| `benchmark/results/*.json` | Scored runs, committed. |
| `benchmark/README.md` | How to reproduce; protocol; what the numbers mean. |
| `benchmark/data/` | The unpacked archive. Git-ignored. |
| `NOTICE` | UN attribution, citation and disclaimer. |
| `tests/benchmark/` | One test file per module, plus `helpers.py` with invented UN-format data. |

---

### Task 1: Branch, package skeleton, data in place

**Files:**
- Create: `benchmark/__init__.py`, `tests/benchmark/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: Create the branch**

```bash
git checkout -b benchmark
```

- [ ] **Step 2: Create the two empty package files**

Create `benchmark/__init__.py` and `tests/benchmark/__init__.py`, both empty.

- [ ] **Step 3: Ignore the data folder**

Append to `.gitignore`:

```
benchmark/data/
```

- [ ] **Step 4: Put the data in place and check its hash**

```bash
mkdir -p benchmark/data
cp ~/Downloads/UNv1.0.testsets.tar.gz benchmark/data/
sha256sum benchmark/data/UNv1.0.testsets.tar.gz
```

Expected: `0b4040d723eab132fadc7809a329a4787b338a424ef23bfe3e029d41b7e0153d`. Stop if it differs.

```bash
cd benchmark/data && tar -xzf UNv1.0.testsets.tar.gz && cd ../..
wc -l benchmark/data/testsets/devset/UNv1.0.devset.en benchmark/data/testsets/devset/UNv1.0.devset.ru
```

Expected: 4000 lines each.

- [ ] **Step 5: Confirm git does not see the data**

Run: `git status --short`
Expected: `.gitignore`, `benchmark/__init__.py` and `tests/benchmark/__init__.py` only.

- [ ] **Step 6: Commit**

```bash
git add .gitignore benchmark/__init__.py tests/benchmark/__init__.py
git commit -m "chore(benchmark): package skeleton, data folder ignored"
```

---

### Task 2: The defect-planting tool

A document is a list of `(text_a, text_b)` rows. Each operator changes one side of one row and says which rules count as catching the change. The tool imports nothing from the linter: it is the benchmark's definition of a defect and must not share the linter's blind spots.

**Files:**
- Create: `benchmark/mutate.py`
- Test: `tests/benchmark/test_mutate.py`

- [ ] **Step 1: Write the failing tests**

`tests/benchmark/test_mutate.py`:

```python
import random
from pathlib import Path

import pytest

from benchmark import mutate as m

ROWS = [
    ("Signed on 12 March 2025 for USD 150,000.",
     "Подписано 12 марта 2025 года на 150 000 долларов США."),
    ("The Seller may not assign its rights, see clause 2.2.",
     "Продавец не вправе уступать свои права, см. п. 2.2."),
    ("Payment within 10 business days.", "Оплата в течение 10 рабочих дней."),
    ("The English text shall prevail.",
     "В случае расхождений преимущество имеет текст на английском языке."),
    ("IBAN DE89 3704 0044 0532 0130 00", "IBAN DE89 3704 0044 0532 0130 00"),
    ("Short.", "Коротко."),
]
PARTIES = {"a": ["Seller", "Buyer"], "b": ["Продавец", "Покупатель"]}


def rng():
    return random.Random(1)


@pytest.mark.parametrize("operator,row,side,before,expected", [
    ("date", 0, "a", "12", "BI003"),
    ("date", 0, "b", "12", "BI003"),
    ("currency", 0, "a", "USD", "BI002"),
    ("currency", 0, "b", "долларов США", "BI002"),
    ("reference", 1, "a", "clause 2.2", "BI006"),
    ("reference", 1, "b", "п. 2.2", "BI006"),
    ("negation", 1, "a", " not", "BI011"),
    ("negation", 1, "b", "не ", "BI011"),
    ("day_type", 2, "a", "business ", "BI005"),
    ("day_type", 2, "b", "рабочих ", "BI005"),
    ("prevailing", 3, "a", "English", "BI010"),
    ("prevailing", 3, "b", "английском", "BI010"),
    ("identifier", 4, "a", "DE89 3704 0044 0532 0130 00", "BI009"),
    ("party", 1, "a", "Seller", "BI008"),
    ("party", 1, "b", "Продавец", "BI008"),
])
def test_operator_changes_the_fragment_it_names(operator, row, side, before, expected):
    new_rows, mutation = m.mutate(ROWS, operator, row, side, rng(), PARTIES)
    index = 0 if side == "a" else 1
    assert mutation.before == before
    assert expected in mutation.expected
    assert new_rows[row][index] != ROWS[row][index]
    assert mutation.after != mutation.before


def test_exactly_one_cell_changes():
    for new_rows, mutation in m.all_mutations(ROWS, 5, PARTIES):
        changed = [(r, i) for r in range(len(ROWS)) for i in (0, 1)
                   if new_rows[r][i] != ROWS[r][i]]
        assert changed == [(mutation.row, 0 if mutation.side == "a" else 1)], mutation


def test_every_operator_finds_work_in_the_fixture():
    seen = {mutation.operator for _, mutation in m.all_mutations(ROWS, 5, PARTIES)}
    assert seen == set(m.OPERATORS)


def test_operator_returns_none_when_the_cell_has_nothing_for_it():
    assert m.mutate(ROWS, "date", 5, "a", rng()) is None
    assert m.mutate(ROWS, "currency", 2, "a", rng()) is None
    assert m.mutate(ROWS, "party", 1, "a", rng(), None) is None


def test_drop_empties_a_long_cell_and_spares_a_short_one():
    new_rows, mutation = m.mutate(ROWS, "drop", 1, "b", rng())
    assert new_rows[1] == (ROWS[1][0], "")
    assert mutation.expected == ("BI007",)
    assert m.mutate(ROWS, "drop", 5, "a", rng()) is None


def test_digit_changes_one_digit_and_keeps_the_length():
    for seed in range(30):
        _, mutation = m.mutate(ROWS, "digit", 2, "a", random.Random(seed))
        assert len(mutation.after) == len(mutation.before) == 2
        assert sum(x != y for x, y in zip(mutation.before, mutation.after, strict=True)) == 1


def test_digit_leaves_groups_of_thousands_alone():
    rows = [("per 100 000 live births", "на 100 000 живорождений")]
    for side in ("a", "b"):
        for seed in range(20):
            assert m.mutate(rows, "digit", 0, side, random.Random(seed)) is None


def test_same_seed_gives_the_same_mutations():
    first = [mutation for _, mutation in m.all_mutations(ROWS, 7, PARTIES)]
    again = [mutation for _, mutation in m.all_mutations(ROWS, 7, PARTIES)]
    other = [mutation for _, mutation in m.all_mutations(ROWS, 8, PARTIES)]
    assert first == again
    assert first != other


def test_per_operator_caps_each_operator():
    counts = {}
    for _, mutation in m.all_mutations(ROWS, 7, PARTIES, per_operator=1):
        counts[mutation.operator] = counts.get(mutation.operator, 0) + 1
    assert set(counts.values()) == {1}


def test_source_rows_are_not_modified():
    before = [tuple(row) for row in ROWS]
    m.all_mutations(ROWS, 7, PARTIES)
    assert ROWS == before


def test_the_tool_shares_no_code_with_the_linter():
    source = Path(m.__file__).read_text(encoding="utf-8")
    assert "bilingual_lint" not in source
    assert "docx" not in source
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/benchmark/test_mutate.py -q`
Expected: collection error, `cannot import name 'mutate' from 'benchmark'`.

- [ ] **Step 3: Write the tool**

`benchmark/mutate.py`:

```python
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
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/benchmark/test_mutate.py -q`
Expected: 25 passed.

- [ ] **Step 5: Prove one guard can fail**

In `benchmark/mutate.py` delete the second line of the `NUMBER` pattern (`r"(?![  ]\d{3}\b)")`) and close the bracket on the first. Run the tests: `test_digit_leaves_groups_of_thousands_alone` fails. Restore the line; 25 pass again.

- [ ] **Step 6: Commit**

```bash
git add benchmark/mutate.py tests/benchmark/test_mutate.py
git commit -m "feat(benchmark): defect-planting tool with ten operators"
```

---

### Task 3: The UN test-set reader

**Files:**
- Create: `benchmark/un.py`, `tests/benchmark/helpers.py`
- Test: `tests/benchmark/test_un.py`

- [ ] **Step 1: Write the test helpers**

Tests never read the real UN files. `tests/benchmark/helpers.py` builds invented data in the same layout:

```python
"""Invented data in the layout of the UN test-set archive."""
from pathlib import Path


def make_set(root: Path, part: str = "devset", n: int = 5, ru_lines: list | None = None,
             en_lines: list | None = None) -> Path:
    folder = root / part
    folder.mkdir(parents=True)
    en = en_lines or [f"Sentence {i} of the report." for i in range(n)]
    ru = ru_lines or [f"Предложение {i} доклада." for i in range(n)]
    ids = [f"2015/a/69/{i // 2} en:{i}:1 ru:{i}:1" for i in range(len(en))]
    for suffix, lines in (("en", en), ("ru", ru), ("ids", ids)):
        (folder / f"UNv1.0.{part}.{suffix}").write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return root


# Eight aligned sentences with figures and dates, enough to plant defects in.
EN = [
    "The Committee held its 14th meeting on 12 March 2015 and adopted the agenda.",
    "The budget for the biennium amounts to 250 million dollars, as stated in paragraph 7.",
    "A total of 48 delegations took part in the general debate on the item.",
    "The report was submitted on 3 February 2015 in accordance with resolution 69/12.",
    "The Secretary-General shall not disclose the names of the experts consulted.",
    "The working group will meet again in Geneva to continue its consideration.",
    "Contributions received from 31 Member States were recorded by the secretariat.",
    "The session was closed by the Chair after the adoption of the draft decision.",
]
RU = [
    "Комитет провел свое 14-е заседание 12 марта 2015 года и утвердил повестку дня.",
    "Бюджет на двухгодичный период составляет 250 млн. долларов, как указано в пункте 7.",
    "В общих прениях по этому пункту приняли участие в общей сложности 48 делегаций.",
    "Доклад был представлен 3 февраля 2015 года в соответствии с резолюцией 69/12.",
    "Генеральный секретарь не должен разглашать имена экспертов, с которыми он консультировался.",
    "Рабочая группа вновь соберется в Женеве, чтобы продолжить рассмотрение вопроса.",
    "Секретариат зарегистрировал взносы, полученные от 31 государства-члена.",
    "Председатель закрыл сессию после принятия проекта решения.",
]
```

- [ ] **Step 2: Write the failing tests**

`tests/benchmark/test_un.py`:

```python
import pytest

from benchmark import un

from .helpers import make_set


def test_load_set_reads_aligned_rows_with_their_document(tmp_path):
    rows = un.load_set(make_set(tmp_path), "devset")
    assert len(rows) == 5
    assert rows[3] == ("Sentence 3 of the report.", "Предложение 3 доклада.", "2015/a/69/1")


def test_load_set_refuses_files_of_different_length(tmp_path):
    make_set(tmp_path, ru_lines=["только одна строка"])
    with pytest.raises(ValueError, match="differ in length"):
        un.load_set(tmp_path, "devset")


def test_load_set_refuses_an_unknown_part(tmp_path):
    with pytest.raises(ValueError, match="part must be one of"):
        un.load_set(tmp_path, "trainset")


def test_documents_cuts_blocks_and_keeps_the_tail(tmp_path):
    docs = un.documents(un.load_set(make_set(tmp_path), "devset"), block=2)
    assert [len(d) for d in docs] == [2, 2, 1]
    assert docs[0][0] == ("Sentence 0 of the report.", "Предложение 0 доклада.")


def test_set_hash_is_stable_and_sees_a_changed_byte(tmp_path):
    make_set(tmp_path)
    first = un.set_hash(tmp_path, "devset")
    assert first == un.set_hash(tmp_path, "devset")
    target = tmp_path / "devset" / "UNv1.0.devset.ru"
    target.write_bytes(target.read_bytes().replace("доклада".encode(), "отчёта".encode(), 1))
    assert un.set_hash(tmp_path, "devset") != first
```

- [ ] **Step 3: Run them to see them fail**

Run: `python -m pytest tests/benchmark/test_un.py -q`
Expected: collection error, `cannot import name 'un' from 'benchmark'`.

- [ ] **Step 4: Write the reader**

`benchmark/un.py`:

```python
"""Read the United Nations Parallel Corpus v1.0 test sets.

The archive holds two sets of 4,000 sentences, aligned one to one across the
six languages: 'devset' (documents of January-March 2015) and 'testset'
(April-June 2015). Each language is one UTF-8 file, one sentence per line;
the .ids file names the source document of each line.

The sentences are a sample, not whole documents, so a benchmark document is
a block of consecutive lines."""
from __future__ import annotations

import hashlib
from pathlib import Path

PARTS = ("devset", "testset")
BLOCK = 40   # rows per benchmark document


def _lines(path: Path) -> list:
    lines = path.read_text(encoding="utf-8").split("\n")
    return lines[:-1] if lines and lines[-1] == "" else lines


def set_files(root: Path, part: str, langs: tuple = ("en", "ru")) -> list:
    if part not in PARTS:
        raise ValueError(f"part must be one of {PARTS}, not {part!r}")
    return [root / part / f"UNv1.0.{part}.{suffix}" for suffix in (*langs, "ids")]


def load_set(root: Path, part: str, langs: tuple = ("en", "ru")) -> list:
    """Rows of the set as (text_a, text_b, document_id), in file order."""
    *texts, ids = (_lines(path) for path in set_files(root, part, langs))
    if not len(texts[0]) == len(texts[1]) == len(ids):
        raise ValueError(f"{part}: the language files and the ids file differ in length")
    return [(a, b, line.split(" ", 1)[0]) for a, b, line in zip(*texts, ids, strict=True)]


def documents(rows: list, block: int = BLOCK) -> list:
    """Cut the set into benchmark documents: lists of (text_a, text_b) of
    'block' rows each. A short tail is kept as its own document."""
    pairs = [(a, b) for a, b, _ in rows]
    return [pairs[i:i + block] for i in range(0, len(pairs), block)]


def set_hash(root: Path, part: str, langs: tuple = ("en", "ru")) -> str:
    """SHA-256 over the set's files, in a fixed order. Pins the data a result
    was scored on."""
    digest = hashlib.sha256()
    for path in set_files(root, part, langs):
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/benchmark/test_un.py -q`
Expected: 5 passed.

- [ ] **Step 6: Check it against the real development set**

```bash
python -c "from pathlib import Path; from benchmark import un; r = Path('benchmark/data/testsets'); rows = un.load_set(r, 'devset'); print(len(rows), len(un.documents(rows)), un.set_hash(r, 'devset')[:16])"
```

Expected: `4000 100 492c6a3c1af551d3`.

- [ ] **Step 7: Commit**

```bash
git add benchmark/un.py tests/benchmark/helpers.py tests/benchmark/test_un.py
git commit -m "feat(benchmark): reader for the UN parallel corpus test sets"
```

---

### Task 4: The invented contracts

Three contracts of 15 rows each: services, loan, lease. They are free of defects by construction (dates, amounts and terms were checked against each other: 36 months from 1 July 2025 ends 30 June 2028; the deposit is three months' rent). Do not run the linter on them before Task 10 and do not edit them to make the linter quieter: whatever it says about them is a result.

**Files:**
- Create: `benchmark/contracts.py`
- Test: `tests/benchmark/test_contracts.py`

- [ ] **Step 1: Write the failing tests**

`tests/benchmark/test_contracts.py`:

```python
from benchmark.contracts import CONTRACTS
from benchmark.mutate import OPERATORS, all_mutations


def test_three_contracts_with_two_filled_columns():
    assert [c["name"] for c in CONTRACTS] == ["services", "loan", "lease"]
    for contract in CONTRACTS:
        assert len(contract["rows"]) == 15
        assert all(a.strip() and b.strip() for a, b in contract["rows"])
        assert all(len(contract["parties"][side]) == 2 for side in ("a", "b"))


def test_every_operator_finds_work_in_every_contract():
    for contract in CONTRACTS:
        seen = {mutation.operator for _, mutation in
                all_mutations(contract["rows"], 1, contract["parties"])}
        assert seen == set(OPERATORS), contract["name"]


def test_party_names_appear_on_their_own_side():
    for contract in CONTRACTS:
        text_a = " ".join(a for a, _ in contract["rows"])
        text_b = " ".join(b for _, b in contract["rows"])
        assert all(name in text_a for name in contract["parties"]["a"])
        assert all(name in text_b for name in contract["parties"]["b"])
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/benchmark/test_contracts.py -q`
Expected: collection error, `No module named 'benchmark.contracts'`.

- [ ] **Step 3: Write the contracts**

`benchmark/contracts.py`:

```python
"""Three invented contracts, with no defects.

UN documents carry numbers, dates and references, but almost no prices, bank
details, defined party names or prevailing-language clauses. These contracts
supply them. All names, numbers and accounts are made up.

They were written by the author of the rules, so they are a weaker test than
the UN text: results on them are reported separately and never merged with
the UN figures."""
from __future__ import annotations

SERVICES = [
    ("SERVICES AGREEMENT No. 27", "ДОГОВОР ОКАЗАНИЯ УСЛУГ № 27"),
    ("Yerevan, 4 September 2025", "г. Ереван, 4 сентября 2025 г."),
    ('Orion Data LLC (the "Customer") and Meridian Soft GmbH (the "Contractor") '
     "have agreed as follows.",
     "ООО «Орион Дата» (далее – «Заказчик») и Meridian Soft GmbH (далее – «Исполнитель») "
     "договорились о нижеследующем."),
    ("1.1. The Contractor shall provide the software support services listed in Annex 1.",
     "1.1. Исполнитель обязуется оказать услуги по сопровождению программного обеспечения, "
     "перечисленные в Приложении 1."),
    ("1.2. The services shall be provided from 1 October 2025 to 30 September 2026.",
     "1.2. Услуги оказываются с 1 октября 2025 года по 30 сентября 2026 года."),
    ("2.1. The monthly fee is EUR 12,500 (twelve thousand five hundred euros), "
     "excluding VAT.",
     "2.1. Ежемесячное вознаграждение составляет 12 500 (двенадцать тысяч пятьсот) евро "
     "без учёта НДС."),
    ("2.2. The Customer shall pay each invoice within 15 (fifteen) business days of receipt.",
     "2.2. Заказчик обязан оплатить каждый счёт в течение 15 (пятнадцати) рабочих дней "
     "с даты его получения."),
    ("2.3. Late payment bears interest at 0.05% of the overdue amount per day, "
     "as provided in clause 2.2.",
     "2.3. За просрочку оплаты начисляются пени в размере 0,05% от просроченной суммы "
     "за каждый день согласно п. 2.2."),
    ("3.1. The Contractor may not engage subcontractors without the prior written consent "
     "of the Customer.",
     "3.1. Исполнитель не вправе привлекать субподрядчиков без предварительного "
     "письменного согласия Заказчика."),
    ("3.2. The Contractor shall remedy any defect in the services within 5 (five) working "
     "days of the Customer's notice.",
     "3.2. Исполнитель обязан устранить любой недостаток услуг в течение 5 (пяти) рабочих "
     "дней с даты уведомления Заказчика."),
    ("4.1. The liability of the Contractor under this Agreement shall not exceed EUR 150,000.",
     "4.1. Ответственность Исполнителя по Договору не может превышать 150 000 евро."),
    ("5.1. Either party may terminate this Agreement by giving 60 (sixty) days' "
     "written notice.",
     "5.1. Любая из сторон вправе расторгнуть Договор, направив письменное уведомление "
     "за 60 (шестьдесят) дней."),
    ("6.1. Bank details of the Contractor: IBAN DE44 5001 0517 5407 3249 31, "
     "registration number 5263018847.",
     "6.1. Банковские реквизиты Исполнителя: IBAN DE44 5001 0517 5407 3249 31, "
     "регистрационный номер 5263018847."),
    ("7.1. This Agreement is made in English and Russian. In case of discrepancy "
     "the English text shall prevail.",
     "7.1. Договор составлен на английском и русском языках. В случае расхождений "
     "преимущество имеет текст на английском языке."),
    ("7.2. This Agreement is made in 2 (two) copies, one for each party.",
     "7.2. Договор составлен в 2 (двух) экземплярах, по одному для каждой из сторон."),
]

LOAN = [
    ("LOAN AGREEMENT No. 8", "ДОГОВОР ЗАЙМА № 8"),
    ("Almaty, 17 February 2026", "г. Алматы, 17 февраля 2026 г."),
    ('Cedar Capital Ltd (the "Lender") and Polar Logistics LLP (the "Borrower") '
     "have agreed as follows.",
     "Cedar Capital Ltd (далее – «Займодавец») и ТОО «Полар Логистикс» (далее – «Заёмщик») "
     "договорились о нижеследующем."),
    ("1.1. The Lender shall lend the Borrower USD 400,000 (four hundred thousand US dollars).",
     "1.1. Займодавец предоставляет Заёмщику заём в размере 400 000 (четыреста тысяч) "
     "долларов США."),
    ("1.2. The loan shall be disbursed within 3 (three) banking days after the date "
     "of this Agreement.",
     "1.2. Заём предоставляется в течение 3 (трёх) банковских дней с даты заключения "
     "Договора."),
    ("2.1. Interest accrues at 9.5% per annum on the outstanding amount of the loan.",
     "2.1. На непогашенную сумму займа начисляются проценты по ставке 9,5% годовых."),
    ("2.2. Interest is payable on the last business day of each calendar quarter.",
     "2.2. Проценты уплачиваются в последний рабочий день каждого календарного квартала."),
    ("3.1. The Borrower shall repay the loan in full not later than 17 February 2029.",
     "3.1. Заёмщик обязан полностью возвратить заём не позднее 17 февраля 2029 года."),
    ("3.2. The Borrower may repay the loan early in instalments of not less than USD 50,000.",
     "3.2. Заёмщик вправе досрочно возвращать заём частями не менее 50 000 долларов США."),
    ("3.3. If repayment is delayed, the Borrower shall pay a penalty of 0.1% of the overdue "
     "amount per day, in addition to the interest under clause 2.1.",
     "3.3. При просрочке возврата Заёмщик уплачивает неустойку в размере 0,1% от "
     "просроченной суммы за каждый день сверх процентов, предусмотренных п. 2.1."),
    ("4.1. The Borrower must not dispose of its fixed assets worth more than USD 100,000 "
     "without the consent of the Lender.",
     "4.1. Заёмщик не вправе отчуждать основные средства стоимостью свыше 100 000 "
     "долларов США без согласия Займодавца."),
    ("4.2. The Lender may demand early repayment if the Borrower is more than 30 (thirty) "
     "days late with any payment.",
     "4.2. Займодавец вправе потребовать досрочного возврата займа, если Заёмщик допустил "
     "просрочку любого платежа более чем на 30 (тридцать) дней."),
    ("5.1. Account of the Lender: IBAN GB29 NWBK 6016 1331 9268 19, "
     "company number 104417750032.",
     "5.1. Счёт Займодавца: IBAN GB29 NWBK 6016 1331 9268 19, "
     "регистрационный номер компании 104417750032."),
    ("6.1. This Agreement is made in English and Russian. In case of discrepancy "
     "the Russian text shall prevail.",
     "6.1. Договор составлен на английском и русском языках. В случае расхождений "
     "преимущество имеет текст на русском языке."),
    ("6.2. Notices shall be sent within 5 (five) business days to the addresses stated "
     "in this Agreement.",
     "6.2. Уведомления направляются в течение 5 (пяти) рабочих дней по адресам, "
     "указанным в Договоре."),
]

LEASE = [
    ("LEASE AGREEMENT No. 112", "ДОГОВОР АРЕНДЫ № 112"),
    ("Tbilisi, 23 June 2025", "г. Тбилиси, 23 июня 2025 г."),
    ('Harbour Estates JSC (the "Landlord") and Lumen Retail LLC (the "Tenant") '
     "have agreed as follows.",
     "АО «Харбор Эстейтс» (далее – «Арендодатель») и ООО «Люмен Ритейл» "
     "(далее – «Арендатор») договорились о нижеследующем."),
    ("1.1. The Landlord shall lease to the Tenant office premises with an area of "
     "340 square metres on the 6th floor.",
     "1.1. Арендодатель передаёт Арендатору в аренду офисное помещение площадью "
     "340 квадратных метров на 6 этаже."),
    ("1.2. The lease term is 36 (thirty-six) months from 1 July 2025.",
     "1.2. Срок аренды составляет 36 (тридцать шесть) месяцев с 1 июля 2025 года."),
    ("2.1. The monthly rent is 8,200 euros, payable in advance not later than the 5th day "
     "of each month.",
     "2.1. Ежемесячная арендная плата составляет 8 200 евро и вносится авансом не позднее "
     "5 числа каждого месяца."),
    ("2.2. The Tenant shall pay a security deposit of 24,600 euros within 10 (ten) banking "
     "days after signing.",
     "2.2. Арендатор вносит обеспечительный платёж в размере 24 600 евро в течение "
     "10 (десяти) банковских дней после подписания."),
    ("2.3. The rent may be increased once a year by not more than 4%, as provided "
     "in clause 2.1.",
     "2.3. Арендная плата может быть увеличена один раз в год не более чем на 4% "
     "в порядке, предусмотренном п. 2.1."),
    ("3.1. The Tenant may not sublease the premises or any part of them.",
     "3.1. Арендатор не вправе передавать помещение или его часть в субаренду."),
    ("3.2. The Tenant shall not carry out alterations without the written consent "
     "of the Landlord.",
     "3.2. Арендатор не должен производить перепланировку без письменного согласия "
     "Арендодателя."),
    ("3.3. The Landlord shall carry out major repairs at its own expense within "
     "20 (twenty) working days of the Tenant's request.",
     "3.3. Арендодатель обязан производить капитальный ремонт за свой счёт в течение "
     "20 (двадцати) рабочих дней с даты обращения Арендатора."),
    ("4.1. Either party may terminate this Agreement early by giving 90 (ninety) days' "
     "notice, subject to clause 2.2.",
     "4.1. Любая из сторон вправе досрочно расторгнуть Договор, уведомив другую сторону "
     "за 90 (девяносто) дней, с учётом п. 2.2."),
    ("5.1. Rent is paid to the account of the Landlord: IBAN NL91 ABNA 0417 1643 00, "
     "tax number 7701456982.",
     "5.1. Арендная плата вносится на счёт Арендодателя: IBAN NL91 ABNA 0417 1643 00, "
     "налоговый номер 7701456982."),
    ("6.1. This Agreement is made in Russian and English. In case of discrepancy "
     "the Russian version shall prevail.",
     "6.1. Договор составлен на русском и английском языках. При расхождениях "
     "преимущество имеет текст на русском языке."),
    ("6.2. The premises shall be returned on 30 June 2028 in the condition recorded "
     "in the handover certificate.",
     "6.2. Помещение подлежит возврату 30 июня 2028 года в состоянии, зафиксированном "
     "в акте приёма-передачи."),
]

CONTRACTS = [
    {"name": "services", "rows": SERVICES,
     "parties": {"a": ["Customer", "Contractor"], "b": ["Заказчик", "Исполнитель"]}},
    {"name": "loan", "rows": LOAN,
     "parties": {"a": ["Lender", "Borrower"], "b": ["Займодавец", "Заёмщик"]}},
    {"name": "lease", "rows": LEASE,
     "parties": {"a": ["Landlord", "Tenant"], "b": ["Арендодатель", "Арендатор"]}},
]
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/benchmark/test_contracts.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add benchmark/contracts.py tests/benchmark/test_contracts.py
git commit -m "feat(benchmark): three invented contracts for contract-only defects"
```

---

### Task 5: The scorer

The scorer treats the linter as a user would: a DOCX goes in, findings come out. A planted defect is caught when the mutated copy has a finding on the changed row that the clean copy did not have. The finding's message is part of its identity, because a first version without it lost 16 of 19 "misses" to rows that were already flagged for something else.

Pairing is measured in two-file mode twice: with equal files, and with one paragraph left out of one side, which is the case that can go wrong.

**Files:**
- Create: `benchmark/score.py`
- Test: `tests/benchmark/test_score.py`

- [ ] **Step 1: Write the failing tests**

`tests/benchmark/test_score.py`:

```python
from benchmark import score

from .helpers import EN, RU

ROWS = list(zip(EN, RU, strict=True))


def test_lint_rows_reports_a_changed_figure_on_its_row(tmp_path):
    clean = score.lint_rows(ROWS, tmp_path)
    broken = [*ROWS]
    broken[2] = (EN[2].replace("48", "84"), RU[2])
    new = [f for f in score.lint_rows(broken, tmp_path) if f not in set(clean)]
    assert new, "the linter should say something new about the changed row"
    assert {f[2] for f in new} == {2}
    assert all(f[1] in score.RANK for f in new)


def test_lint_rows_is_quiet_on_matching_text(tmp_path):
    rows = [("The fee is 500 euros.", "Вознаграждение составляет 500 евро.")]
    assert [f for f in score.lint_rows(rows, tmp_path) if f[1] == "error"] == []


def test_pairing_is_whole_on_equal_files_and_counts_only_rows_with_a_partner(tmp_path):
    assert score.pairing(ROWS, tmp_path) == (8, 8)
    right, total = score.pairing(ROWS, tmp_path, missing=3, side="b")
    assert total == 7
    assert 0 <= right <= 7


def test_score_document_catches_planted_figures_and_reports_misses():
    result = score.score_document(ROWS, seed=1)
    by_operator = {}
    for case in result["cases"]:
        by_operator.setdefault(case["operator"], []).append(case)
    assert {"digit", "date", "drop"} <= set(by_operator)
    assert all(case["caught_any"] for case in by_operator["digit"])
    assert all(case["caught_any"] for case in by_operator["drop"])
    assert result["pairs"] == 8
    assert result["pairing"] == {"right": 8, "total": 8}
    assert result["pairing_one_missing"]["total"] == 14


def test_a_defect_on_a_row_that_was_already_flagged_still_counts():
    rows = [*ROWS]
    rows[2] = (EN[2].replace("48", "49"), RU[2])      # flagged before any mutation
    result = score.score_document(rows, seed=1, operators=("digit",))
    assert any(f[2] == 2 for f in result["clean_findings"])
    on_row = [case for case in result["cases"] if case["row"] == 2]
    assert on_row and all(case["caught_any"] for case in on_row)


def fake_result(caught: int, planted: int, operator: str = "digit", errors: int = 0) -> dict:
    cases = [{"operator": operator, "caught_expected": i < caught, "caught_any": i < caught}
             for i in range(planted)]
    return {"pairs": 50, "cases": cases,
            "clean_findings": [["BI001", "error", i, "m"] for i in range(errors)],
            "pairing": {"right": 50, "total": 50},
            "pairing_one_missing": {"right": 90, "total": 98}}


def test_summarise_adds_up_operators_groups_and_rates():
    summary = score.summarise([fake_result(9, 10, errors=2), fake_result(4, 4, "drop")])
    assert summary["documents"] == 2 and summary["pairs"] == 100
    assert summary["operators"]["digit"]["recall_any"] == 0.9
    assert summary["figures"] == {"planted": 10, "caught": 9, "recall": 0.9}
    assert summary["paragraphs"]["recall"] == 1.0
    assert summary["clean_flags_per_100_pairs"]["error"] == 2.0
    assert summary["pairing_accuracy"] == 1.0
    assert summary["pairing_accuracy_one_missing"] == round(180 / 196, 4)


def test_targets_mark_met_missed_and_unmeasured():
    summary = score.summarise([fake_result(9, 10, errors=2)])
    rows = {name: (value, met) for name, value, _, met in score.targets(summary)}
    assert rows["figures_recall"] == (0.9, False)
    assert rows["paragraphs_recall"] == (None, None)
    assert rows["error_flags_per_100_pairs"] == (4.0, False)
    assert rows["pairing_accuracy"] == (round(90 / 98, 4), False)
    judged = {name: (value, met) for name, value, _, met in score.targets(summary, 1.5)}
    assert judged["error_flags_per_100_pairs"] == (1.5, True)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/benchmark/test_score.py -q`
Expected: collection error, `cannot import name 'score' from 'benchmark'`.

- [ ] **Step 3: Write the scorer**

`benchmark/score.py`:

```python
"""Run the linter over clean and mutated documents and count what it catches.

Every document goes through the real pipeline: it is written to a DOCX file
and read back by the linter's own loader, the same way a user's file is."""
from __future__ import annotations

import random
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from bilingual_lint.config import Config
from bilingual_lint.loaders import load
from bilingual_lint.rules import run_all
from bilingual_lint.segment import refine
from docx import Document as new_docx

from .mutate import OPERATORS, all_mutations

ROW = re.compile(r"(?:row|paragraph) (\d+)")
RANK = {"info": 0, "warning": 1, "error": 2}
# Spec section 9: the operator groups the published targets are stated for.
FIGURE_OPERATORS = ("digit", "date", "currency", "identifier")
PARAGRAPH_OPERATORS = ("drop",)
TARGETS = {"figures_recall": 0.98, "paragraphs_recall": 0.95,
           "error_flags_per_100_pairs": 3.0, "pairing_accuracy": 0.95}


def write_two_column(path: Path, rows: list) -> Path:
    document = new_docx()
    table = document.add_table(rows=0, cols=2)
    for a, b in rows:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = a, b
    document.save(str(path))
    return path


def write_plain(path: Path, paragraphs: list) -> Path:
    document = new_docx()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(str(path))
    return path


def _row_of(finding) -> int | None:
    """0-based source row a finding points at, read from its location text."""
    pair = finding.pair
    for segment in (pair.a, pair.b) if pair else ():
        match = ROW.search(segment.location) if segment else None
        if match:
            return int(match.group(1)) - 1
    return None


def lint_rows(rows: list, workdir: Path, langs: tuple = ("en", "ru")) -> list:
    """Findings for a two-column document as (rule_id, severity, row, message)
    tuples. File notes (BI000) are left out: they are about the file, not a row."""
    path = write_two_column(workdir / "case.docx", rows)
    doc = refine(load([path], langs))
    findings, *_ = run_all(doc, Config())
    return [(f.rule_id, f.severity.value, _row_of(f), f.message) for f in findings
            if f.rule_id != "BI000"]


def pairing(rows: list, workdir: Path, missing: int | None = None, side: str = "b",
            langs: tuple = ("en", "ru")) -> tuple:
    """Two-file mode: (rows paired with their true partner, rows that have one).
    With 'missing', that row is left out of one file, as when a paragraph was
    dropped from one language version."""
    kept = [(a, b) for i, (a, b) in enumerate(rows) if i != missing]
    path_a = write_plain(workdir / "a.docx", [a for i, (a, _) in enumerate(rows)
                                             if not (side == "a" and i == missing)])
    path_b = write_plain(workdir / "b.docx", [b for i, (_, b) in enumerate(rows)
                                             if not (side == "b" and i == missing)])
    doc = load([path_a, path_b], langs)
    truth = dict(kept)
    right = sum(1 for p in doc.pairs if p.a and p.b and truth.get(p.a.text) == p.b.text)
    return right, len(kept)


def score_document(rows: list, seed: int, parties: dict | None = None,
                   operators: tuple = OPERATORS, per_operator: int | None = None,
                   langs: tuple = ("en", "ru")) -> dict:
    """Lint the clean document, then one mutated copy per planted defect.

    A defect is caught when the mutated copy has a finding on the mutated row
    that the clean copy did not have. The message is part of a finding's
    identity, so a row that was already flagged still counts once the linter
    says something new about it. 'expected' means the finding came from a rule
    built for that kind of defect; 'any' accepts any rule."""
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        clean = lint_rows(rows, workdir, langs)
        baseline = set(clean)
        cases = []
        for mutated_rows, mutation in all_mutations(rows, seed, parties, operators,
                                                    per_operator):
            new = [f for f in lint_rows(mutated_rows, workdir, langs)
                   if f not in baseline and f[2] == mutation.row]
            expected = [f for f in new if f[0] in mutation.expected]
            cases.append({
                **mutation.as_dict(),
                "caught_expected": bool(expected),
                "caught_any": bool(new),
                "top_severity": max((f[1] for f in new), key=RANK.get, default=None),
                "rules": sorted({f[0] for f in new}),
            })
        right, total = pairing(rows, workdir, langs=langs)
        gap_right = gap_total = 0
        if len(rows) > 2:
            for side in ("a", "b"):
                missing = random.Random(f"{seed}:gap:{side}").randrange(1, len(rows) - 1)
                r, t = pairing(rows, workdir, missing, side, langs)
                gap_right, gap_total = gap_right + r, gap_total + t
    return {"pairs": len(rows), "clean_findings": clean, "cases": cases,
            "pairing": {"right": right, "total": total},
            "pairing_one_missing": {"right": gap_right, "total": gap_total}}


def _ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def summarise(results: list) -> dict:
    """results: score_document outputs. Returns the numbers the README prints."""
    by_operator: dict = defaultdict(lambda: {"planted": 0, "expected": 0, "any": 0})
    pairs = right = total = gap_right = gap_total = 0
    clean: dict = defaultdict(int)
    for result in results:
        pairs += result["pairs"]
        right += result["pairing"]["right"]
        total += result["pairing"]["total"]
        gap_right += result["pairing_one_missing"]["right"]
        gap_total += result["pairing_one_missing"]["total"]
        for _, severity, *_ in result["clean_findings"]:
            clean[severity] += 1
        for case in result["cases"]:
            row = by_operator[case["operator"]]
            row["planted"] += 1
            row["expected"] += case["caught_expected"]
            row["any"] += case["caught_any"]
    for row in by_operator.values():
        row["recall_expected"] = _ratio(row["expected"], row["planted"])
        row["recall_any"] = _ratio(row["any"], row["planted"])

    def group(names: tuple) -> dict:
        planted = sum(by_operator[n]["planted"] for n in names if n in by_operator)
        caught = sum(by_operator[n]["any"] for n in names if n in by_operator)
        return {"planted": planted, "caught": caught, "recall": _ratio(caught, planted)}

    return {
        "documents": len(results),
        "pairs": pairs,
        "operators": {name: by_operator[name] for name in OPERATORS if name in by_operator},
        "figures": group(FIGURE_OPERATORS),
        "paragraphs": group(PARAGRAPH_OPERATORS),
        "clean_flags_per_100_pairs": {
            severity: round(100 * clean[severity] / pairs, 2) if pairs else None
            for severity in ("error", "warning", "info")},
        "pairing_accuracy": _ratio(right, total),
        "pairing_accuracy_one_missing": _ratio(gap_right, gap_total),
    }


def targets(summary: dict, false_error_flags_per_100: float | None = None) -> list:
    """The four published targets as (name, value, target, met). 'met' is None
    when there was nothing to measure. The false-flag target is judged on the
    adjudicated rate when one is given, otherwise on the raw rate."""
    flags = (false_error_flags_per_100 if false_error_flags_per_100 is not None
             else summary["clean_flags_per_100_pairs"]["error"])
    pairing_values = [v for v in (summary["pairing_accuracy"],
                                  summary["pairing_accuracy_one_missing"]) if v is not None]
    values = {
        "figures_recall": summary["figures"]["recall"],
        "paragraphs_recall": summary["paragraphs"]["recall"],
        "error_flags_per_100_pairs": flags,
        "pairing_accuracy": min(pairing_values) if pairing_values else None,
    }
    out = []
    for name, target in TARGETS.items():
        value = values[name]
        if value is None:
            met = None
        elif name == "error_flags_per_100_pairs":
            met = value <= target
        else:
            met = value >= target
        out.append((name, value, target, met))
    return out
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/benchmark/test_score.py -q`
Expected: 7 passed.

- [ ] **Step 5: Prove the masking guard can fail**

In `lint_rows`, drop `f.message` from the returned tuple (and `, f.message` only). Run the tests: `test_a_defect_on_a_row_that_was_already_flagged_still_counts` fails. Restore; 7 pass.

- [ ] **Step 6: Commit**

```bash
git add benchmark/score.py tests/benchmark/test_score.py
git commit -m "feat(benchmark): scorer for catches, false flags and pairing"
```

---

### Task 6: Verdicts on findings in clean text

A finding on unmodified text is a false flag or a real difference between the two published versions. A person decides. Verdicts live in `benchmark/adjudication/<part>.json`; a finding without a verdict counts against the linter.

**Files:**
- Create: `benchmark/adjudicate.py`
- Test: `tests/benchmark/test_adjudicate.py`

- [ ] **Step 1: Write the failing tests**

`tests/benchmark/test_adjudicate.py`:

```python
import json

import pytest

from benchmark import adjudicate

RESULTS = [
    {"pairs": 40, "clean_findings": [
        ["BI001", "error", 5, "numbers differ — en only: 100,000 · ru only: 10 000"],
        ["BI003", "error", 19, "times differ — en only: 11 a.m."],
        ["BI011", "info", 2, "possible negation mismatch"]]},
    {"pairs": 60, "clean_findings": [["BI001", "error", 0, "numbers differ — en only: 5"]]},
]
REAL = "0|5|BI001|numbers differ — en only: 100,000 · ru only: 10 000"
FALSE = "0|19|BI003|times differ — en only: 11 a.m."
DOCS = [[("a", "b")] * 40, [("first a", "first b")] * 60]


def test_only_errors_are_listed_and_each_has_a_stable_key():
    found = adjudicate.error_findings(RESULTS)
    assert [item[0] for item in found] == [REAL, FALSE, "1|0|BI001|numbers differ — en only: 5"]


def test_tally_counts_an_unjudged_finding_as_a_false_flag():
    verdicts = {REAL: {"verdict": "real", "note": "the Russian text has 10 000"},
                FALSE: {"verdict": "false", "note": "same time, written differently"}}
    assert adjudicate.tally(RESULTS, verdicts) == {
        "error_findings": 3, "real": 1, "false": 1, "open": 1, "false_per_100_pairs": 2.0}
    assert adjudicate.tally(RESULTS, {})["false_per_100_pairs"] == 3.0


def test_load_returns_nothing_for_a_missing_file_and_rejects_a_bad_verdict(tmp_path):
    assert adjudicate.load(tmp_path / "dev.json") == {}
    path = tmp_path / "dev.json"
    path.write_text(json.dumps({REAL: {"verdict": "maybe"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="verdict must be one of"):
        adjudicate.load(path)


def test_worksheet_lists_only_the_findings_without_a_verdict():
    sheet = adjudicate.worksheet(RESULTS, DOCS, {REAL: {"verdict": "real"}})
    assert REAL not in sheet
    assert f"## `{FALSE}`" in sheet
    assert "- A: first a" in sheet and "- B: first b" in sheet
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/benchmark/test_adjudicate.py -q`
Expected: collection error, `cannot import name 'adjudicate' from 'benchmark'`.

- [ ] **Step 3: Write the module**

`benchmark/adjudicate.py`:

```python
"""Hand verdicts on what the linter reports in unmodified text.

A finding on a clean pair is either a false flag or a real difference between
the two published versions. Only a person reading both can tell, so each
error-level finding gets a verdict in benchmark/adjudication/<part>.json:

    {"<key>": {"verdict": "real" | "false", "note": "<why>"}}

A finding with no verdict counts as a false flag."""
from __future__ import annotations

import json
from pathlib import Path

VERDICTS = ("real", "false")


def key(document: int, finding: list) -> str:
    rule, _, row, message = finding
    return f"{document}|{row}|{rule}|{message}"


def error_findings(results: list) -> list:
    """(key, document, row, rule, message) for every error on clean text."""
    return [(key(n, f), n, f[2], f[0], f[3])
            for n, result in enumerate(results)
            for f in result["clean_findings"] if f[1] == "error"]


def load(path: Path) -> dict:
    if not path.is_file():
        return {}
    verdicts = json.loads(path.read_text(encoding="utf-8"))
    bad = [k for k, v in verdicts.items() if v.get("verdict") not in VERDICTS]
    if bad:
        raise ValueError(f"verdict must be one of {VERDICTS}: {bad[:3]}")
    return verdicts


def tally(results: list, verdicts: dict) -> dict:
    found = error_findings(results)
    counts = {"real": 0, "false": 0, "open": 0}
    for finding_key, *_ in found:
        counts[verdicts.get(finding_key, {}).get("verdict", "open")] += 1
    pairs = sum(result["pairs"] for result in results)
    not_real = counts["false"] + counts["open"]
    return {"error_findings": len(found), **counts,
            "false_per_100_pairs": round(100 * not_real / pairs, 2) if pairs else None}


def worksheet(results: list, documents: list, verdicts: dict) -> str:
    """Markdown list of the findings still without a verdict, with both texts."""
    lines = ["# Findings on clean text awaiting a verdict", ""]
    for finding_key, document, row, rule, message in error_findings(results):
        if finding_key in verdicts:
            continue
        a, b = documents[document][row] if row is not None else ("", "")
        lines += [f"## `{finding_key}`", "", f"- {rule}: {message}", f"- A: {a}",
                  f"- B: {b}", ""]
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/benchmark/test_adjudicate.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add benchmark/adjudicate.py tests/benchmark/test_adjudicate.py
git commit -m "feat(benchmark): hand verdicts on findings in clean text"
```

---

### Task 7: The freeze

From here on the definition of a defect and the data are fixed. `code_hash` normalises line endings so a Windows checkout that turns LF into CRLF still matches.

**Files:**
- Create: `benchmark/freeze.py`, `benchmark/FROZEN.json` (generated), `tests/benchmark/test_frozen.py`
- Test: `tests/benchmark/test_freeze.py`

- [ ] **Step 1: Write the failing tests**

`tests/benchmark/test_freeze.py`:

```python
import json

from benchmark import freeze

from .helpers import make_set


def frozen_tree(tmp_path):
    data = tmp_path / "data"
    make_set(data, "devset")
    make_set(data, "testset")
    mutate = tmp_path / "mutate.py"
    mutate.write_bytes(b"A = 1\nB = 2\n")
    record = {"mutate_sha256": freeze.code_hash(mutate)}
    for part in ("devset", "testset"):
        record[f"{part}_sha256"] = freeze.set_hash(data, part)
    frozen = tmp_path / "FROZEN.json"
    frozen.write_text(json.dumps(record), encoding="utf-8")
    return data, mutate, frozen


def test_code_hash_ignores_line_endings_and_sees_a_real_change(tmp_path):
    lf, crlf, other = tmp_path / "lf.py", tmp_path / "crlf.py", tmp_path / "other.py"
    lf.write_bytes(b"A = 1\nB = 2\n")
    crlf.write_bytes(b"A = 1\r\nB = 2\r\n")
    other.write_bytes(b"A = 1\nB = 3\n")
    assert freeze.code_hash(lf) == freeze.code_hash(crlf)
    assert freeze.code_hash(lf) != freeze.code_hash(other)


def test_an_intact_tree_has_no_problems(tmp_path):
    data, mutate, frozen = frozen_tree(tmp_path)
    assert freeze.problems(data, frozen, mutate) == []
    assert freeze.problems(None, frozen, mutate) == []


def test_a_changed_mutation_tool_is_reported(tmp_path):
    data, mutate, frozen = frozen_tree(tmp_path)
    mutate.write_bytes(b"A = 1\nB = 3\n")
    assert freeze.problems(data, frozen, mutate) == ["mutate.py has changed since the freeze"]


def test_changed_data_is_reported(tmp_path):
    data, mutate, frozen = frozen_tree(tmp_path)
    target = data / "testset" / "UNv1.0.testset.en"
    target.write_bytes(target.read_bytes() + b"One more line.\n")
    assert freeze.problems(data, frozen, mutate) == [
        "the testset files differ from the frozen ones"]


def test_no_freeze_file_is_a_problem(tmp_path):
    assert freeze.problems(None, tmp_path / "FROZEN.json") == [
        "FROZEN.json does not exist: nothing has been frozen"]


def test_snapshot_records_the_tool_the_archive_and_both_sets(tmp_path):
    data, _, _ = frozen_tree(tmp_path)
    archive = tmp_path / "sets.tar.gz"
    archive.write_bytes(b"not really an archive")
    record = freeze.snapshot(data, archive)
    assert record["mutate_sha256"] == freeze.code_hash(freeze.MUTATE)
    assert record["archive"] == "sets.tar.gz" and len(record["archive_sha256"]) == 64
    assert record["devset_sha256"] == freeze.set_hash(data, "devset")
    assert record["testset_sha256"] == freeze.set_hash(data, "testset")
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/benchmark/test_freeze.py -q`
Expected: collection error, `cannot import name 'freeze' from 'benchmark'`.

- [ ] **Step 3: Write the module**

`benchmark/freeze.py`:

```python
"""Pin the defect-planting tool and the data before any rule is tuned.

FROZEN.json records the hash of mutate.py and of both UN sets. A hold-out
score counts only if both still match: the definition of a defect and the
data it is planted in were fixed before the linter was tuned against them.

    python -m benchmark.freeze --data benchmark/data/testsets --archive <tar.gz>
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path

from .un import PARTS, set_hash

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "FROZEN.json"
MUTATE = HERE / "mutate.py"


def code_hash(path: Path) -> str:
    """SHA-256 of a source file with line endings normalised, so a Windows
    checkout that rewrites LF as CRLF hashes the same."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def snapshot(data_root: Path, archive: Path | None = None) -> dict:
    record = {"frozen_on": datetime.date.today().isoformat(),
              "mutate_sha256": code_hash(MUTATE)}
    if archive is not None:
        record["archive"] = archive.name
        record["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    for part in PARTS:
        record[f"{part}_sha256"] = set_hash(data_root, part)
    return record


def problems(data_root: Path | None = None, frozen: Path = FROZEN,
             mutate: Path = MUTATE) -> list:
    """Reasons the current tree does not match the freeze; empty when it does.
    Without data_root only the code is checked."""
    if not frozen.is_file():
        return [f"{frozen.name} does not exist: nothing has been frozen"]
    record = json.loads(frozen.read_text(encoding="utf-8"))
    found = []
    if code_hash(mutate) != record["mutate_sha256"]:
        found.append("mutate.py has changed since the freeze")
    if data_root is not None:
        for part in PARTS:
            if set_hash(data_root, part) != record[f"{part}_sha256"]:
                found.append(f"the {part} files differ from the frozen ones")
    return found


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Freeze the mutation tool and the data.")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args(argv)
    if FROZEN.exists():
        print(f"{FROZEN} already exists. The freeze is made once; a new hold-out "
              "needs a new file name and a note in benchmark/README.md.")
        return 2
    record = snapshot(args.data, args.archive)
    FROZEN.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/benchmark/test_freeze.py -q`
Expected: 6 passed.

- [ ] **Step 5: Freeze**

```bash
python -m benchmark.freeze --data benchmark/data/testsets --archive benchmark/data/UNv1.0.testsets.tar.gz
```

Expected: a JSON record is printed and `benchmark/FROZEN.json` exists, with `"archive_sha256": "0b4040d723eab132fadc7809a329a4787b338a424ef23bfe3e029d41b7e0153d"` and a `devset_sha256` that starts `492c6a3c1af551d3`. This hashes the test-set files without reading them as text.

- [ ] **Step 6: Add the standing guard**

`tests/benchmark/test_frozen.py`:

```python
from benchmark import freeze


def test_the_mutation_tool_is_unchanged_since_the_freeze():
    assert freeze.problems() == []
```

Run: `python -m pytest tests/benchmark/test_frozen.py -q`
Expected: 1 passed.

- [ ] **Step 7: Prove the guard can fail**

Add a blank comment line `# x` to the end of `benchmark/mutate.py`. Run the test: it fails with `['mutate.py has changed since the freeze']`. Remove the line; it passes.

- [ ] **Step 8: Commit**

```bash
git add benchmark/freeze.py benchmark/FROZEN.json tests/benchmark/test_freeze.py tests/benchmark/test_frozen.py
git commit -m "feat(benchmark): freeze the mutation tool and pin both UN sets by hash"
```

---

### Task 8: The model comparison arm

One model call per document: the whole document as numbered rows, and the model names the rows that differ. The model function is passed in, so tests use a stand-in and never touch the network.

A model may also name rows on the clean copy. Some of those are real differences, so they are reported as a rate and not called false flags; a planted defect on such a row cannot be attributed and is excluded from recall.

**Files:**
- Create: `benchmark/llm_arm.py`
- Test: `tests/benchmark/test_llm_arm.py`

- [ ] **Step 1: Write the failing tests**

`tests/benchmark/test_llm_arm.py`:

```python
import json

import pytest

from benchmark import llm_arm

from .helpers import EN, RU

ROWS = list(zip(EN, RU, strict=True))


def test_render_numbers_rows_from_one_and_marks_an_empty_cell():
    text = llm_arm.render([("One.", "Один."), ("Two.", "")])
    assert text == "Row 1\nen: One.\nru: Один.\n\nRow 2\nen: Two.\nru: (empty)"


def test_parse_reads_rows_and_ignores_numbers_out_of_range():
    reply = 'Here you go: {"rows": [{"row": 2, "reason": "x"}, {"row": 99}, 3]}'
    assert llm_arm.parse(reply, row_count=8) == {1, 2}
    assert llm_arm.parse('{"rows": []}', row_count=8) == set()


@pytest.mark.parametrize("reply", ["no json here", '{"lines": [1]}', '{"rows": 3}'])
def test_parse_rejects_a_reply_in_another_shape(reply):
    with pytest.raises(ValueError):
        llm_arm.parse(reply, row_count=8)


def reviewer(clean_rows=(), blind_to=()):
    """A stand-in model: names the rows that differ from the clean text, except
    the operators' rows listed in blind_to, plus clean_rows on every call."""
    def complete(system, user):
        named = set(clean_rows)
        blocks = user.split("\n\n")
        for number, (block, (a, b)) in enumerate(zip(blocks, ROWS, strict=True), start=1):
            if block != f"Row {number}\nen: {a}\nru: {b}" and number - 1 not in blind_to:
                named.add(number)
        return json.dumps({"rows": [{"row": n, "reason": "differs"} for n in sorted(named)]})
    return complete


def test_compare_document_scores_caught_missed_and_excluded():
    perfect = llm_arm.compare_document(ROWS, 1, reviewer(), per_operator=None)
    assert perfect["clean_rows"] == []
    assert {case["outcome"] for case in perfect["cases"]} == {"caught"}
    blind = llm_arm.compare_document(ROWS, 1, reviewer(blind_to={0}), per_operator=None)
    assert {case["outcome"] for case in blind["cases"] if case["row"] == 0} == {"missed"}
    noisy = llm_arm.compare_document(ROWS, 1, reviewer(clean_rows={1}), per_operator=None)
    assert noisy["clean_rows"] == [0]
    assert {case["outcome"] for case in noisy["cases"] if case["row"] == 0} == {"excluded"}


def test_a_failed_call_is_counted_not_guessed():
    def broken(system, user):
        raise TimeoutError("no answer")
    result = llm_arm.compare_document(ROWS, 1, broken)
    assert result["clean_rows"] is None
    assert {case["outcome"] for case in result["cases"]} == {"failed"}
    summary = llm_arm.summarise([result])
    assert summary["clean_documents_failed"] == 1
    assert all(row["recall"] is None for row in summary["operators"].values())


def test_summarise_gives_recall_per_operator_and_the_noise_rate():
    results = [llm_arm.compare_document(ROWS, 1, reviewer(clean_rows={1}), per_operator=None)]
    summary = llm_arm.summarise(results)
    assert summary["clean_rows_named_per_100_pairs"] == 12.5
    assert summary["extra_rows_named_per_mutated_copy"] == 0
    digit = summary["operators"]["digit"]
    assert digit["recall"] == 1.0 and digit["excluded"] >= 1
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/benchmark/test_llm_arm.py -q`
Expected: collection error, `cannot import name 'llm_arm' from 'benchmark'`.

- [ ] **Step 3: Write the module**

`benchmark/llm_arm.py`:

```python
"""Comparison arm: one model reads the whole document and names the rows that
differ. It is given the same mutated copies the linter was scored on, to test
the claim that rules are the more reliable tool for this class of error."""
from __future__ import annotations

import json
import re

from .mutate import OPERATORS, all_mutations

SYSTEM_PROMPT = """\
You are checking a bilingual contract or official document. Each numbered row
holds the same passage in two languages. Find every row where the two versions
do not say the same thing: a different number, amount, currency, date, period,
reference, name or identifier, a missing or extra passage, or a different
meaning. Ignore style, word order and formatting.
Respond with ONLY a JSON object:
{"rows": [{"row": <row number>, "reason": "<one sentence>"}]}
Use an empty list when every row matches."""


def render(rows: list, langs: tuple = ("en", "ru")) -> str:
    """The document as numbered rows, 1-based, an empty cell shown as (empty)."""
    return "\n\n".join(
        f"Row {number}\n{langs[0]}: {a or '(empty)'}\n{langs[1]}: {b or '(empty)'}"
        for number, (a, b) in enumerate(rows, start=1))


def parse(content: str, row_count: int) -> set:
    """0-based row indexes the model named. Raises ValueError on a reply that
    is not the requested JSON."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in response")
    payload = json.loads(match.group(0))
    if not isinstance(payload.get("rows"), list):
        raise ValueError("no 'rows' list in response")
    named = set()
    for item in payload["rows"]:
        number = item.get("row") if isinstance(item, dict) else item
        if isinstance(number, int) and 1 <= number <= row_count:
            named.add(number - 1)
    return named


def litellm_complete(model: str, timeout: int = 120):
    """A complete(system, user) -> str function backed by litellm."""
    import litellm

    def complete(system: str, user: str) -> str:
        response = litellm.completion(
            model=model, timeout=timeout,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return response.choices[0].message.content

    return complete


def review(rows: list, complete, langs: tuple = ("en", "ru")) -> set | None:
    """Rows the model says differ, or None when the call or the reply failed."""
    try:
        return parse(complete(SYSTEM_PROMPT, render(rows, langs)), len(rows))
    except Exception:
        return None


def compare_document(rows: list, seed: int, complete, parties: dict | None = None,
                     operators: tuple = OPERATORS, per_operator: int | None = 1,
                     langs: tuple = ("en", "ru")) -> dict:
    """Review the clean document, then each mutated copy.

    A defect is caught when the model names the mutated row and had not named
    it on the clean copy. A defect on a row the model already named on the
    clean copy cannot be attributed, so it is marked 'excluded'."""
    clean = review(rows, complete, langs)
    cases = []
    for mutated_rows, mutation in all_mutations(rows, seed, parties, operators, per_operator):
        named = None if clean is None else review(mutated_rows, complete, langs)
        if named is None:
            outcome = "failed"
        elif mutation.row in clean:
            outcome = "excluded"
        else:
            outcome = "caught" if mutation.row in named else "missed"
        cases.append({**mutation.as_dict(), "outcome": outcome,
                      "extra_rows": None if named is None
                      else len(named - clean - {mutation.row})})
    return {"pairs": len(rows), "clean_rows": None if clean is None else sorted(clean),
            "cases": cases}


def summarise(results: list) -> dict:
    """results: compare_document outputs."""
    by_operator: dict = {}
    pairs = clean_rows = clean_failed = extra = scored = 0
    for result in results:
        if result["clean_rows"] is None:
            clean_failed += 1
        else:
            pairs += result["pairs"]
            clean_rows += len(result["clean_rows"])
        for case in result["cases"]:
            row = by_operator.setdefault(
                case["operator"], {"caught": 0, "missed": 0, "excluded": 0, "failed": 0})
            row[case["outcome"]] += 1
            if case["outcome"] in ("caught", "missed"):
                scored += 1
                extra += case["extra_rows"]
    for row in by_operator.values():
        judged = row["caught"] + row["missed"]
        row["recall"] = round(row["caught"] / judged, 4) if judged else None
    return {
        "documents": len(results),
        "clean_documents_failed": clean_failed,
        "operators": {name: by_operator[name] for name in OPERATORS if name in by_operator},
        "clean_rows_named_per_100_pairs": round(100 * clean_rows / pairs, 2) if pairs else None,
        "extra_rows_named_per_mutated_copy": round(extra / scored, 2) if scored else None,
    }
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/benchmark/test_llm_arm.py -q`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add benchmark/llm_arm.py tests/benchmark/test_llm_arm.py
git commit -m "feat(benchmark): whole-document model review as the comparison arm"
```

---

### Task 9: The command line

`holdout` is the only command with conditions: an intact freeze, a clean git tree, no sampling options, and no earlier hold-out result. Each condition has a test that sees it refuse and a test that sees it run.

**Files:**
- Create: `benchmark/run.py`
- Test: `tests/benchmark/test_run.py`

- [ ] **Step 1: Write the failing tests**

`tests/benchmark/test_run.py`:

```python
import json

import pytest

from benchmark import freeze, run

from .helpers import EN, RU, make_set


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Invented UN-format data, a matching freeze, and a git that says 'clean'."""
    data = tmp_path / "data"
    make_set(data, "devset", en_lines=EN, ru_lines=RU)
    make_set(data, "testset", en_lines=EN[::-1], ru_lines=RU[::-1])
    frozen = tmp_path / "FROZEN.json"
    frozen.write_text(json.dumps(freeze.snapshot(data)), encoding="utf-8")
    monkeypatch.setattr(freeze, "FROZEN", frozen)
    monkeypatch.setattr(freeze.problems, "__defaults__", (None, frozen, freeze.MUTATE))
    state = {"dirty": ""}
    monkeypatch.setattr(
        run, "_git", lambda *args: state["dirty"] if args[0] == "status" else "abc1234")
    return {"data": data, "out": tmp_path / "results", "adj": tmp_path / "adjudication",
            "git": state, "lines": []}


def score(tree, part, **kwargs):
    options = {"limit": None, "per_operator": None, **kwargs}
    return run.run_score(part, tree["data"], options["limit"], options["per_operator"],
                         tree["out"], tree["adj"], echo=tree["lines"].append)


def test_dev_run_writes_a_record_with_the_numbers_and_their_provenance(tree):
    assert score(tree, "dev") == 0
    record = json.loads((tree["out"] / "dev.json").read_text(encoding="utf-8"))
    assert record["part"] == "dev" and record["commit"] == "abc1234"
    assert record["data_sha256"] == freeze.set_hash(tree["data"], "devset")
    assert record["summary"]["pairs"] == 8
    assert [row[0] for row in record["targets"]] == list(run.TARGET_LABELS)
    assert any(line.startswith("| Measure | Target | Result | Met |")
               for line in tree["lines"])


def test_holdout_is_scored_once(tree):
    assert score(tree, "holdout") == 0
    assert (tree["out"] / "holdout.json").exists()
    tree["lines"].clear()
    assert score(tree, "holdout") == 2
    assert tree["lines"] == ["refused: the hold-out has already been scored; it is scored once"]


def test_holdout_refuses_sampling_a_dirty_tree_and_a_broken_freeze(tree):
    assert score(tree, "holdout", limit=1) == 2
    tree["git"]["dirty"] = " M benchmark/score.py"
    assert score(tree, "holdout") == 2
    tree["git"]["dirty"] = ""
    target = tree["data"] / "testset" / "UNv1.0.testset.en"
    target.write_bytes(target.read_bytes() + b"One more line.\n")
    assert score(tree, "holdout") == 2
    assert not (tree["out"] / "holdout.json").exists()
    assert "refused: the hold-out is scored whole: no --limit, no --per-operator" in tree["lines"]
    assert "refused: the git tree has uncommitted changes" in tree["lines"]
    assert "refused: the testset files differ from the frozen ones" in tree["lines"]


def test_contracts_need_no_data_and_score_every_operator(tree):
    assert run.run_score("contracts", None, None, 1, tree["out"], tree["adj"],
                         echo=tree["lines"].append) == 0
    record = json.loads((tree["out"] / "contracts.json").read_text(encoding="utf-8"))
    assert record["summary"]["documents"] == 3 and record["data_sha256"] is None
    assert set(record["summary"]["operators"]) == set(run.llm_arm.OPERATORS)


def test_a_verdict_file_moves_a_finding_out_of_the_false_flags(tree):
    make = tree["data"] / "devset" / "UNv1.0.devset.en"
    make.write_text(make.read_text(encoding="utf-8").replace("48 delegations", "49 delegations"),
                    encoding="utf-8", newline="\n")
    assert score(tree, "dev", per_operator=1) == 0
    record = json.loads((tree["out"] / "dev.json").read_text(encoding="utf-8"))
    assert record["adjudication"]["open"] >= 1
    sheet = []
    assert run.run_worksheet("dev", tree["data"], tree["out"], tree["adj"],
                             echo=sheet.append) == 0
    keys = [line[4:-1] for line in sheet[0].splitlines() if line.startswith("## `")]
    tree["adj"].mkdir()
    (tree["adj"] / "dev.json").write_text(
        json.dumps({key: {"verdict": "real", "note": "planted by the test"} for key in keys},
                   ensure_ascii=False), encoding="utf-8")
    assert score(tree, "dev", per_operator=1) == 0
    judged = json.loads((tree["out"] / "dev.json").read_text(encoding="utf-8"))["adjudication"]
    assert judged["open"] == 0 and judged["real"] == len(keys)
    assert judged["false_per_100_pairs"] == 0.0


def test_llm_run_puts_the_model_and_the_linter_side_by_side(tree):
    def complete(system, user):
        return json.dumps({"rows": []})
    assert run.run_llm("dev", tree["data"], 1, "fake/model", tree["out"], complete,
                       echo=tree["lines"].append) == 0
    record = json.loads((tree["out"] / "llm_dev.json").read_text(encoding="utf-8"))
    assert record["model"] == "fake/model" and record["documents"] == 1
    assert record["model_summary"]["operators"]["digit"]["recall"] == 0.0
    assert record["linter_summary"]["operators"]["digit"]["recall_any"] == 1.0


def test_llm_on_the_holdout_waits_for_the_linter_score(tree):
    assert run.run_llm("holdout", tree["data"], 1, "fake/model", tree["out"],
                       lambda s, u: "{}", echo=tree["lines"].append) == 2
    assert tree["lines"] == ["refused: score the hold-out with the linter first"]
```

- [ ] **Step 2: Run them to see them fail**

Run: `python -m pytest tests/benchmark/test_run.py -q`
Expected: collection error, `cannot import name 'run' from 'benchmark'`.

- [ ] **Step 3: Write the module**

`benchmark/run.py`:

```python
"""Run the benchmark.

    python -m benchmark.run dev       --data benchmark/data/testsets
    python -m benchmark.run contracts
    python -m benchmark.run worksheet dev --data benchmark/data/testsets
    python -m benchmark.run llm dev   --data benchmark/data/testsets --llm-docs 25
    python -m benchmark.run holdout   --data benchmark/data/testsets

'holdout' scores the UN test set. It runs once: it needs a clean git tree and
an intact freeze, takes no sampling options, and refuses to run again."""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import bilingual_lint

from . import adjudicate, freeze, llm_arm
from .contracts import CONTRACTS
from .score import score_document, summarise, targets
from .un import documents, load_set, set_hash

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ADJUDICATION = HERE / "adjudication"
SEED = 20261113
UN_PART = {"dev": "devset", "holdout": "testset"}
TARGET_LABELS = {
    "figures_recall": "Recall on planted number, amount, date and identifier defects",
    "paragraphs_recall": "Recall on dropped paragraphs",
    "error_flags_per_100_pairs": "False flags on clean pairs, error severity, per 100 pairs",
    "pairing_accuracy": "Correct pairing in two-file mode",
}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=HERE.parent, capture_output=True,
                          text=True, check=True).stdout.strip()


def load_documents(part: str, data: Path | None) -> tuple:
    """(documents, parties per document, data hash) for dev, holdout or contracts."""
    if part == "contracts":
        return ([c["rows"] for c in CONTRACTS], [c["parties"] for c in CONTRACTS], None)
    if data is None:
        raise SystemExit(f"'{part}' needs --data: the folder that holds devset/ and testset/")
    docs = documents(load_set(data, UN_PART[part]))
    return docs, [None] * len(docs), set_hash(data, UN_PART[part])


def score_all(docs: list, parties: list, per_operator: int | None, echo=print) -> list:
    results = []
    for number, (rows, names) in enumerate(zip(docs, parties, strict=True), start=1):
        results.append(score_document(rows, SEED, names, per_operator=per_operator))
        echo(f"  document {number}/{len(docs)}: {len(results[-1]['cases'])} planted defects")
    return results


def table(summary: dict, target_rows: list) -> str:
    lines = ["| Measure | Target | Result | Met |", "|---|---|---|---|"]
    for name, value, target, met in target_rows:
        shown = "not measured" if value is None else value
        verdict = {True: "yes", False: "no", None: "n/a"}[met]
        sign = "<=" if name == "error_flags_per_100_pairs" else ">="
        lines.append(f"| {TARGET_LABELS[name]} | {sign} {target} | {shown} | {verdict} |")
    lines += ["", "| Planted defect | Planted | Caught | Recall |", "|---|---|---|---|"]
    for name, row in summary["operators"].items():
        lines.append(f"| {name} | {row['planted']} | {row['any']} | {row['recall_any']} |")
    return "\n".join(lines)


def run_score(part: str, data: Path | None, limit: int | None, per_operator: int | None,
              out: Path, adjudication: Path, echo=print) -> int:
    if part == "holdout":
        stop = freeze.problems(data)
        if limit is not None or per_operator is not None:
            stop.append("the hold-out is scored whole: no --limit, no --per-operator")
        if (out / "holdout.json").exists():
            stop.append("the hold-out has already been scored; it is scored once")
        if _git("status", "--porcelain"):
            stop.append("the git tree has uncommitted changes")
        if stop:
            for reason in stop:
                echo(f"refused: {reason}")
            return 2
    docs, parties, data_hash = load_documents(part, data)
    if limit is not None:
        docs, parties = docs[:limit], parties[:limit]
    results = score_all(docs, parties, per_operator, echo)
    summary = summarise(results)
    verdicts = adjudicate.load(adjudication / f"{part}.json")
    judged = adjudicate.tally(results, verdicts)
    target_rows = targets(summary, judged["false_per_100_pairs"])
    record = {
        "part": part, "scored_on": datetime.date.today().isoformat(),
        "commit": _git("rev-parse", "HEAD"), "version": bilingual_lint.__version__,
        "seed": SEED, "limit": limit, "per_operator": per_operator,
        "data_sha256": data_hash, "summary": summary, "adjudication": judged,
        "targets": [list(row) for row in target_rows], "results": results,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{part}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    echo(table(summary, target_rows))
    echo(f"clean text: {judged['error_findings']} error findings — {judged['real']} real "
         f"differences, {judged['false']} false flags, {judged['open']} not yet judged")
    return 0


def run_worksheet(part: str, data: Path | None, out: Path, adjudication: Path,
                  echo=print) -> int:
    record = json.loads((out / f"{part}.json").read_text(encoding="utf-8"))
    docs, _, _ = load_documents(part, data)
    verdicts = adjudicate.load(adjudication / f"{part}.json")
    echo(adjudicate.worksheet(record["results"], docs, verdicts))
    return 0


def run_llm(part: str, data: Path | None, llm_docs: int, model: str, out: Path,
            complete=None, echo=print) -> int:
    if part == "holdout" and not (out / "holdout.json").exists():
        echo("refused: score the hold-out with the linter first")
        return 2
    docs, parties, data_hash = load_documents(part, data)
    docs, parties = docs[:llm_docs], parties[:llm_docs]
    complete = complete or llm_arm.litellm_complete(model)
    model_results, linter_results = [], []
    for number, (rows, names) in enumerate(zip(docs, parties, strict=True), start=1):
        model_results.append(llm_arm.compare_document(rows, SEED, complete, names))
        linter_results.append(score_document(rows, SEED, names, per_operator=1))
        echo(f"  document {number}/{len(docs)}")
    record = {
        "part": part, "scored_on": datetime.date.today().isoformat(), "model": model,
        "seed": SEED, "documents": len(docs), "data_sha256": data_hash,
        "model_summary": llm_arm.summarise(model_results),
        "linter_summary": summarise(linter_results),
        "model_results": model_results,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"llm_{part}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    echo("| Planted defect | Model recall | Linter recall |")
    echo("|---|---|---|")
    for name, row in record["model_summary"]["operators"].items():
        linter = record["linter_summary"]["operators"].get(name, {}).get("recall_any")
        echo(f"| {name} | {row['recall']} | {linter} |")
    return 0


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m benchmark.run", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["dev", "holdout", "contracts", "worksheet", "llm"])
    parser.add_argument("part", nargs="?", choices=["dev", "holdout", "contracts"])
    parser.add_argument("--data", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--per-operator", type=int)
    parser.add_argument("--llm-docs", type=int, default=25)
    parser.add_argument("--model", default="anthropic/claude-sonnet-5")
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--adjudication", type=Path, default=ADJUDICATION)
    args = parser.parse_args(argv)
    if args.command in ("worksheet", "llm") and args.part is None:
        parser.error(f"'{args.command}' needs a part: dev, holdout or contracts")
    if args.command == "worksheet":
        return run_worksheet(args.part, args.data, args.results, args.adjudication)
    if args.command == "llm":
        return run_llm(args.part, args.data, args.llm_docs, args.model, args.results)
    return run_score(args.command, args.data, args.limit, args.per_operator,
                     args.results, args.adjudication)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/benchmark/test_run.py -q`
Expected: 7 passed.

- [ ] **Step 5: Run everything**

```bash
python -m pytest -q
python -m ruff check .
```

Expected: 304 passed (238 existing, 66 new), and `All checks passed!`.

- [ ] **Step 6: Commit**

```bash
git add benchmark/run.py tests/benchmark/test_run.py
git commit -m "feat(benchmark): command line with a once-only hold-out run"
```

---

### Task 10: Score the development set and the contracts

- [ ] **Step 1: Run the development set**

About 40 minutes (100 documents, roughly 100 planted defects each, one DOCX round trip per defect). Run it in the background.

```bash
python -m benchmark.run dev --data benchmark/data/testsets
```

Expected: a line per document, then the target table and the per-defect table; `benchmark/results/dev.json` is written.

- [ ] **Step 2: Print the worksheet**

```bash
python -m benchmark.run worksheet dev --data benchmark/data/testsets > dev_worksheet.md
```

`dev_worksheet.md` is a scratch file: do not commit it.

- [ ] **Step 3: Give every finding a verdict**

Read each entry (both texts are shown) and write `benchmark/adjudication/dev.json`. The key is the text between the backticks in the worksheet heading. Shape:

```json
{
  "0|5|BI001|numbers differ — en only: 100,000 · ru only: 10 000": {
    "verdict": "real",
    "note": "English says per 100,000 live births, Russian says per 10 000"
  },
  "0|19|BI003|times differ — en only: 11 a.m.": {
    "verdict": "false",
    "note": "same time: Russian writes 11 ч. 00 м."
  }
}
```

The test for a verdict: would a lawyer comparing the two versions want this row pointed out because the two versions state different facts? If yes, `real`. If the two versions state the same fact in different notation, `false`. If unsure, `false`.

- [ ] **Step 4: Rerun so the record carries the verdicts**

```bash
python -m benchmark.run dev --data benchmark/data/testsets
```

Expected: the last line reports 0 findings not yet judged.

- [ ] **Step 5: Run the contracts**

```bash
python -m benchmark.run contracts
python -m benchmark.run worksheet contracts
```

Give verdicts in `benchmark/adjudication/contracts.json` the same way (the contracts have no real differences, so every verdict there is `false`), then rerun `python -m benchmark.run contracts`.

- [ ] **Step 6: Commit**

```bash
git add benchmark/results/dev.json benchmark/results/contracts.json benchmark/adjudication/
git commit -m "bench: development-set and contract results for 0.1.1, with verdicts"
```

- [ ] **Step 7: Report to the maintainer and ask one question**

Report the four targets for the development set, the per-defect table, the count of real differences found in UN text, and the kinds of false flag. Then ask: tune the linter on the development set before the hold-out is scored (Task 11), or score the hold-out on 0.1.1 as it stands (skip to Task 12)?

---

### Task 11: Tune on the development set (only if the maintainer chose it)

Each change is a change to the linter under `src/bilingual_lint/`, made test-first in the existing test suite, never in `benchmark/`. One kind of false flag or miss per commit.

The kinds seen in the trial, in the order to take them:

1. **Clock times in two notations.** "11 a.m." against "11 ч. 00 м." and "3 p.m." against "15 ч. 00 м." draw BI003 ("times differ") and BI001 ("numbers differ"); "12.40" against "12 ч. 40 м." draws BI001. The time extractor should read `N ч. MM м.` as a time and compare times as minutes after midnight, and BI001 should not count digits that a recognised time already covers.
2. **A date range where one language repeats a part.** "from 3 to 5 February and ... 30 April 2015" against "с 3 по 5 февраля 2015 года ... 30 апреля 2015 года" draws BI003 and BI001.
3. **Negation carried by another word.** "No reform ... can" against "Ни одна реформа ... не может": dropping "не" is not reported. BI011 is an info-level hint; widening it is optional.

- [ ] **Step 1: For the chosen kind, write a failing test** in `tests/facts/` or `tests/rules/` next to the existing tests for that extractor or rule, using an invented sentence pair of the same shape (not UN text). Pair it with a test that a true difference of the same shape is still reported: for clock times, "11 a.m." against "12 ч. 00 м." must still be an error.

- [ ] **Step 2: Run it to see it fail**, then make the smallest change that passes.

- [ ] **Step 3: Run the whole suite and the frozen guard**

```bash
python -m pytest -q
python -m ruff check .
```

Expected: all pass, including `test_the_mutation_tool_is_unchanged_since_the_freeze` and the golden reports under `tests/golden/`.

- [ ] **Step 4: Commit the change**, then repeat Steps 1 to 4 for the next kind.

- [ ] **Step 5: Rescore the development set**

```bash
python -m benchmark.run dev --data benchmark/data/testsets
python -m benchmark.run contracts
```

Verdict keys include the finding's message, so a finding whose wording changed needs a new verdict: run the worksheet again and judge what it lists.

- [ ] **Step 6: Stop when** the development set meets the four targets, or when two rounds in a row bring no gain. Do not keep going past either point. Commit the results:

```bash
git add benchmark/results/ benchmark/adjudication/
git commit -m "bench: development-set results after tuning"
```

---

### Task 12: Model comparison on the development set

This step spends money on a model API and needs a key. Ask the maintainer for a go first, and state the size: 25 documents, about 6 calls each (one clean copy, one copy per kind of defect present), each call a 40-row document, about one million input tokens in total. The key is read from the environment by litellm (`ANTHROPIC_API_KEY` for the default model); never write it to a file or print it.

- [ ] **Step 1: Install the extra**

```bash
python -m pip install -e ".[llm]"
```

- [ ] **Step 2: Run**

```bash
python -m benchmark.run llm dev --data benchmark/data/testsets --llm-docs 25
```

Expected: a line per document, then a table of model recall against linter recall per kind of defect on the same copies; `benchmark/results/llm_dev.json` is written.

- [ ] **Step 3: Check the run was sound**

Open `benchmark/results/llm_dev.json`: `model_summary.clean_documents_failed` must be 0 and no operator may have `failed` above 0. If calls failed, delete the file and rerun; do not publish a run with failed calls.

- [ ] **Step 4: Commit**

```bash
git add benchmark/results/llm_dev.json
git commit -m "bench: model comparison on the development set"
```

---

### Task 13: The hold-out, once

- [ ] **Step 1: Check the conditions before spending the run**

```bash
git status --short
python -m pytest tests/benchmark/test_frozen.py -q
```

Expected: no output from git, 1 passed.

- [ ] **Step 2: Score the hold-out**

About 40 minutes. Run it in the background and do not interrupt it.

```bash
python -m benchmark.run holdout --data benchmark/data/testsets
```

Expected: the two tables; `benchmark/results/holdout.json` exists. A second run prints `refused: the hold-out has already been scored; it is scored once`.

- [ ] **Step 3: Commit the raw result before reading anything else**

```bash
git add benchmark/results/holdout.json
git commit -m "bench: hold-out result, scored once"
```

- [ ] **Step 4: Give verdicts on the hold-out's clean findings**

```bash
python -m benchmark.run worksheet holdout --data benchmark/data/testsets > holdout_worksheet.md
```

Write `benchmark/adjudication/holdout.json` as in Task 10. The verdicts change one number only, the adjudicated false-flag rate. Recompute it without rescoring:

```bash
python -c "import json; from pathlib import Path; from benchmark import adjudicate as a; r = json.loads(Path('benchmark/results/holdout.json').read_text(encoding='utf-8')); print(a.tally(r['results'], a.load(Path('benchmark/adjudication/holdout.json'))))"
```

Record the printed dictionary for the README. From this point the hold-out has been read: no rule may be tuned against it, and any later tuning needs a new hold-out drawn from other documents.

- [ ] **Step 5: Model comparison on the hold-out** (same cost and same go as Task 12)

```bash
python -m benchmark.run llm holdout --data benchmark/data/testsets --llm-docs 25
```

Check for failed calls as in Task 12, Step 3.

- [ ] **Step 6: Commit**

```bash
git add benchmark/adjudication/holdout.json benchmark/results/llm_holdout.json
git commit -m "bench: hold-out verdicts and model comparison"
```

---

### Task 14: Publish the numbers

**Files:**
- Create: `NOTICE`, `benchmark/README.md`
- Modify: `README.md`, `CHANGELOG.md`

- [ ] **Step 1: Write `NOTICE`**

```
bilingual-lint benchmark: third-party data

The benchmark in benchmark/ is scored on the development and test sets of the
United Nations Parallel Corpus v1.0. The data is not distributed with this
repository. Source of the information: the United Nations.

Reference:
Ziemski, M., Junczys-Dowmunt, M., and Pouliquen, B. (2016). The United Nations
Parallel Corpus. Language Resources and Evaluation (LREC'16), Portorož,
Slovenia, May 2016.

The corpus is published at https://conferences.unite.un.org/UNCorpus under the
following disclaimer, which applies to any use of it:

The United Nations Parallel Corpus is made available without warranty of any
kind, explicit or implied. The United Nations specifically makes no warranties
or representations as to the accuracy or completeness of the information
contained in the United Nations corpus.

Under no circumstances shall the United Nations be liable for any loss,
liability, injury or damage incurred or suffered that is claimed to have
resulted from the use of the United Nations Corpus. The use of the United
Nations Corpus is at the user's sole risk. The user specifically acknowledges
and agrees that the United Nations is not liable for the conduct of any user.
If the user is dissatisfied with any of the material provided in the United
Nations Corpus, the user's sole and exclusive remedy is to discontinue using
the United Nations Corpus.

When using the United Nations Corpus, the user must acknowledge the United
Nations as the source of the information.

Nothing herein shall constitute or be considered to be a limitation upon or
waiver, express or implied, of the privileges and immunities of the United
Nations, which are specifically reserved.

The benchmark results do not come from the United Nations and are not endorsed
by it. The contracts in benchmark/contracts.py are invented.
```

- [ ] **Step 2: Write `benchmark/README.md`**

````markdown
# Benchmark

How often does bilingual-lint catch a planted defect, and how often does it
flag text that has none? This folder holds the tool that plants the defects,
the scorer, the results and everything needed to run it again.

## Method

- **Text.** English and Russian from the development and test sets of the
  United Nations Parallel Corpus v1.0: 4,000 aligned sentences each, from
  official documents of 2015. The sets are samples, so a benchmark document is
  a block of 40 consecutive sentences: 100 documents per set.
- **Planted defects.** `mutate.py` changes one thing on one side of one row: a
  digit, the day of a date, a clause reference, a currency, a day type
  ("business days" to "days"), a negation, the prevailing language, an
  identifier, a party name, or a whole paragraph. It uses the standard library
  only and shares no code with the linter.
- **A catch.** Each copy is written to a DOCX and linted the way a user's file
  is. A defect is caught when the linter says something about the changed row
  that it did not say about the clean copy.
- **Clean text.** Error-level findings on unmodified text were read by a person
  and marked as a false flag or as a real difference between the two published
  versions. A finding nobody judged counts as a false flag.
- **Protocol.** `mutate.py` and both sets were pinned by hash in `FROZEN.json`
  before any rule was tuned. The development set was used for tuning. The test
  set is the hold-out: the tool refuses to score it twice.
- **Comparison.** A model was given the same mutated copies as whole documents
  and asked to name the rows that differ.
- **Contracts.** UN documents have almost no prices, bank details, party names
  or prevailing-language clauses. Those defects are planted in three invented
  contracts (`contracts.py`). The contracts were written by the author of the
  rules, so that result is weaker evidence and is reported on its own.

## Limits

- The text is UN prose, not contracts. Contract-only defects rest on 45
  invented rows.
- One language pair. Defects are planted in two-column DOCX files; two-file
  mode is used for the pairing measure only.
- One model, one run, one prompt for the comparison.
- While the archive's format was inspected, six sentences of the test set were
  printed and seven pattern counts were taken over its English file. No linter
  was run on it and no code changed because of it.
- The verdicts on clean text are one reader's.

## Run it again

The UN server refuses automated downloads, so fetch the archive in a browser:
<https://www.un.org/dgacm/sites/www.un.org.dgacm/files/files/UNCORPUS/UNv1.0.testsets.tar.gz>

```bash
mkdir -p benchmark/data && cp UNv1.0.testsets.tar.gz benchmark/data/
cd benchmark/data && tar -xzf UNv1.0.testsets.tar.gz && cd ../..
python -m pytest tests/benchmark/test_frozen.py -q
python -m benchmark.run dev --data benchmark/data/testsets
python -m benchmark.run contracts
```

`FROZEN.json` holds the SHA-256 of the archive and of each set. The hold-out
result in `results/holdout.json` records the commit it was scored at; to
reproduce it, check out that commit, delete the result file and run
`python -m benchmark.run holdout --data benchmark/data/testsets`.

The data belongs to the United Nations Parallel Corpus; see `NOTICE` in the
repository root for the attribution and the disclaimer.
````

- [ ] **Step 3: Add the results to the main `README.md`**

Add a section `## Benchmark` before the section on contributing or licence, whichever comes first. It has four parts, each filled from the committed result files, with no rounding beyond what the files hold:

1. One paragraph: what was measured and on what (UN Parallel Corpus v1.0 test set, 4,000 EN/RU sentence pairs, 100 documents; defects planted by a tool frozen before tuning; scored once at commit `<commit from holdout.json>`), with a link to `benchmark/README.md`.
2. The target table printed by the hold-out run, with the false-flag row taken from the adjudicated tally of Task 13, Step 4, and the raw rate stated in the sentence under it together with the number of real differences found in the UN text.
3. The per-defect table for the hold-out, then, under the heading "Invented contracts (45 rows, weaker evidence)", the per-defect table from `results/contracts.json`.
4. The model comparison table from `results/llm_holdout.json`, with the model name, the number of documents, and the two noise rates.

Under the tables write one sentence for every target that was missed, starting "Missed:", naming the target, the result and the main cause. If no target was missed, write "All four targets were met on the hold-out." Do not soften a miss and do not explain it away.

- [ ] **Step 4: Add a changelog entry** at the top of `CHANGELOG.md` under a new `## Unreleased` heading:

```markdown
## Unreleased

- Benchmark published: planted-defect recall, false flags on clean text and
  two-file pairing, measured on the United Nations Parallel Corpus v1.0 and on
  invented contracts, with a whole-document model review for comparison. See
  `benchmark/README.md`.
```

If Task 11 changed the linter, list each change as its own bullet in the same entry.

- [ ] **Step 5: Verify the tree**

```bash
python -m pytest -q
python -m ruff check .
python -m build
python -c "import zipfile, glob; names = zipfile.ZipFile(sorted(glob.glob('dist/*.whl'))[-1]).namelist(); print([n for n in names if 'benchmark' in n])"
git status --short
```

Expected: all tests pass, including the internal-terms guard over the new files; ruff is clean; the wheel lists no `benchmark` file (prints `[]`); git shows only the files of this task, and nothing under `benchmark/data/`.

- [ ] **Step 6: Commit**

```bash
git add NOTICE benchmark/README.md README.md CHANGELOG.md
git commit -m "docs: publish the benchmark results and the UN corpus notice"
```

- [ ] **Step 7: Hand back to the maintainer**

Report the four hold-out targets with met or missed, the contract table, the model comparison, and anything that did not go to plan. Merging to `main`, the version number, the tag and the push are the maintainer's decisions.

---

## Self-review

**Spec section 9, line by line.**

| Requirement | Where |
|---|---|
| Public EN/RU texts whose licence allows reuse; no client or firm documents | "What is already known"; Task 1; `NOTICE` in Task 14 |
| One change per copy: digit, currency, date, day type, clause reference, dropped paragraph, swapped party, flipped prevailing-language clause, dropped negation | Task 2 (plus an identifier operator, which the recall target names) |
| Mutation tool frozen before tuning, sharing no code with the extractors | Task 2 (`test_the_tool_shares_no_code_with_the_linter`); Task 7 |
| Clean arm; real discrepancies adjudicated by hand and reported separately | Tasks 6, 10, 13 |
| Development set for tuning; hold-out pinned by hash and scored once | Tasks 7, 9, 11, 13 |
| Reading hold-out failures means pinning a new hold-out | Task 13, Step 4; `benchmark/README.md` |
| One whole-document model review of the same mutated files | Tasks 8, 12, 13 |
| Four targets fixed before scoring | `TARGETS` in Task 5, values copied from the spec |
| If a target is missed, the README says so | Task 14, Step 3 |

**Gaps against the spec, stated plainly.**

- The spec names "dropped or extra paragraphs". The tool plants dropped paragraphs on either side; a paragraph dropped from side A is an extra paragraph on side B, so both directions are covered, but no operator invents new text.
- The spec's source list included WIPO treaty texts. Their reuse terms could not be confirmed, so they are not used.
- Contract-only defects are measured on invented text written by the rules' author. The README says so and keeps those numbers apart.

**Consistency.** `score_document` returns `pairs`, `clean_findings`, `cases`, `pairing`, `pairing_one_missing`; `summarise`, `adjudicate.tally` and `run` read exactly those keys. A finding is `(rule_id, severity, row, message)` everywhere, a list of four after a JSON round trip, and `adjudicate.key` unpacks four. `all_mutations(rows, seed, parties, operators, per_operator)` is called with the same seed and `per_operator=1` by the model arm and by its linter counterpart, so both see the same copies.
