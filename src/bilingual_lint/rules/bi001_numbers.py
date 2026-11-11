from __future__ import annotations

from ..models import Document, Finding, Severity
from .base import value_findings


class NumbersDiffer:
    id = "BI001"
    name = "numbers"
    description = "a number or percentage appears on one side only"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        return value_findings(doc, cfg, self.id, ("number", "percent"), "numbers")
