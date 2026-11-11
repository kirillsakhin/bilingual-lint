from __future__ import annotations

from collections import Counter

from ..models import Document, Finding, Severity
from .base import describe, severity_of


class IdentifiersDiffer:
    id = "BI009"
    name = "identifiers"
    description = "a registration number, IBAN, e-mail or URL differs"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        for pair in doc.complete_pairs():
            ids_a = Counter(pair.facts_a.identifiers)
            ids_b = Counter(pair.facts_b.identifiers)
            if ids_a == ids_b:
                continue
            only_a = sorted((ids_a - ids_b).elements())
            only_b = sorted((ids_b - ids_a).elements())
            out.append(Finding(
                self.id, severity_of(cfg),
                f"identifiers differ — {describe(doc, only_a, only_b)}", pair,
                {"only_a": only_a, "only_b": only_b}))
        return out
