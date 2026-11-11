from __future__ import annotations

import re

from ..models import Document, Finding, Severity
from ..wordlists import load_wordlists
from .base import severity_of

FLAGS = re.IGNORECASE | re.UNICODE
WORDS = {"equal": "both languages equally", "unclear": "unclear"}


def _spans(patterns: list, text: str) -> list:
    return [m.start() for p in patterns
            for m in re.finditer(r"(?<!\w)(?:" + p + r")(?!\w)", text, FLAGS)]


def prevailing(text: str, lang: str) -> str | None:
    """Which language this text says prevails: a language code, 'equal',
    'unclear', or None when it is not a prevailing-language clause."""
    data = load_wordlists(lang).raw.get("prevailing") or {}
    mentions = {code: _spans(patterns, text)
                for code, patterns in (data.get("languages") or {}).items()}
    mentions = {code: spans for code, spans in mentions.items() if spans}
    if not mentions:
        return None
    if _spans(data.get("equal") or [], text):
        return "equal"
    cues = _spans(data.get("cues") or [], text)
    if not cues:
        return None
    # The prevailing language is normally named once more than the other
    # ("between the English and Russian texts, the English text prevails").
    most = max(len(spans) for spans in mentions.values())
    leaders = [code for code, spans in mentions.items() if len(spans) == most]
    if len(leaders) == 1:
        return leaders[0]
    cue = cues[0]
    before = {code: max((s for s in mentions[code] if s < cue), default=None)
              for code in leaders}
    before = {code: pos for code, pos in before.items() if pos is not None}
    if before:
        return max(before, key=before.get)
    after = {code: min(mentions[code]) for code in leaders}
    nearest = min(after.values())
    winners = [code for code, pos in after.items() if pos == nearest]
    return winners[0] if len(winners) == 1 else "unclear"


class PrevailingLanguage:
    id = "BI010"
    name = "prevailing-language"
    description = "the prevailing-language clause is one-sided or contradicts itself"
    default_severity = Severity.ERROR
    needs_wordlists = True

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        seen = False
        for pair in doc.complete_pairs():
            says_a = prevailing(pair.a.text, doc.lang_a)
            says_b = prevailing(pair.b.text, doc.lang_b)
            if says_a is None and says_b is None:
                continue
            seen = True
            context = {"a": says_a, "b": says_b}
            if says_a is None or says_b is None:
                side = doc.lang_a if says_b is None else doc.lang_b
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"prevailing-language clause found on the {side} side only", pair,
                    context))
            elif "unclear" in (says_a, says_b):
                out.append(Finding(
                    self.id, Severity.INFO,
                    "prevailing-language clause found, but the tool could not tell "
                    "which language it names — check by hand", pair, context))
            elif says_a != says_b:
                out.append(Finding(
                    self.id, severity_of(cfg),
                    f"the two sides disagree on which language prevails — "
                    f"{doc.lang_a} side: {WORDS.get(says_a, says_a)} · "
                    f"{doc.lang_b} side: {WORDS.get(says_b, says_b)}", pair, context))
        if not seen:
            out.append(Finding(self.id, Severity.INFO,
                               "no prevailing-language clause found"))
        return out
