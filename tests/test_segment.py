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
