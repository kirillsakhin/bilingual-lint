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
