from bilingual_lint.text_utils import clean, letters, script_for_lang, script_of


def test_script_of():
    assert script_of("The Buyer shall pay") == "latin"
    assert script_of("Покупатель оплачивает") == "cyrillic"
    assert script_of("ООО «Альфа» и Beta GmbH договорились") == "cyrillic"
    assert script_of("Préstamo en España") == "latin"
    assert script_of("合同") == "other"
    assert script_of("12 345 — 67%") == "none"


def test_script_for_lang():
    assert script_for_lang("ru") == "cyrillic"
    assert script_for_lang("en") == "latin"
    assert script_for_lang("es") == "latin"


def test_letters_counts_only_letters():
    assert letters("No. 15, п. 2") == 3


def test_clean_keeps_line_breaks_and_no_break_spaces():
    assert clean("  a \t b  \n\n  c d ") == "a b\nc d"
