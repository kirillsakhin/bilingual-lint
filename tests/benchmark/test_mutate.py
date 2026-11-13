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
