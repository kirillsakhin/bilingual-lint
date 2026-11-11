from __future__ import annotations

from collections import Counter
from typing import Protocol, runtime_checkable

from ..facts.numbers import match_quantities
from ..models import Document, Finding, Pair, Severity
from ..wordlists import load_wordlists


@runtime_checkable
class Rule(Protocol):
    id: str
    name: str
    description: str
    default_severity: Severity
    needs_wordlists: bool  # True: runs only when both languages have a wordlist

    def check(self, doc: Document, cfg: dict) -> list[Finding]: ...


def supported(rule: Rule, doc: Document) -> bool:
    if not rule.needs_wordlists:
        return True
    return all(load_wordlists(lang).has_language_rules
               for lang in (doc.lang_a, doc.lang_b))


def severity_of(cfg: dict) -> Severity:
    return Severity(cfg["severity"])


def soften(severity: Severity) -> Severity:
    """One step down, for the less certain findings of a rule."""
    return Severity.WARNING if severity is Severity.ERROR else severity


def unmatched_quantities(pair: Pair) -> tuple[list, list, list]:
    """(matched pairs, only on side a, only on side b). A number that the other
    side spells out in words ('2' against 'two') is not counted as unmatched."""
    matched, only_a, only_b = match_quantities(
        pair.facts_a.quantities, pair.facts_b.quantities)
    only_a = [q for q in only_a if not (q.cands & pair.facts_b.word_values)]
    only_b = [q for q in only_b if not (q.cands & pair.facts_a.word_values)]
    return matched, only_a, only_b


def _cancel(quantities: list, refs: Counter) -> list:
    left = []
    for q in quantities:
        if q.kind == "number" and refs[q.raw] > 0:
            refs[q.raw] -= 1
        else:
            left.append(q)
    return left


def reconcile(pair: Pair) -> tuple[list, list, list, list]:
    """(quantities only on a, only on b, references only on a, only on b).

    'article 5' on one side and a bare '5' on the other carry the same value:
    one side merely words the reference in a way the wordlist does not know.
    Such a pair is cancelled, so neither rule reports it."""
    _, only_a, only_b = unmatched_quantities(pair)
    refs_a, refs_b = Counter(pair.facts_a.refs), Counter(pair.facts_b.refs)
    ref_only_a, ref_only_b = refs_a - refs_b, refs_b - refs_a
    only_a = _cancel(only_a, ref_only_b)
    only_b = _cancel(only_b, ref_only_a)
    return (only_a, only_b, sorted(ref_only_a.elements()),
            sorted(ref_only_b.elements()))


def describe(doc: Document, items_a: list, items_b: list) -> str:
    parts = []
    if items_a:
        parts.append(f"{doc.lang_a} only: {', '.join(items_a)}")
    if items_b:
        parts.append(f"{doc.lang_b} only: {', '.join(items_b)}")
    return " · ".join(parts)


def value_findings(doc: Document, cfg: dict, rule_id: str, kinds: tuple,
                   label: str) -> list[Finding]:
    """One finding per pair whose quantities of the given kinds do not match."""
    out = []
    for pair in doc.complete_pairs():
        only_a, only_b, _, _ = reconcile(pair)
        raw_a = [q.raw for q in only_a if q.kind in kinds]
        raw_b = [q.raw for q in only_b if q.kind in kinds]
        if raw_a or raw_b:
            out.append(Finding(
                rule_id, severity_of(cfg),
                f"{label} differ — {describe(doc, raw_a, raw_b)}", pair,
                {"only_a": raw_a, "only_b": raw_b}))
    return out
