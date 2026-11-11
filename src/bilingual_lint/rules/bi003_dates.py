from __future__ import annotations

from ..facts.dates import match_dates
from ..models import Document, Finding, Severity
from .base import describe, severity_of, soften


class DatesDiffer:
    id = "BI003"
    name = "dates"
    description = "a date differs, or agrees only under one day/month reading"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        severity = severity_of(cfg)
        for pair in doc.complete_pairs():
            ambiguous, only_a, only_b = match_dates(pair.facts_a.dates, pair.facts_b.dates)
            if only_a or only_b:
                raw_a, raw_b = [d.raw for d in only_a], [d.raw for d in only_b]
                out.append(Finding(
                    self.id, severity, f"dates differ — {describe(doc, raw_a, raw_b)}",
                    pair, {"only_a": raw_a, "only_b": raw_b}))
            for da, db in ambiguous:
                out.append(Finding(
                    self.id, soften(severity),
                    f"ambiguous day/month order — {da.raw} against {db.raw} agree "
                    "only under one reading; write the month in words", pair,
                    {"a": da.raw, "b": db.raw}))
        return out
