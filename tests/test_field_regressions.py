"""Regressions found by running the linter over real two-column documents.

Every sentence below is invented; only the pattern that tripped the linter is
kept. Each false alarm has a twin test showing the real defect is still caught.
"""
from bilingual_lint.models import Severity
from bilingual_lint.rules.bi001_numbers import NumbersDiffer
from bilingual_lint.rules.bi002_money import AmountsDiffer
from bilingual_lint.rules.bi003_dates import DatesDiffer
from bilingual_lint.rules.bi006_refs import ReferencesDiffer
from bilingual_lint.rules.bi007_structure import SegmentsDiffer
from bilingual_lint.rules.bi008_terms import TermsDiffer
from bilingual_lint.rules.bi011_modality import ModalityDiffers, cues

from .helpers import check

# --- a number glued to "No." ------------------------------------------------

def test_number_glued_to_no_dot_is_read():
    rows = [("Agreement No.15 applies.", "Применяется договор №15.")]
    assert check(NumbersDiffer, rows) == []


def test_number_glued_to_no_dot_is_still_compared():
    rows = [("Agreement No.15 applies.", "Применяется договор №16.")]
    (finding,) = check(NumbersDiffer, rows)
    assert finding.context == {"only_a": ["15"], "only_b": ["16"]}


def test_inner_parts_of_a_dotted_number_are_not_separate_numbers():
    rows = [("Version 1.2.3 applies.", "Применяется версия 1.2.3.")]
    assert check(NumbersDiffer, rows) == []


# --- time of day -------------------------------------------------------------

def test_time_of_day_24h_against_pm():
    rows = [("The office closes at 9 p.m. local time.",
             "Офис закрывается в 21:00 по местному времени.")]
    assert check(NumbersDiffer, rows) == []
    assert check(DatesDiffer, rows) == []


def test_time_of_day_differs():
    rows = [("The office closes at 8 p.m. local time.",
             "Офис закрывается в 21:00 по местному времени.")]
    assert check(NumbersDiffer, rows) == []
    (finding,) = check(DatesDiffer, rows)
    assert finding.severity is Severity.ERROR
    assert finding.message == "times differ — en only: 8 p.m. · ru only: 21:00"


# --- clause references -------------------------------------------------------

def test_reference_keyword_in_genitive_plural():
    rows = [("As set out in Articles 2.3 and 8.4.", "На основании Статей 2.3 и 8.4.")]
    assert check(ReferencesDiffer, rows) == []
    assert check(NumbersDiffer, rows) == []


def test_subparagraph_is_a_reference_keyword():
    rows = [("Exempt under subparagraph 14 of the Code.", "Освобождено по пп. 14 Кодекса.")]
    assert check(ReferencesDiffer, rows) == []
    assert check(NumbersDiffer, rows) == []


def test_reference_on_one_side_bare_number_on_the_other():
    rows = [("Exempt under item 14, para. 3, article 149.",
             "Освобождено на основании пп. 14 п. 3 статьи 149.")]
    assert check(ReferencesDiffer, rows) == []
    assert check(NumbersDiffer, rows) == []


def test_reference_against_a_different_bare_number_is_still_reported():
    rows = [("Exempt under item 14, para. 4, article 149.",
             "Освобождено на основании пп. 14 п. 3 статьи 149.")]
    (ref,) = check(ReferencesDiffer, rows)
    assert ref.message == "cross-references differ — ru only: 3"
    (num,) = check(NumbersDiffer, rows)
    assert num.message == "numbers differ — en only: 4"


# --- currency named without an amount ---------------------------------------

def test_currency_named_without_amount_clean():
    rows = [("Payment shall be made in U.S. dollars.", "Оплата производится в долларах США.")]
    assert check(AmountsDiffer, rows) == []


def test_currency_named_without_amount_differs():
    rows = [("Payment shall be made in euros.", "Оплата производится в долларах США.")]
    (finding,) = check(AmountsDiffer, rows)
    assert finding.severity is Severity.WARNING
    assert finding.message == "currencies named differ — en: EUR · ru: USD"


def test_currency_of_an_amount_is_reported_once():
    rows = [("The Buyer pays USD 100.", "Покупатель уплачивает 100 евро.")]
    (finding,) = check(AmountsDiffer, rows)
    assert finding.message.startswith("currency differs")


# --- untranslated text -------------------------------------------------------

def test_latin_name_kept_on_the_russian_side_is_not_untranslated():
    rows = [("Beneficiary bank: Northwind Trade Bank AG, Vienna",
             "Банк получателя: Northwind Trade Bank AG, Vienna")]
    assert check(SegmentsDiffer, rows) == []


def test_cell_left_wholly_in_english_is_still_reported():
    rows = [("Beneficiary bank: Northwind Trade Bank AG, Vienna",
             "Beneficiary bank: Northwind Trade Bank AG, Vienna")]
    (finding,) = check(SegmentsDiffer, rows)
    assert "ru side does not look like ru" in finding.message


def test_cyrillic_address_left_on_the_english_side_is_still_reported():
    rows = [("Address: г. Северск, ул. Тестовая, дом 1",
             "Адрес: г. Северск, ул. Тестовая, дом 1")]
    (finding,) = check(SegmentsDiffer, rows)
    assert "en side does not look like en" in finding.message


# --- defined terms -----------------------------------------------------------

DEFINE_ORDERS = ('Tasks issued by the Buyer (the "Orders").',
                 'Задания Покупателя (далее – «Заказы»).')
DEFINE_AGENT = ('The person named below (the "Representative").',
                'Указанное ниже лицо (далее – «Представитель»).')


def test_term_defined_in_plural_matches_singular_use():
    rows = [DEFINE_ORDERS, ("Each Order is binding.", "Каждый Заказ обязателен.")]
    assert check(TermsDiffer, rows) == []


def test_term_defined_in_plural_still_catches_a_missing_term():
    rows = [DEFINE_ORDERS, ("Each Order is binding.", "Каждое поручение обязательно.")]
    (finding,) = check(TermsDiffer, rows)
    assert 'term "Orders" is used' in finding.message


def test_capitalised_term_does_not_match_the_common_noun():
    rows = [DEFINE_AGENT,
            ("To take part in all proceedings.",
             "Участвовать в качестве представителя во всех процедурах.")]
    assert check(TermsDiffer, rows) == []


def test_capitalised_term_matches_all_capitals():
    rows = [DEFINE_AGENT, ("THE REPRESENTATIVE", "ПРЕДСТАВИТЕЛЬ")]
    assert check(TermsDiffer, rows) == []


# --- obligation and negation cues -------------------------------------------

def test_numero_sign_is_not_a_negation():
    for text in ("Assignment No 1 to the Agreement", "court case No. A40-1/2026",
                 "Agreement No.15 of this year"):
        assert cues(text, "en")["negation"] is False, text


def test_plain_no_is_still_a_negation():
    assert cues("There is no delay.", "en")["negation"] is True


def test_unless_pairs_with_a_russian_negation():
    rows = [("Unless otherwise agreed by the Parties, the Buyer pays.",
             "Если иное не согласовано Сторонами, Покупатель платит.")]
    assert check(ModalityDiffers, rows) == []


def test_absence_wording_pairs_with_no():
    rows = [("The Seller confirms that there is no conflict.",
             "Продавец подтверждает отсутствие конфликта.")]
    assert check(ModalityDiffers, rows) == []


def test_lack_pairs_with_a_russian_absence():
    rows = [("CONFIRMATION OF LACK OF DEFECTS", "ПОДТВЕРЖДЕНИЕ ОТСУТСТВИЯ НЕДОСТАТКОВ")]
    assert check(ModalityDiffers, rows) == []


def test_shall_be_entitled_is_a_permission():
    rows = [("The Manager shall be entitled to replace the adviser.",
             "Управляющий вправе заменить консультанта.")]
    assert check(ModalityDiffers, rows) == []


def test_plain_shall_against_a_permission_is_still_reported():
    rows = [("The Manager shall replace the adviser.",
             "Управляющий вправе заменить консультанта.")]
    (finding,) = check(ModalityDiffers, rows)
    assert "obligation on the en side" in finding.message


# --- clock times in hour-and-minute notation ---------------------------------

def test_am_time_against_russian_hours_and_minutes():
    rows = [("The hearing opens on Monday at 11 a.m.",
             "Слушание начнется в понедельник в 11 ч. 00 м.")]
    assert check(NumbersDiffer, rows) == []
    assert check(DatesDiffer, rows) == []


def test_pm_time_against_russian_hours_and_minutes():
    rows = [("The hearing opens at 3 p.m. and closes at 6:15 p.m.",
             "Слушание начнется в 15 ч. 00 м. и закончится в 18 ч. 15 м.")]
    assert check(NumbersDiffer, rows) == []
    assert check(DatesDiffer, rows) == []


def test_time_written_with_a_dot_before_pm():
    rows = [("The hearing opens at 12.40 p.m.", "Слушание начнется в 12 ч. 40 м.")]
    assert check(NumbersDiffer, rows) == []
    assert check(DatesDiffer, rows) == []


def test_a_range_of_russian_clock_times():
    rows = [("The office is open from 10 a.m. to 1 p.m.",
             "Офис открыт с 10 ч. 00 м. до 13 ч. 00 м.")]
    assert check(NumbersDiffer, rows) == []
    assert check(DatesDiffer, rows) == []


def test_russian_hours_and_minutes_that_differ_are_reported():
    rows = [("The hearing opens on Monday at 11 a.m.",
             "Слушание начнется в понедельник в 12 ч. 00 м.")]
    (finding,) = check(DatesDiffer, rows)
    assert finding.severity is Severity.ERROR
    assert finding.message == "times differ — en only: 11 a.m. · ru only: 12 ч. 00 м."


def test_dotted_time_that_differs_is_reported():
    rows = [("The hearing opens at 10.10 a.m.", "Слушание начнется в 10 ч. 00 м.")]
    (finding,) = check(DatesDiffer, rows)
    assert finding.message == "times differ — en only: 10.10 a.m. · ru only: 10 ч. 00 м."


def test_a_russian_length_of_time_is_not_a_clock_time():
    rows = [("The test lasts 3 hours 15 minutes.", "Испытание длится 3 ч. 15 м.")]
    assert check(DatesDiffer, rows) == []
