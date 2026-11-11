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
