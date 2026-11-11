from bilingual_lint.models import Segment
from bilingual_lint.pairing import find_anchors, pair_segments


def segs(lang, texts):
    return [Segment(t, lang, i, f"paragraph {i + 1}") for i, t in enumerate(texts)]


EN = [
    "1. Subject",
    "The Seller shall deliver the goods to the Buyer within the agreed time.",
    "2. Price",
    "The price of the goods is 150,000 US dollars, payable within 30 days.",
    "3. Liability",
    "Each party is liable for its own breach of this agreement.",
]
RU = [
    "1. Предмет",
    "Продавец обязуется поставить товар Покупателю в согласованный срок.",
    "2. Цена",
    "Цена товара составляет 150 000 долларов США и уплачивается в течение 30 дней.",
    "3. Ответственность",
    "Каждая сторона отвечает за собственное нарушение настоящего договора.",
]


def shape(pairs):
    return [(p.a.index if p.a else None, p.b.index if p.b else None) for p in pairs]


def test_identical_structure_pairs_one_to_one():
    pairs = pair_segments(segs("en", EN), segs("ru", RU))
    assert shape(pairs) == [(i, i) for i in range(6)]
    assert [p.pair_no for p in pairs] == [1, 2, 3, 4, 5, 6]
    assert all(p.confidence >= 0.5 for p in pairs)


def test_anchors_use_clause_numbers_and_digit_signatures():
    anchors = find_anchors(segs("en", EN), segs("ru", RU))
    assert anchors == [(0, 0), (2, 2), (3, 3), (4, 4)]


def test_missing_paragraph_becomes_an_unpaired_segment():
    extra = "This additional sentence exists only in the English version of the text."
    en = EN[:2] + [extra] + EN[2:]
    pairs = pair_segments(segs("en", en), segs("ru", RU))
    assert shape(pairs) == [(0, 0), (1, 1), (2, None), (3, 2), (4, 3), (5, 4), (6, 5)]


def test_paragraph_split_in_two_is_merged():
    first = "The Seller shall deliver the goods to the Buyer"
    second = "within the agreed time and at the agreed place."
    en = [EN[0], first, second] + EN[2:]
    ru = list(RU)
    ru[1] = "Продавец обязуется поставить товар Покупателю в согласованный срок и в месте."
    pairs = pair_segments(segs("en", en), segs("ru", ru))
    assert shape(pairs)[:3] == [(0, 0), (1, 1), (3, 2)]
    assert pairs[1].a.text == first + " " + second
    assert pairs[1].a.location == "paragraph 2–paragraph 3"


def test_no_anchors_still_aligns_by_length():
    en = ["Short title", "A considerably longer paragraph of contract text goes here."]
    ru = ["Заголовок", "Здесь находится значительно более длинный абзац текста договора."]
    assert shape(pair_segments(segs("en", en), segs("ru", ru))) == [(0, 0), (1, 1)]


def test_empty_side_returns_everything_unpaired():
    pairs = pair_segments(segs("en", EN[:2]), [])
    assert shape(pairs) == [(0, None), (1, None)]
