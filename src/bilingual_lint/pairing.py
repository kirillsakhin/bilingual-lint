"""Pair the paragraphs of two separate files, deterministically.

Pass 1 pins the texts together at anchors: paragraphs whose clause number or
set of digits is unique on both sides. Pass 2 aligns what lies between two
anchors by length, allowing a paragraph to be missing or split in two."""
from __future__ import annotations

import math
import re
from collections import Counter

from .models import Pair, Segment

LEADING_RE = re.compile(r"^\s*((?:\d{1,3}\.)+\d{0,3}|\d{1,3}[.)])(?=\s)")
SKIP_COST = 1.0    # a paragraph with no partner
MERGE_COST = 0.5   # two paragraphs facing one
DIGIT_COST = 0.4   # the two sides do not carry the same digits
MIN_ANCHOR_CHARS = 50
MOVES = ((1, 1), (1, 0), (0, 1), (2, 1), (1, 2))


def _leading(text: str) -> str | None:
    m = LEADING_RE.match(text)
    return m.group(1).rstrip(".)") if m else None


def _signature(text: str) -> tuple | None:
    digits = re.findall(r"\d+", text)
    return tuple(digits) if len("".join(digits)) >= 4 else None


def _unique_matches(keys_a: list, keys_b: list) -> dict:
    count_a = Counter(k for k in keys_a if k)
    count_b = Counter(k for k in keys_b if k)
    position_b = {k: j for j, k in enumerate(keys_b) if k and count_b[k] == 1}
    return {i: position_b[k] for i, k in enumerate(keys_a)
            if k and count_a[k] == 1 and k in position_b}


def find_anchors(a: list, b: list) -> list:
    """Return [(i, j)] strictly increasing in both i and j."""
    texts_a = [s.text for s in a]
    texts_b = [s.text for s in b]
    by_signature = _unique_matches([_signature(t) for t in texts_a],
                                   [_signature(t) for t in texts_b])
    by_leading = _unique_matches([_leading(t) for t in texts_a],
                                 [_leading(t) for t in texts_b])
    merged = {**by_signature, **by_leading}  # a clause number wins a conflict
    used = Counter(merged.values())
    candidates = sorted((i, j) for i, j in merged.items() if used[j] == 1)
    # longest chain that also increases in j
    best = [1] * len(candidates)
    previous = [-1] * len(candidates)
    for x in range(len(candidates)):
        for y in range(x):
            if candidates[y][1] < candidates[x][1] and best[y] + 1 > best[x]:
                best[x], previous[x] = best[y] + 1, y
    if not candidates:
        return []
    x = max(range(len(candidates)), key=best.__getitem__)
    chain = []
    while x != -1:
        chain.append(candidates[x])
        x = previous[x]
    return chain[::-1]


def _digits(segments: list) -> Counter:
    return Counter(d for s in segments for d in re.findall(r"\d+", s.text))


def _length_cost(len_a: int, len_b: int, ratio: float) -> float:
    return abs(math.log((len_b + 5) / (len_a * ratio + 5)))


def _join(segments: list) -> Segment:
    if len(segments) == 1:
        return segments[0]
    return Segment(" ".join(s.text for s in segments), segments[0].lang,
                   segments[0].index,
                   f"{segments[0].location}–{segments[-1].location}")


def _align_block(a: list, b: list, ratio: float) -> list:
    """Length-based alignment. Returns [(Segment|None, Segment|None, confidence)]."""
    n, m = len(a), len(b)
    inf = float("inf")
    cost = [[inf] * (m + 1) for _ in range(n + 1)]
    back: list = [[None] * (m + 1) for _ in range(n + 1)]
    cost[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if cost[i][j] == inf:
                continue
            for da, db in MOVES:
                if i + da > n or j + db > m:
                    continue
                if da == 0 or db == 0:
                    step = SKIP_COST
                else:
                    step = _length_cost(sum(len(s.text) for s in a[i:i + da]),
                                        sum(len(s.text) for s in b[j:j + db]), ratio)
                    if da + db > 2:
                        step += MERGE_COST
                    if _digits(a[i:i + da]) != _digits(b[j:j + db]):
                        step += DIGIT_COST
                if cost[i][j] + step < cost[i + da][j + db]:
                    cost[i + da][j + db] = cost[i][j] + step
                    back[i + da][j + db] = (da, db)
    rows: list = []
    i, j = n, m
    while (i, j) != (0, 0):
        da, db = back[i][j]
        seg_a = _join(a[i - da:i]) if da else None
        seg_b = _join(b[j - db:j]) if db else None
        if seg_a and seg_b:
            confidence = math.exp(-_length_cost(len(seg_a.text), len(seg_b.text), ratio))
            if da + db > 2:
                confidence *= 0.8
        else:
            confidence = 1.0
        rows.append((seg_a, seg_b, round(confidence, 3)))
        i, j = i - da, j - db
    return rows[::-1]


def pair_segments(a: list, b: list) -> list:
    """Pair two ordered lists of Segments. Nothing is dropped: a segment with
    no partner comes back in a Pair whose other side is None."""
    anchors = find_anchors(a, b)
    # Expected length ratio b/a. Anchored paragraphs are known to correspond,
    # so they give a cleaner estimate than whole-file totals, which a missing
    # paragraph would distort.
    total_a = sum(len(a[i].text) for i, _ in anchors)
    total_b = sum(len(b[j].text) for _, j in anchors)
    if total_a < MIN_ANCHOR_CHARS:
        total_a = sum(len(s.text) for s in a)
        total_b = sum(len(s.text) for s in b)
    ratio = (total_b / total_a) if total_a and total_b else 1.0
    rows: list = []
    i0 = j0 = 0
    for i, j in anchors + [(len(a), len(b))]:
        rows.extend(_align_block(a[i0:i], b[j0:j], ratio))
        if i < len(a):
            rows.append((a[i], b[j], 1.0))
        i0, j0 = i + 1, j + 1
    return [Pair(pair_no=n, a=seg_a, b=seg_b, confidence=confidence)
            for n, (seg_a, seg_b, confidence) in enumerate(rows, start=1)]
