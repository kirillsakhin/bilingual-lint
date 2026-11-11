from __future__ import annotations

import json

from .. import __version__
from ..models import Document, Finding


def _finding_dict(finding: Finding) -> dict:
    pair = finding.pair
    a = pair.a if pair else None
    b = pair.b if pair else None
    return {
        "rule_id": finding.rule_id,
        "severity": finding.severity.value,
        "message": finding.message,
        "pair_no": pair.pair_no if pair else None,
        "confidence": pair.confidence if pair else None,
        "location_a": a.location if a else None,
        "location_b": b.location if b else None,
        "text_a": a.text if a else None,
        "text_b": b.text if b else None,
        "context": finding.context,
    }


def build_report(doc: Document, findings: list, ran: list, disabled: list,
                 skipped: list, llm_status: dict | None = None) -> dict:
    by_severity: dict = {}
    by_rule: dict = {}
    for finding in findings:
        by_severity[finding.severity.value] = by_severity.get(finding.severity.value, 0) + 1
        by_rule[finding.rule_id] = by_rule.get(finding.rule_id, 0) + 1
    return {
        "tool": "bilingual-lint",
        "version": __version__,
        "source": {
            "paths": [str(path) for path in doc.source_paths],
            "mode": doc.mode,
            "lang_a": doc.lang_a,
            "lang_b": doc.lang_b,
            "pairs": len(doc.pairs),
            "unpaired": sum(1 for pair in doc.pairs if pair.a is None or pair.b is None),
        },
        "summary": {"total": len(findings), "by_severity": by_severity,
                    "by_rule": by_rule},
        "rules": {"ran": ran, "disabled": disabled, "skipped": skipped},
        "findings": [_finding_dict(finding) for finding in findings],
        "llm_pass": llm_status or {"requested": False},
    }


def to_json(doc: Document, findings: list, ran: list, disabled: list, skipped: list,
            llm_status: dict | None = None) -> str:
    return json.dumps(build_report(doc, findings, ran, disabled, skipped, llm_status),
                      indent=2, ensure_ascii=False)
