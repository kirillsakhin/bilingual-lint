from __future__ import annotations

from statistics import median

from ..models import Document, Finding, Severity
from ..text_utils import letters, script_for_lang, script_of
from .base import severity_of, soften


class SegmentsDiffer:
    id = "BI007"
    name = "missing-text"
    description = "a segment is missing, empty, untranslated or far off in length"
    default_severity = Severity.ERROR
    needs_wordlists = False

    def check(self, doc: Document, cfg: dict) -> list[Finding]:
        out = []
        severity = severity_of(cfg)
        complete = doc.complete_pairs()
        ratios = [len(p.b.text) / len(p.a.text) for p in complete if len(p.a.text) >= 20]
        typical = median(ratios) if ratios else 1.0
        scripts = (script_for_lang(doc.lang_a), script_for_lang(doc.lang_b))
        for pair in doc.pairs:
            if pair.a is None or pair.b is None:
                missing = doc.lang_a if pair.a is None else doc.lang_b
                out.append(Finding(self.id, severity,
                                   f"segment has no counterpart on the {missing} side",
                                   pair, {"missing": missing}))
                continue
            if not pair.complete:
                empty = doc.lang_a if not pair.a.text.strip() else doc.lang_b
                out.append(Finding(self.id, severity, f"empty on the {empty} side",
                                   pair, {"missing": empty}))
                continue
            text_a, text_b = pair.a.text, pair.b.text
            enough = min(letters(text_a), letters(text_b)) >= cfg["untranslated_min_letters"]
            if enough and scripts[0] != scripts[1]:
                for lang, text, want in ((doc.lang_a, text_a, scripts[0]),
                                         (doc.lang_b, text_b, scripts[1])):
                    if script_of(text) != want:
                        out.append(Finding(
                            self.id, soften(severity),
                            f"text on the {lang} side does not look like {lang} — "
                            "possibly left untranslated", pair, {"lang": lang}))
            elif enough and text_a.strip() == text_b.strip():
                out.append(Finding(self.id, soften(severity),
                                   "both sides are identical — possibly left untranslated",
                                   pair, {}))
            if max(len(text_a), len(text_b)) >= cfg["min_chars"]:
                relative = (len(text_b) / len(text_a)) / typical
                if not cfg["min_ratio"] <= relative <= cfg["max_ratio"]:
                    out.append(Finding(
                        self.id, soften(severity),
                        f"length is far off — {len(text_a)} characters against "
                        f"{len(text_b)}; text may be missing", pair,
                        {"relative_ratio": round(relative, 2)}))
        return out
