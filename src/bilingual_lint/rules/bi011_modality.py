from __future__ import annotations

import re

from ..models import Document, Finding, Severity
from ..wordlists import load_wordlists
from .base import severity_of

FLAGS = re.IGNORECASE | re.UNICODE


def cues(text: str, lang: str) -> dict:
    """{'obligation': bool, 'permission': bool, 'negation': bool} for a text."""
    data = load_wordlists(lang).raw.get("modality") or {}
    return {kind: any(re.search(r"(?<!\w)(?:" + p + r")(?!\w)", text, FLAGS)
                      for p in data.get(kind) or [])
            for kind in ("obligation", "permission", "negation")}


class ModalityDiffers:
    id = "BI011"
    name = "obligation-cues"
    description = "obligation, permission or negation wording differs (heuristic)"
    default_severity = Severity.INFO
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        for pair in doc.complete_pairs():
            a, b = cues(pair.a.text, doc.lang_a), cues(pair.b.text, doc.lang_b)
            if a["negation"] != b["negation"]:
                side = doc.lang_a if a["negation"] else doc.lang_b
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"negation on the {side} side only — check the meaning", pair,
                    {"a": a, "b": b}))
            for must, may in ((a, b), (b, a)):
                if (must["obligation"] and not must["permission"]
                        and may["permission"] and not may["obligation"]):
                    strong = doc.lang_a if must is a else doc.lang_b
                    weak = doc.lang_b if must is a else doc.lang_a
                    out.append(Finding(
                        self.id, severity_of(cfg),
                        f"an obligation on the {strong} side reads as a permission on "
                        f"the {weak} side — check the meaning", pair, {"a": a, "b": b}))
        return out
