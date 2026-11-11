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
