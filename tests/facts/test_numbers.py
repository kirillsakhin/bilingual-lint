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
