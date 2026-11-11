from __future__ import annotations

from ..models import Document, Finding, Severity
from .base import severity_of, soften, unmatched_quantities, value_findings


class AmountsDiffer:
    id = "BI002"
    name = "amounts"
    description = "a money amount or its currency differs"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = value_findings(doc, cfg, self.id, ("money",), "amounts")
        severity = severity_of(cfg)
        for pair in doc.complete_pairs():
            matched, _, _ = unmatched_quantities(pair)
            for qa, qb in matched:
                if qa.kind == "money" and qb.kind == "money":
                    if qa.unit != qb.unit:
                        out.append(Finding(
                            self.id, severity,
                            f"currency differs — {doc.lang_a}: {qa.raw} {qa.unit} · "
                            f"{doc.lang_b}: {qb.raw} {qb.unit}", pair,
                            {"a": qa.unit, "b": qb.unit}))
                elif cfg["missing_currency"] and "money" in (qa.kind, qb.kind):
                    money, lang = (qa, doc.lang_a) if qa.kind == "money" else (qb, doc.lang_b)
                    out.append(Finding(
                        self.id, soften(severity),
                        f"currency stated on the {lang} side only — {money.raw} {money.unit}",
                        pair, {"currency": money.unit}))
        return out
