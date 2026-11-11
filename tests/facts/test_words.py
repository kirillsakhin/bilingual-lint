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
