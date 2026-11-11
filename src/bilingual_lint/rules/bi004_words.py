from __future__ import annotations

from ..models import Document, Finding, Severity
from .base import severity_of


class DigitsAndWordsDisagree:
    id = "BI004"
    name = "digits-vs-words"
    description = "digits and the number in words disagree on the same side"
    default_severity = Severity.ERROR
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        for pair in doc.complete_pairs():
            for lang, facts in ((doc.lang_a, pair.facts_a), (doc.lang_b, pair.facts_b)):
                for digits, words in facts.word_digit_mismatches:
                    out.append(Finding(
                        self.id, severity_of(cfg),
                        f"digits and words disagree on the {lang} side — "
                        f"{digits} against \"{words}\"", pair,
                        {"lang": lang, "digits": digits, "words": words}))
        return out
