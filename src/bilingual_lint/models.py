from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .facts.extract import Facts


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"error": 2, "warning": 1, "info": 0}[self.value]


@dataclass
class Segment:
    """One unit of text on one side. location is human-readable, e.g.
    'table 1, row 4' or 'paragraph 17'."""

    text: str
    lang: str
    index: int
    location: str


@dataclass
class Pair:
    pair_no: int
    a: Segment | None
    b: Segment | None
    confidence: float = 1.0
    facts_a: Facts | None = None
    facts_b: Facts | None = None

    @property
    def complete(self) -> bool:
        return bool(self.a and self.b and self.a.text.strip() and self.b.text.strip())


@dataclass
class Finding:
    rule_id: str
    severity: Severity
    message: str
    pair: Pair | None = None
    context: dict = field(default_factory=dict)


@dataclass
class Document:
    pairs: list[Pair]
    lang_a: str
    lang_b: str
    mode: Literal["two-column", "two-files"]
    source_paths: list[Path]
    notes: list[Finding] = field(default_factory=list)  # BI000, set by loaders

    def complete_pairs(self) -> list[Pair]:
        return [p for p in self.pairs if p.complete]

    def side(self, lang: str) -> str | None:
        """'a' or 'b' for the side written in lang, else None."""
        if self.lang_a == lang:
            return "a"
        if self.lang_b == lang:
            return "b"
        return None
