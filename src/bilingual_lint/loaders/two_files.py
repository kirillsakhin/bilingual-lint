"""Load a source file and its translation as two separate DOCX files."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from ..models import Document, Finding, Segment, Severity
from ..pairing import pair_segments
from ..text_utils import DEFAULT_LANG, letters, script_for_lang, script_of
from .docx_reader import LoaderError, read_docx


def _texts(blocks: list) -> list:
    """[(text, location)] for every paragraph and every non-empty table cell."""
    out = []
    for block in blocks:
        if block.kind == "paragraph":
            out.append((block.text, block.location))
            continue
        for number, row in enumerate(block.rows, start=1):
            for position, column in enumerate(sorted(row), start=1):
                if row[column].strip():
                    out.append((row[column],
                                f"{block.location}, row {number}, cell {position}"))
    return out


def _main_script(texts: list) -> str:
    weight: Counter = Counter()
    for text, _ in texts:
        weight[script_of(text)] += letters(text)
    weight.pop("none", None)
    return weight.most_common(1)[0][0] if weight else "none"


def load_two_files(path_a: Path, path_b: Path, langs: tuple | None = None) -> Document:
    blocks_a, notes_a = read_docx(path_a)
    blocks_b, notes_b = read_docx(path_b)
    texts_a, texts_b = _texts(blocks_a), _texts(blocks_b)
    for path, texts in ((path_a, texts_a), (path_b, texts_b)):
        if not texts:
            raise LoaderError(f"{Path(path).name} contains no text")
    script_a, script_b = _main_script(texts_a), _main_script(texts_b)
    if langs is None:
        if {script_a, script_b} != {"latin", "cyrillic"}:
            raise LoaderError(
                "cannot tell the two languages apart by script; pass --langs, "
                "for example --langs en,es (first file, second file)")
        lang_a, lang_b = DEFAULT_LANG[script_a], DEFAULT_LANG[script_b]
    else:
        lang_a, lang_b = langs
        swapped = (script_for_lang(lang_a) != script_for_lang(lang_b)
                   and script_a == script_for_lang(lang_b))
        if swapped:
            lang_a, lang_b = lang_b, lang_a
    segments_a = [Segment(text, lang_a, i, where) for i, (text, where) in enumerate(texts_a)]
    segments_b = [Segment(text, lang_b, i, where) for i, (text, where) in enumerate(texts_b)]
    findings = [Finding("BI000", Severity.INFO, note) for note in notes_a + notes_b]
    return Document(pair_segments(segments_a, segments_b), lang_a, lang_b, "two-files",
                    [Path(path_a), Path(path_b)], findings)
