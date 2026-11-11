import copy

import pytest
from docx import Document as new_docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from bilingual_lint.loaders import LoaderError, load
from bilingual_lint.loaders.docx_reader import read_docx
from bilingual_lint.loaders.two_column import pick_columns

from .helpers import write_plain, write_two_column

ROWS = [
    ("1. Subject", "1. Предмет"),
    ("The Seller shall deliver the goods.", "Продавец обязуется поставить товар."),
]


def _run(text: str):
    run = OxmlElement("w:r")
    node = OxmlElement("w:t")
    node.text = text
    run.append(node)
    return run


def _tracked(paragraph, tag: str, text: str) -> None:
    """Append a tracked insertion (w:ins) or deletion (w:del) to a paragraph."""
    wrapper = OxmlElement(tag)
    wrapper.set(qn("w:id"), "1")
    wrapper.set(qn("w:author"), "Reviewer")
    run = _run(text)
    if tag == "w:del":
        run[0].tag = qn("w:delText")
    wrapper.append(run)
    paragraph._p.append(wrapper)


# --- docx_reader -----------------------------------------------------------

def test_blocks_come_back_in_document_order(tmp_path):
    path = write_two_column(tmp_path / "a.docx", ROWS, intro="SUPPLY AGREEMENT")
    blocks, notes = read_docx(path)
    assert [b.kind for b in blocks] == ["paragraph", "table"]
    assert blocks[0].text == "SUPPLY AGREEMENT" and blocks[0].location == "paragraph 1"
    assert blocks[1].rows == [{0: a, 1: b} for a, b in ROWS]
    assert notes == []


def test_tracked_changes_are_read_as_accepted(tmp_path):
    document = new_docx()
    paragraph = document.add_paragraph("The price is ")
    _tracked(paragraph, "w:del", "100")
    _tracked(paragraph, "w:ins", "200")
    paragraph._p.append(_run(" dollars."))
    path = tmp_path / "tracked.docx"
    document.save(str(path))
    blocks, notes = read_docx(path)
    assert blocks[0].text == "The price is 200 dollars."
    assert len(notes) == 1 and "tracked changes" in notes[0]


def test_merged_cell_keeps_its_grid_column(tmp_path):
    document = new_docx()
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "Heading across both columns"
    table.cell(1, 0).text, table.cell(1, 1).text = "Left", "Правый"
    path = tmp_path / "merged.docx"
    document.save(str(path))
    blocks, _ = read_docx(path)
    assert blocks[0].rows == [{0: "Heading across both columns"}, {0: "Left", 1: "Правый"}]


def test_multi_paragraph_cell_keeps_line_breaks(tmp_path):
    document = new_docx()
    cell = document.add_table(rows=1, cols=2).cell(0, 0)
    cell.text = "First line"
    cell.add_paragraph("Second line")
    path = tmp_path / "lines.docx"
    document.save(str(path))
    blocks, _ = read_docx(path)
    assert blocks[0].rows[0][0] == "First line\nSecond line"


@pytest.mark.parametrize("content, fragment", [
    (bytes.fromhex("d0cf11e0a1b11ae1") + b"x" * 64, "password-protected"),
    (b"just some text", "not a DOCX"),
    (b"PK\x03\x04 broken zip", "cannot read"),
])
def test_unreadable_files_are_refused_with_a_reason(tmp_path, content, fragment):
    path = tmp_path / "bad.docx"
    path.write_bytes(content)
    with pytest.raises(LoaderError, match=fragment):
        read_docx(path)


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(LoaderError, match="file not found"):
        read_docx(tmp_path / "nope.docx")


# --- two-column ------------------------------------------------------------

def test_pick_columns_by_script():
    rows = [{0: "1.", 1: "The Seller delivers", 2: "Продавец поставляет"}]
    assert pick_columns(rows, None) == (1, 2, "en", "ru")
    flipped = [{0: "Продавец поставляет", 1: "The Seller delivers"}]
    assert pick_columns(flipped, None) == (0, 1, "ru", "en")


def test_pick_columns_same_script_needs_langs():
    rows = [{0: "The Seller delivers", 1: "El Vendedor entrega"}]
    assert pick_columns(rows, None) is None
    assert pick_columns(rows, ("en", "es")) == (0, 1, "en", "es")


def test_pick_columns_rejects_single_language_table():
    assert pick_columns([{0: "Item", 1: "Price"}], None) is None


def test_two_column_document(tmp_path):
    path = write_two_column(tmp_path / "c.docx", ROWS, intro="Title outside the table")
    doc = load([path])
    assert (doc.lang_a, doc.lang_b, doc.mode) == ("en", "ru", "two-column")
    assert [(p.a.text, p.b.text) for p in doc.pairs] == ROWS
    assert doc.pairs[1].a.location == "table 1, row 2"
    assert [n.rule_id for n in doc.notes] == ["BI000"]
    assert "1 block(s) of text outside" in doc.notes[0].message


def test_empty_cell_is_kept_as_a_pair(tmp_path):
    path = write_two_column(tmp_path / "e.docx", ROWS + [("3. Signatures", "")])
    doc = load([path])
    assert doc.pairs[2].a.text == "3. Signatures" and doc.pairs[2].b.text == ""
    assert not doc.pairs[2].complete


def test_file_without_bilingual_table_is_refused(tmp_path):
    path = write_plain(tmp_path / "p.docx", ["Only English text here."])
    with pytest.raises(LoaderError, match="no two-language table"):
        load([path])


# --- two files -------------------------------------------------------------

def test_two_files_are_paired(tmp_path):
    en = write_plain(tmp_path / "en.docx", [a for a, _ in ROWS])
    ru = write_plain(tmp_path / "ru.docx", [b for _, b in ROWS])
    doc = load([en, ru])
    assert (doc.lang_a, doc.lang_b, doc.mode) == ("en", "ru", "two-files")
    assert [(p.a.text, p.b.text) for p in doc.pairs] == ROWS


def test_two_files_same_script_need_langs(tmp_path):
    en = write_plain(tmp_path / "en.docx", ["The Seller delivers the goods."])
    es = write_plain(tmp_path / "es.docx", ["El Vendedor entrega los bienes."])
    with pytest.raises(LoaderError, match="--langs"):
        load([en, es])
    doc = load([en, es], ("en", "es"))
    assert (doc.lang_a, doc.lang_b) == ("en", "es")


def test_langs_given_in_the_wrong_order_follow_the_script(tmp_path):
    en = write_plain(tmp_path / "en.docx", ["The Seller delivers the goods."])
    ru = write_plain(tmp_path / "ru.docx", ["Продавец поставляет товар."])
    doc = load([en, ru], ("ru", "en"))
    assert (doc.lang_a, doc.lang_b) == ("en", "ru")


def test_empty_file_is_refused(tmp_path):
    en = write_plain(tmp_path / "en.docx", ["Some text."])
    empty = write_plain(tmp_path / "empty.docx", [])
    with pytest.raises(LoaderError, match="contains no text"):
        load([en, empty])


def test_three_paths_are_refused(tmp_path):
    with pytest.raises(LoaderError, match="one bilingual DOCX"):
        load([tmp_path / "a", tmp_path / "b", tmp_path / "c"])


def test_helpers_do_not_share_state():
    assert copy.deepcopy(ROWS) == ROWS
