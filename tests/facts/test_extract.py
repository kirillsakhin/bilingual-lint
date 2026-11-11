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
