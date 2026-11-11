from __future__ import annotations

from .facts.extract import extract_facts
from .models import Document


def analyse(doc: Document, strict: bool = False) -> Document:
    """Extract the facts of every complete pair. Rules read these facts; they
    never parse numbers out of raw text themselves."""
    for pair in doc.complete_pairs():
        pair.facts_a = extract_facts(pair.a.text, doc.lang_a, strict)
        pair.facts_b = extract_facts(pair.b.text, doc.lang_b, strict)
    return doc
