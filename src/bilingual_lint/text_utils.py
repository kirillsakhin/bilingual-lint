from __future__ import annotations

import re

CYRILLIC_LANGS = {"ru", "uk", "be", "bg", "sr", "mk", "kk", "ky", "tg", "mn"}
DEFAULT_LANG = {"latin": "en", "cyrillic": "ru"}
_SPACES = re.compile(r"[ \t\r\f\v]+")


def letters(text: str) -> int:
    return sum(1 for ch in text if ch.isalpha())


def script_of(text: str) -> str:
    """'latin', 'cyrillic', 'other' (letters of another script) or 'none'."""
    latin = cyrillic = other = 0
    for ch in text:
        if not ch.isalpha():
            continue
        if "Ѐ" <= ch <= "ԯ":
            cyrillic += 1
        elif ch.isascii() or "À" <= ch <= "ɏ":
            latin += 1
        else:
            other += 1
    if not (latin or cyrillic or other):
        return "none"
    return max((("latin", latin), ("cyrillic", cyrillic), ("other", other)),
               key=lambda item: item[1])[0]


def script_for_lang(lang: str) -> str:
    return "cyrillic" if lang in CYRILLIC_LANGS else "latin"


def clean(text: str) -> str:
    """Collapse runs of spaces and tabs; keep line breaks and no-break spaces."""
    lines = [_SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)
