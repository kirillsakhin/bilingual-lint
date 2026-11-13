"""Comparison arm: one model reads the whole document and names the rows that
differ. It is given the same mutated copies the linter was scored on, to test
the claim that rules are the more reliable tool for this class of error."""
from __future__ import annotations

import json
import re
import time

from .mutate import OPERATORS, all_mutations

SYSTEM_PROMPT = """\
You are checking a bilingual contract or official document. Each numbered row
holds the same passage in two languages. Find every row where the two versions
do not say the same thing: a different number, amount, currency, date, period,
reference, name or identifier, a missing or extra passage, or a different
meaning. Ignore style, word order and formatting.
Respond with ONLY a JSON object:
{"rows": [{"row": <row number>, "reason": "<one sentence>"}]}
Use an empty list when every row matches."""


def render(rows: list, langs: tuple = ("en", "ru")) -> str:
    """The document as numbered rows, 1-based, an empty cell shown as (empty)."""
    return "\n\n".join(
        f"Row {number}\n{langs[0]}: {a or '(empty)'}\n{langs[1]}: {b or '(empty)'}"
        for number, (a, b) in enumerate(rows, start=1))


def parse(content: str, row_count: int) -> set:
    """0-based row indexes the model named. Raises ValueError on a reply that
    is not the requested JSON."""
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in response")
    payload = json.loads(match.group(0))
    if not isinstance(payload.get("rows"), list):
        raise ValueError("no 'rows' list in response")
    named = set()
    for item in payload["rows"]:
        number = item.get("row") if isinstance(item, dict) else item
        if isinstance(number, int) and 1 <= number <= row_count:
            named.add(number - 1)
    return named


def litellm_complete(model: str, timeout: int = 120):
    """A complete(system, user) -> str function backed by litellm."""
    import litellm

    def complete(system: str, user: str) -> str:
        response = litellm.completion(
            model=model, timeout=timeout,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return response.choices[0].message.content

    return complete


def with_retries(complete, attempts: int = 6, pause: float = 30.0, sleep=time.sleep):
    """Wrap complete(system, user) so a failed call is sent again after a pause
    that grows with each attempt. The last failure is raised."""
    def retrying(system: str, user: str) -> str:
        for attempt in range(1, attempts):
            try:
                return complete(system, user)
            except Exception:
                sleep(pause * attempt)
        return complete(system, user)

    return retrying


def review(rows: list, complete, langs: tuple = ("en", "ru")) -> set | None:
    """Rows the model says differ, or None when the call or the reply failed."""
    try:
        return parse(complete(SYSTEM_PROMPT, render(rows, langs)), len(rows))
    except Exception:
        return None


def compare_document(rows: list, seed: int, complete, parties: dict | None = None,
                     operators: tuple = OPERATORS, per_operator: int | None = 1,
                     langs: tuple = ("en", "ru")) -> dict:
    """Review the clean document, then each mutated copy.

    A defect is caught when the model names the mutated row and had not named
    it on the clean copy. A defect on a row the model already named on the
    clean copy cannot be attributed, so it is marked 'excluded'."""
    clean = review(rows, complete, langs)
    cases = []
    for mutated_rows, mutation in all_mutations(rows, seed, parties, operators, per_operator):
        named = None if clean is None else review(mutated_rows, complete, langs)
        if named is None:
            outcome = "failed"
        elif mutation.row in clean:
            outcome = "excluded"
        else:
            outcome = "caught" if mutation.row in named else "missed"
        cases.append({**mutation.as_dict(), "outcome": outcome,
                      "extra_rows": None if named is None
                      else len(named - clean - {mutation.row})})
    return {"pairs": len(rows), "clean_rows": None if clean is None else sorted(clean),
            "cases": cases}


def summarise(results: list) -> dict:
    """results: compare_document outputs."""
    by_operator: dict = {}
    pairs = clean_rows = clean_failed = extra = scored = 0
    for result in results:
        if result["clean_rows"] is None:
            clean_failed += 1
        else:
            pairs += result["pairs"]
            clean_rows += len(result["clean_rows"])
        for case in result["cases"]:
            row = by_operator.setdefault(
                case["operator"], {"caught": 0, "missed": 0, "excluded": 0, "failed": 0})
            row[case["outcome"]] += 1
            if case["outcome"] in ("caught", "missed"):
                scored += 1
                extra += case["extra_rows"]
    for row in by_operator.values():
        judged = row["caught"] + row["missed"]
        row["recall"] = round(row["caught"] / judged, 4) if judged else None
    return {
        "documents": len(results),
        "clean_documents_failed": clean_failed,
        "operators": {name: by_operator[name] for name in OPERATORS if name in by_operator},
        "clean_rows_named_per_100_pairs": round(100 * clean_rows / pairs, 2) if pairs else None,
        "extra_rows_named_per_mutated_copy": round(extra / scored, 2) if scored else None,
    }
