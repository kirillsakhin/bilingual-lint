"""Run the linter over clean and mutated documents and count what it catches.

Every document goes through the real pipeline: it is written to a DOCX file
and read back by the linter's own loader, the same way a user's file is."""
from __future__ import annotations

import random
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from bilingual_lint.config import Config
from bilingual_lint.loaders import load
from bilingual_lint.rules import run_all
from bilingual_lint.segment import refine
from docx import Document as new_docx

from .mutate import OPERATORS, all_mutations

ROW = re.compile(r"(?:row|paragraph) (\d+)")
RANK = {"info": 0, "warning": 1, "error": 2}
# Spec section 9: the operator groups the published targets are stated for.
FIGURE_OPERATORS = ("digit", "date", "currency", "identifier")
PARAGRAPH_OPERATORS = ("drop",)
TARGETS = {"figures_recall": 0.98, "paragraphs_recall": 0.95,
           "error_flags_per_100_pairs": 3.0, "pairing_accuracy": 0.95}


def write_two_column(path: Path, rows: list) -> Path:
    document = new_docx()
    table = document.add_table(rows=0, cols=2)
    for a, b in rows:
        cells = table.add_row().cells
        cells[0].text, cells[1].text = a, b
    document.save(str(path))
    return path


def write_plain(path: Path, paragraphs: list) -> Path:
    document = new_docx()
    for text in paragraphs:
        document.add_paragraph(text)
    document.save(str(path))
    return path


def _row_of(finding) -> int | None:
    """0-based source row a finding points at, read from its location text."""
    pair = finding.pair
    for segment in (pair.a, pair.b) if pair else ():
        match = ROW.search(segment.location) if segment else None
        if match:
            return int(match.group(1)) - 1
    return None


def lint_rows(rows: list, workdir: Path, langs: tuple = ("en", "ru")) -> list:
    """Findings for a two-column document as (rule_id, severity, row, message)
    tuples. File notes (BI000) are left out: they are about the file, not a row."""
    path = write_two_column(workdir / "case.docx", rows)
    doc = refine(load([path], langs))
    findings, *_ = run_all(doc, Config())
    return [(f.rule_id, f.severity.value, _row_of(f), f.message) for f in findings
            if f.rule_id != "BI000"]


def pairing(rows: list, workdir: Path, missing: int | None = None, side: str = "b",
            langs: tuple = ("en", "ru")) -> tuple:
    """Two-file mode: (rows paired with their true partner, rows that have one).
    With 'missing', that row is left out of one file, as when a paragraph was
    dropped from one language version."""
    kept = [(a, b) for i, (a, b) in enumerate(rows) if i != missing]
    path_a = write_plain(workdir / "a.docx", [a for i, (a, _) in enumerate(rows)
                                             if not (side == "a" and i == missing)])
    path_b = write_plain(workdir / "b.docx", [b for i, (_, b) in enumerate(rows)
                                             if not (side == "b" and i == missing)])
    doc = load([path_a, path_b], langs)
    truth = dict(kept)
    right = sum(1 for p in doc.pairs if p.a and p.b and truth.get(p.a.text) == p.b.text)
    return right, len(kept)


def score_document(rows: list, seed: int, parties: dict | None = None,
                   operators: tuple = OPERATORS, per_operator: int | None = None,
                   langs: tuple = ("en", "ru")) -> dict:
    """Lint the clean document, then one mutated copy per planted defect.

    A defect is caught when the mutated copy has a finding on the mutated row
    that the clean copy did not have. The message is part of a finding's
    identity, so a row that was already flagged still counts once the linter
    says something new about it. 'expected' means the finding came from a rule
    built for that kind of defect; 'any' accepts any rule."""
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        clean = lint_rows(rows, workdir, langs)
        baseline = set(clean)
        cases = []
        for mutated_rows, mutation in all_mutations(rows, seed, parties, operators,
                                                    per_operator):
            new = [f for f in lint_rows(mutated_rows, workdir, langs)
                   if f not in baseline and f[2] == mutation.row]
            expected = [f for f in new if f[0] in mutation.expected]
            cases.append({
                **mutation.as_dict(),
                "caught_expected": bool(expected),
                "caught_any": bool(new),
                "top_severity": max((f[1] for f in new), key=RANK.get, default=None),
                "rules": sorted({f[0] for f in new}),
            })
        right, total = pairing(rows, workdir, langs=langs)
        gap_right = gap_total = 0
        if len(rows) > 2:
            for side in ("a", "b"):
                missing = random.Random(f"{seed}:gap:{side}").randrange(1, len(rows) - 1)
                r, t = pairing(rows, workdir, missing, side, langs)
                gap_right, gap_total = gap_right + r, gap_total + t
    return {"pairs": len(rows), "clean_findings": clean, "cases": cases,
            "pairing": {"right": right, "total": total},
            "pairing_one_missing": {"right": gap_right, "total": gap_total}}


def _ratio(part: int, whole: int) -> float | None:
    return round(part / whole, 4) if whole else None


def summarise(results: list) -> dict:
    """results: score_document outputs. Returns the numbers the README prints."""
    by_operator: dict = defaultdict(lambda: {"planted": 0, "expected": 0, "any": 0})
    pairs = right = total = gap_right = gap_total = 0
    clean: dict = defaultdict(int)
    for result in results:
        pairs += result["pairs"]
        right += result["pairing"]["right"]
        total += result["pairing"]["total"]
        gap_right += result["pairing_one_missing"]["right"]
        gap_total += result["pairing_one_missing"]["total"]
        for _, severity, *_ in result["clean_findings"]:
            clean[severity] += 1
        for case in result["cases"]:
            row = by_operator[case["operator"]]
            row["planted"] += 1
            row["expected"] += case["caught_expected"]
            row["any"] += case["caught_any"]
    for row in by_operator.values():
        row["recall_expected"] = _ratio(row["expected"], row["planted"])
        row["recall_any"] = _ratio(row["any"], row["planted"])

    def group(names: tuple) -> dict:
        planted = sum(by_operator[n]["planted"] for n in names if n in by_operator)
        caught = sum(by_operator[n]["any"] for n in names if n in by_operator)
        return {"planted": planted, "caught": caught, "recall": _ratio(caught, planted)}

    return {
        "documents": len(results),
        "pairs": pairs,
        "operators": {name: by_operator[name] for name in OPERATORS if name in by_operator},
        "figures": group(FIGURE_OPERATORS),
        "paragraphs": group(PARAGRAPH_OPERATORS),
        "clean_flags_per_100_pairs": {
            severity: round(100 * clean[severity] / pairs, 2) if pairs else None
            for severity in ("error", "warning", "info")},
        "pairing_accuracy": _ratio(right, total),
        "pairing_accuracy_one_missing": _ratio(gap_right, gap_total),
    }


def targets(summary: dict, false_error_flags_per_100: float | None = None) -> list:
    """The four published targets as (name, value, target, met). 'met' is None
    when there was nothing to measure. The false-flag target is judged on the
    adjudicated rate when one is given, otherwise on the raw rate."""
    flags = (false_error_flags_per_100 if false_error_flags_per_100 is not None
             else summary["clean_flags_per_100_pairs"]["error"])
    pairing_values = [v for v in (summary["pairing_accuracy"],
                                  summary["pairing_accuracy_one_missing"]) if v is not None]
    values = {
        "figures_recall": summary["figures"]["recall"],
        "paragraphs_recall": summary["paragraphs"]["recall"],
        "error_flags_per_100_pairs": flags,
        "pairing_accuracy": min(pairing_values) if pairing_values else None,
    }
    out = []
    for name, target in TARGETS.items():
        value = values[name]
        if value is None:
            met = None
        elif name == "error_flags_per_100_pairs":
            met = value <= target
        else:
            met = value >= target
        out.append((name, value, target, met))
    return out
