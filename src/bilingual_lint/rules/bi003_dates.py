from __future__ import annotations

from collections import Counter

from ..facts.dates import match_dates
from ..models import Document, Finding, Severity
from .base import describe, severity_of, soften


class DatesDiffer:
    id = "BI003"
    name = "dates"
    description = "a date or time differs, or a date agrees only under one day/month reading"
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
            times_a = Counter(t.value for t in pair.facts_a.times)
            times_b = Counter(t.value for t in pair.facts_b.times)
            if times_a != times_b:
                extra_a, extra_b = times_a - times_b, times_b - times_a
                raw_a = [t.raw for t in pair.facts_a.times if extra_a[t.value]]
                raw_b = [t.raw for t in pair.facts_b.times if extra_b[t.value]]
                out.append(Finding(
                    self.id, severity, f"times differ — {describe(doc, raw_a, raw_b)}",
                    pair, {"only_a": raw_a, "only_b": raw_b}))
            for da, db in ambiguous:
                out.append(Finding(
                    self.id, soften(severity),
                    f"ambiguous day/month order — {da.raw} against {db.raw} agree "
                    "only under one reading; write the month in words", pair,
                    {"a": da.raw, "b": db.raw}))
        return out
