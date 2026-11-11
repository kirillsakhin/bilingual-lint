from __future__ import annotations

from ..analysis import analyse
from ..config import Config
from ..models import Document, Finding, Severity
from .base import Rule, supported
from .bi001_numbers import NumbersDiffer
from .bi002_money import AmountsDiffer
from .bi003_dates import DatesDiffer
from .bi004_words import DigitsAndWordsDisagree
from .bi005_durations import DurationsDiffer
from .bi006_refs import ReferencesDiffer
from .bi007_structure import SegmentsDiffer
from .bi008_terms import TermsDiffer
from .bi009_identifiers import IdentifiersDiffer
from .bi010_prevailing import PrevailingLanguage
from .bi011_modality import ModalityDiffers

ALL_RULES: list[Rule] = [
    NumbersDiffer(),
    AmountsDiffer(),
    DatesDiffer(),
    DigitsAndWordsDisagree(),
    DurationsDiffer(),
    ReferencesDiffer(),
    SegmentsDiffer(),
    TermsDiffer(),
    IdentifiersDiffer(),
    PrevailingLanguage(),
    ModalityDiffers(),
]


def sort_key(finding: Finding) -> tuple:
    return (-finding.severity.rank, finding.pair.pair_no if finding.pair else 0,
            finding.rule_id)


def run_all(doc: Document, config: Config,
            only: set | None = None) -> tuple[list, list, list, list]:
    """Returns (findings, ran, disabled, skipped). 'skipped' lists rules that
    need wordlists this language pair does not have."""
    analyse(doc, strict=config.rules["BI001"]["strict_separators"])
    findings: list = []
    ran: list = []
    disabled: list = []
    skipped: list = []

    def wanted(rule_id: str) -> bool:
        return config.rules[rule_id]["enabled"] and (only is None or rule_id in only)

    if wanted("BI000"):
        ran.append("BI000")
        findings.extend(doc.notes)
    else:
        disabled.append("BI000")
    for rule in ALL_RULES:
        if not wanted(rule.id):
            disabled.append(rule.id)
        elif not supported(rule, doc):
            skipped.append(rule.id)
        else:
            ran.append(rule.id)
            cfg = dict(config.rules[rule.id], glossary=config.glossary)
            findings.extend(rule.check(doc, cfg))
    for finding in findings:
        pair = finding.pair
        if pair is not None and pair.complete and pair.confidence < config.low_confidence:
            finding.context["pairing"] = "low confidence — check the pairing first"
            if finding.severity is Severity.ERROR:
                finding.severity = Severity.WARNING
    findings.sort(key=sort_key)
    return findings, ran, disabled, skipped
