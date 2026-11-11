from __future__ import annotations

from collections import Counter

from ..models import Document, Finding, Severity
from .base import describe, severity_of


class ReferencesDiffer:
    id = "BI006"
    name = "clause-references"
    description = "a clause number or cross-reference differs"
    default_severity = Severity.WARNING
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        for pair in doc.complete_pairs():
            lead_a, lead_b = pair.facts_a.leading_number, pair.facts_b.leading_number
            if lead_a != lead_b:
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"clause number differs — {doc.lang_a}: {lead_a or 'none'} · "
                    f"{doc.lang_b}: {lead_b or 'none'}", pair, {"a": lead_a, "b": lead_b}))
            refs_a, refs_b = Counter(pair.facts_a.refs), Counter(pair.facts_b.refs)
            if refs_a != refs_b:
                only_a = sorted((refs_a - refs_b).elements())
                only_b = sorted((refs_b - refs_a).elements())
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"cross-references differ — {describe(doc, only_a, only_b)}", pair,
                    {"only_a": only_a, "only_b": only_b}))
        return out
