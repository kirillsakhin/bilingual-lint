from __future__ import annotations

from ..models import Document, Finding, Severity
from .base import severity_of, unmatched_quantities, value_findings


def _day_type(quantity) -> str:
    # A bare "30 days" means calendar days.
    return quantity.day_type or "calendar"


class DurationsDiffer:
    id = "BI005"
    name = "durations"
    description = "a time period differs in length, unit or day type"
    default_severity = Severity.ERROR
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = value_findings(doc, cfg, self.id, ("duration",), "durations")
        for pair in doc.complete_pairs():
            matched, _, _ = unmatched_quantities(pair)
            for qa, qb in matched:
                if qa.kind != "duration" or qb.kind != "duration":
                    continue
                if qa.unit != qb.unit:
                    what = f"unit differs — {qa.unit} against {qb.unit}"
                elif qa.unit == "day" and _day_type(qa) != _day_type(qb):
                    what = f"day type differs — {_day_type(qa)} against {_day_type(qb)} days"
                else:
                    continue
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"duration {what} ({doc.lang_a}: {qa.raw}, {doc.lang_b}: {qb.raw})",
                    pair, {"a": [qa.unit, _day_type(qa)], "b": [qb.unit, _day_type(qb)]}))
        return out
