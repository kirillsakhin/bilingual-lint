"""Shared test helpers: build Documents in memory and DOCX files on disk."""
from __future__ import annotations

from pathlib import Path

from docx import Document as new_docx

from bilingual_lint.analysis import analyse
from bilingual_lint.config import RULE_DEFAULTS
from bilingual_lint.models import Document, Pair, Segment


def make_doc(rows, lang_a="en", lang_b="ru", mode="two-column") -> Document:
    """rows: [(text_a, text_b)]; None on a side means no segment there."""
    pairs = []
    for i, (a, b) in enumerate(rows):
        pairs.append(Pair(
            i + 1,
            None if a is None else Segment(a, lang_a, i, f"row {i + 1}"),
            None if b is None else Segment(b, lang_b, i, f"row {i + 1}")))
    return analyse(Document(pairs, lang_a, lang_b, mode, []))


def check(rule_cls, rows, lang_a="en", lang_b="ru", **overrides) -> list:
    cfg = dict(RULE_DEFAULTS[rule_cls.id], glossary=[])
    cfg.update(overrides)
    return rule_cls().check(make_doc(rows, lang_a, lang_b), cfg)


def write_two_column(path: Path, rows, intro: str | None = None) -> Path:
    document = new_docx()
    if intro:
        document.add_paragraph(intro)
    table = document.add_table(rows=0, cols=2)
    for a, b in rows:
        cells = table.add_row().cells
        cells[0].text = a
        cells[1].text = b
    document.save(str(path))
    return path


def write_plain(path: Path, paragraphs) -> Path:
    document = new_docx()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(str(path))
    return path
