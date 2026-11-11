from __future__ import annotations

import re

from ..models import Document, Finding, Severity
from ..wordlists import load_wordlists
from .base import severity_of

FLAGS = re.IGNORECASE | re.UNICODE
INFLECTED = {"ru"}  # languages where a term changes its ending


def definitions(text: str, lang: str) -> list:
    """Defined terms introduced in this text, in order of appearance."""
    patterns = load_wordlists(lang).raw.get("definitions") or {}
    found = []
    for key in ("inline", "leading"):
        if key in patterns:
            found.extend((m.start(), m.group(1).strip())
                         for m in re.finditer(patterns[key], text, FLAGS))
    return [term for _, term in sorted(found)]


def _word_pattern(word: str, lang: str) -> str:
    """One word of a term: any ending in an inflected language, singular or
    plural elsewhere. A term defined with a capital letter keeps it, so
    "Representative" does not match the common noun "representative"; the
    rest of the word is matched in any case, so "REPRESENTATIVE" still does."""
    low = word.lower()
    if lang in INFLECTED and len(word) >= 5:
        stem, tail = word[:-2], r"\w*"
    elif lang not in INFLECTED and len(word) > 4 and low.endswith("ies"):
        stem, tail = word[:-3], r"(?:y|ies)(?:'s|’s)?"
    else:
        plural = (lang not in INFLECTED and len(word) > 3 and low.endswith("s")
                  and not low.endswith("ss"))
        stem, tail = (word[:-1] if plural else word), r"(?:s|es)?(?:'s|’s)?"
    if stem[:1].isupper():
        return re.escape(stem[0]) + "(?i:" + re.escape(stem[1:]) + tail + ")"
    return "(?i:" + re.escape(stem) + tail + ")"


def term_pattern(term: str, lang: str) -> re.Pattern:
    pieces = [_word_pattern(word, lang) for word in term.split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(pieces) + r"(?!\w)", re.UNICODE)


def learn_terms(doc: Document) -> list:
    """Term pairs taken from the document's own definitions."""
    learned = []
    for pair in doc.complete_pairs():
        terms_a = definitions(pair.a.text, doc.lang_a)
        terms_b = definitions(pair.b.text, doc.lang_b)
        if terms_a and len(terms_a) == len(terms_b):
            learned.extend(zip(terms_a, terms_b, strict=True))
    return learned


class TermsDiffer:
    id = "BI008"
    name = "terms"
    description = "a defined term or glossary term is rendered inconsistently"
    default_severity = Severity.WARNING
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        terms = learn_terms(doc)
        for entry in cfg.get("glossary") or []:
            if doc.lang_a in entry and doc.lang_b in entry:
                terms.append((entry[doc.lang_a], entry[doc.lang_b]))
        out = []
        for term_a, term_b in dict.fromkeys(terms):
            pattern_a = term_pattern(term_a, doc.lang_a)
            pattern_b = term_pattern(term_b, doc.lang_b)
            for pair in doc.complete_pairs():
                in_a = bool(pattern_a.search(pair.a.text))
                in_b = bool(pattern_b.search(pair.b.text))
                if in_a == in_b:
                    continue
                present, absent = (term_a, term_b) if in_a else (term_b, term_a)
                side = doc.lang_b if in_a else doc.lang_a
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"term \"{present}\" is used, but \"{absent}\" is not on the {side} side",
                    pair, {"term_a": term_a, "term_b": term_b}))
        return out
