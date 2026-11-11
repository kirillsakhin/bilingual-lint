"""Read a DOCX into ordered blocks of text, as if tracked changes were accepted."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from docx import Document as open_docx
from docx.oxml.ns import qn
from docx.table import Table

from ..text_utils import clean

OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"
# Deleted and moved-away text is not part of the accepted document.
SKIPPED = {qn("w:del"), qn("w:moveFrom"), MC_FALLBACK}
TRACKED = [qn("w:ins"), qn("w:del"), qn("w:moveFrom"), qn("w:moveTo")]
COMMENTED = [qn("w:commentRangeStart"), qn("w:commentReference")]
TEXT, TAB, HYPHEN = qn("w:t"), qn("w:tab"), qn("w:noBreakHyphen")
BREAKS = {qn("w:br"), qn("w:cr")}
PARAGRAPH = qn("w:p")


class LoaderError(Exception):
    pass


@dataclass
class Block:
    kind: str  # "paragraph" | "table"
    location: str
    text: str = ""
    rows: list = field(default_factory=list)  # table: one {grid column: text} per row


def element_text(element) -> str:
    out: list = []

    def walk(node) -> None:
        for child in node:
            tag = child.tag
            if tag in SKIPPED:
                continue
            if tag == TEXT:
                out.append(child.text or "")
            elif tag == TAB:
                out.append("\t")
            elif tag in BREAKS:
                out.append("\n")
            elif tag == HYPHEN:
                out.append("-")
            else:
                walk(child)

    walk(element)
    return "".join(out)


def _cell_text(tc) -> str:
    parts = [clean(element_text(p)) for p in tc.iter(PARAGRAPH)]
    return "\n".join(part for part in parts if part)


def _table_rows(table: Table) -> list:
    rows = []
    for tr in table._tbl.tr_lst:
        row: dict = {}
        column = 0
        for tc in tr.tc_lst:
            row[column] = _cell_text(tc)
            column += tc.grid_span
        rows.append(row)
    return rows


def read_docx(path: Path) -> tuple[list, list]:
    """Return (blocks in document order, notes about the file)."""
    path = Path(path)
    if not path.is_file():
        raise LoaderError(f"file not found: {path}")
    head = path.read_bytes()[:8]
    if head == OLE_MAGIC:
        raise LoaderError(
            f"{path.name} is password-protected or an old .doc file; "
            "save it as an unprotected .docx first")
    if not head.startswith(b"PK"):
        raise LoaderError(f"{path.name} is not a DOCX file")
    try:
        document = open_docx(str(path))
    except Exception as exc:  # python-docx raises several unrelated types
        raise LoaderError(f"cannot read {path.name}: {exc}") from exc

    body = document.element.body
    notes = []
    if next(body.iter(*TRACKED), None) is not None:
        notes.append(f"{path.name} has tracked changes; "
                     "the text was read as if all changes were accepted")
    if next(body.iter(*COMMENTED), None) is not None:
        notes.append(f"{path.name} has comments; comments were not checked")

    blocks = []
    paragraphs = tables = 0
    for item in document.iter_inner_content():
        if isinstance(item, Table):
            tables += 1
            blocks.append(Block("table", f"table {tables}", rows=_table_rows(item)))
            continue
        text = clean(element_text(item._p))
        if text:
            paragraphs += 1
            blocks.append(Block("paragraph", f"paragraph {paragraphs}", text=text))
    return blocks, notes
