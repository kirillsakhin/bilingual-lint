"""Hand verdicts on what the linter reports in unmodified text.

A finding on a clean pair is either a false flag or a real difference between
the two published versions. Only a person reading both can tell, so each
error-level finding gets a verdict in benchmark/adjudication/<part>.json:

    {"<key>": {"verdict": "real" | "false", "note": "<why>"}}

A finding with no verdict counts as a false flag."""
from __future__ import annotations

import json
from pathlib import Path

VERDICTS = ("real", "false")


def key(document: int, finding: list) -> str:
    rule, _, row, message = finding
    return f"{document}|{row}|{rule}|{message}"


def error_findings(results: list) -> list:
    """(key, document, row, rule, message) for every error on clean text."""
    return [(key(n, f), n, f[2], f[0], f[3])
            for n, result in enumerate(results)
            for f in result["clean_findings"] if f[1] == "error"]


def load(path: Path) -> dict:
    if not path.is_file():
        return {}
    verdicts = json.loads(path.read_text(encoding="utf-8"))
    bad = [k for k, v in verdicts.items() if v.get("verdict") not in VERDICTS]
    if bad:
        raise ValueError(f"verdict must be one of {VERDICTS}: {bad[:3]}")
    return verdicts


def tally(results: list, verdicts: dict) -> dict:
    found = error_findings(results)
    counts = {"real": 0, "false": 0, "open": 0}
    for finding_key, *_ in found:
        counts[verdicts.get(finding_key, {}).get("verdict", "open")] += 1
    pairs = sum(result["pairs"] for result in results)
    not_real = counts["false"] + counts["open"]
    return {"error_findings": len(found), **counts,
            "false_per_100_pairs": round(100 * not_real / pairs, 2) if pairs else None}


def worksheet(results: list, documents: list, verdicts: dict) -> str:
    """Markdown list of the findings still without a verdict, with both texts."""
    lines = ["# Findings on clean text awaiting a verdict", ""]
    for finding_key, document, row, rule, message in error_findings(results):
        if finding_key in verdicts:
            continue
        a, b = documents[document][row] if row is not None else ("", "")
        lines += [f"## `{finding_key}`", "", f"- {rule}: {message}", f"- A: {a}",
                  f"- B: {b}", ""]
    return "\n".join(lines)
