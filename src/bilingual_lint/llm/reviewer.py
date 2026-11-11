"""Optional model pass. It only sees pairs the rules could not settle, and its
answers are marked as suggestions."""
from __future__ import annotations

import json
import re

from ..models import Document, Finding, Severity

SYSTEM_PROMPT = """\
You compare two versions of the same contract clause written in two languages.
Decide whether they say the same thing in legal effect: the same obligations,
permissions, prohibitions, conditions, parties and scope. Ignore style and
word order. Do not guess: if you cannot tell, say so.
Respond with ONLY a JSON object:
{"label": "same" | "differs" | "unclear", "reason": "<one sentence>"}"""
LABELS = {"same", "differs", "unclear"}
UNSETTLED_RULES = {"BI011"}


class LlmUnavailable(Exception):
    pass


def _parse_payload(content: str) -> dict:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in response")
    payload = json.loads(match.group(0))
    if payload.get("label") not in LABELS:
        raise ValueError(f"unknown label {payload.get('label')!r}")
    return payload


def unsettled_pairs(findings: list) -> list:
    """Pairs the rules flagged but could not settle, in document order."""
    pairs: dict = {}
    for finding in findings:
        pair = finding.pair
        if pair is None or not pair.complete:
            continue
        if finding.rule_id in UNSETTLED_RULES or finding.context.get("pairing"):
            pairs.setdefault(pair.pair_no, pair)
    return [pairs[number] for number in sorted(pairs)]


def run_llm_pass(doc: Document, findings: list, llm_cfg: dict, model: str,
                 gate: bool = False) -> dict:
    """Review unsettled pairs. Appends 'LLM' findings in place and returns the
    status dict for the report. With gate=True a 'differs' answer is an error."""
    try:
        import litellm
    except ImportError as exc:
        raise LlmUnavailable(
            'the model pass requires the extra: pip install "bilingual-lint[llm]"') from exc

    pairs = unsettled_pairs(findings)
    capped = len(pairs) > llm_cfg["max_pairs"]
    pairs = pairs[: llm_cfg["max_pairs"]]
    completed = failed = 0
    for pair in pairs:
        try:
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",
                     "content": f"Version in {doc.lang_a}:\n{pair.a.text}\n\n"
                                f"Version in {doc.lang_b}:\n{pair.b.text}"},
                ],
                timeout=llm_cfg["timeout_seconds"],
            )
            payload = _parse_payload(response.choices[0].message.content)
        except Exception:
            failed += 1
            continue
        completed += 1
        label = payload["label"]
        reason = str(payload.get("reason", "")).strip()
        for finding in findings:
            if finding.pair is pair:
                finding.context["llm"] = {"label": label, "reason": reason}
        if label != "same":
            severity = Severity.ERROR if gate and label == "differs" else Severity.INFO
            findings.append(Finding(
                "LLM", severity,
                f"model suggestion: meaning {label} — {reason}", pair,
                {"model": model, "label": label}))
    return {"requested": True, "model": model, "completed": completed,
            "failed": failed, "capped": capped}
