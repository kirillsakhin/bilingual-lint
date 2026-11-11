from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import Severity


class ConfigError(Exception):
    pass


RULE_DEFAULTS: dict = {
    "BI000": {"enabled": True, "severity": "info"},
    "BI001": {"enabled": True, "severity": "error", "strict_separators": False},
    "BI002": {"enabled": True, "severity": "error", "missing_currency": True},
    "BI003": {"enabled": True, "severity": "error"},
    "BI004": {"enabled": True, "severity": "error"},
    "BI005": {"enabled": True, "severity": "error"},
    "BI006": {"enabled": True, "severity": "warning"},
    "BI007": {"enabled": True, "severity": "error", "min_ratio": 0.4, "max_ratio": 2.5,
              "min_chars": 80, "untranslated_min_letters": 20},
    "BI008": {"enabled": True, "severity": "warning"},
    "BI009": {"enabled": True, "severity": "error"},
    "BI010": {"enabled": True, "severity": "error"},
    "BI011": {"enabled": True, "severity": "info"},
}
LLM_DEFAULTS = {"model": "anthropic/claude-sonnet-5", "max_pairs": 50,
                "timeout_seconds": 60}
TOP_KEYS = {"langs", "fail_on", "glossary", "low_confidence", "rules", "llm"}
SEVERITY_VALUES = {s.value for s in Severity}
LANG_RE = re.compile(r"[a-z]{2,3}\Z")


def parse_langs(value) -> tuple:
    """'en,ru' or ['en', 'ru'] -> ('en', 'ru')."""
    items = value.split(",") if isinstance(value, str) else list(value or [])
    items = [str(item).strip().lower() for item in items]
    if len(items) != 2 or not all(LANG_RE.match(item) for item in items):
        raise ConfigError(f"langs must be two language codes such as en,ru; got {value!r}")
    if items[0] == items[1]:
        raise ConfigError("langs must name two different languages")
    return items[0], items[1]


def load_glossary(path: Path) -> list:
    """A YAML list of term entries: - {en: Buyer, ru: Покупатель}."""
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"glossary file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise ConfigError("glossary must be a list of mappings like {en: Buyer, ru: ...}")
    return [{str(k): str(v) for k, v in item.items()} for item in raw]


@dataclass
class Config:
    langs: tuple | None = None
    fail_on: str = "error"
    glossary: list = field(default_factory=list)
    low_confidence: float = 0.5
    rules: dict = field(default_factory=lambda: copy.deepcopy(RULE_DEFAULTS))
    llm: dict = field(default_factory=lambda: dict(LLM_DEFAULTS))

    @classmethod
    def load(cls, path: Path | str | None) -> Config:
        cfg = cls()
        if path is None:
            default = Path(".bilingual-lint.yaml")
            path = default if default.is_file() else None
        if path is None:
            return cfg
        path = Path(path)
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ConfigError("config root must be a mapping")
        unknown = set(raw) - TOP_KEYS
        if unknown:
            raise ConfigError(f"unknown config keys: {sorted(unknown)}")
        if raw.get("langs") is not None:
            cfg.langs = parse_langs(raw["langs"])
        if "fail_on" in raw:
            if raw["fail_on"] not in ("error", "warning"):
                raise ConfigError(f"fail_on must be error or warning, got {raw['fail_on']!r}")
            cfg.fail_on = raw["fail_on"]
        if raw.get("glossary"):
            cfg.glossary = load_glossary(path.parent / str(raw["glossary"]))
        if "low_confidence" in raw:
            value = raw["low_confidence"]
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                raise ConfigError("low_confidence must be a number between 0 and 1")
            cfg.low_confidence = float(value)
        for rule_id, user_rule in (raw.get("rules") or {}).items():
            if rule_id not in RULE_DEFAULTS:
                raise ConfigError(f"unknown rule id: {rule_id}")
            if not isinstance(user_rule, dict):
                raise ConfigError(f"rules.{rule_id} must be a mapping")
            bad = set(user_rule) - set(RULE_DEFAULTS[rule_id])
            if bad:
                raise ConfigError(f"unknown keys for {rule_id}: {sorted(bad)}")
            if "severity" in user_rule and user_rule["severity"] not in SEVERITY_VALUES:
                raise ConfigError(
                    f"rules.{rule_id}.severity must be one of {sorted(SEVERITY_VALUES)}")
            cfg.rules[rule_id].update(user_rule)
        llm = raw.get("llm") or {}
        bad = set(llm) - set(LLM_DEFAULTS)
        if bad:
            raise ConfigError(f"unknown llm keys: {sorted(bad)}")
        cfg.llm.update(llm)
        return cfg
