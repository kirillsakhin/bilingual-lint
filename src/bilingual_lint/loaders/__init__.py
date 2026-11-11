from __future__ import annotations

from pathlib import Path

from ..models import Document
from .docx_reader import LoaderError
from .two_column import load_two_column
from .two_files import load_two_files


def load(paths: list, langs: tuple | None = None) -> Document:
    """One path: a two-column bilingual DOCX. Two paths: source and translation."""
    if len(paths) == 1:
        return load_two_column(Path(paths[0]), langs)
    if len(paths) == 2:
        return load_two_files(Path(paths[0]), Path(paths[1]), langs)
    raise LoaderError("pass one bilingual DOCX, or two DOCX files")


__all__ = ["LoaderError", "load", "load_two_column", "load_two_files"]
