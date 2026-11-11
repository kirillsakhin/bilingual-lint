"""Shared test helpers: build DOCX files on disk."""
from __future__ import annotations

from pathlib import Path

from docx import Document as new_docx


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
