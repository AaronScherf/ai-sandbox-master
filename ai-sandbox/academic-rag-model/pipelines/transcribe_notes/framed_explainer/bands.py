# pipelines/transcribe_notes/framed_explainer/bands.py
"""Ink-to-slide assignment. Port of the framer's JS `matchInk` (Auto-Frame Slides.md);
tests/.../test_framed_explainer_bands_parity.py guards drift.

1. Slides that do not overlap in y form a column (x may jitter); each owns a band from
   its top edge to the next slide's top. Slides that do not overlap in x form a row
   (same rule, axes swapped).
2. Strokes near a band edge are settled by drawing time (`created`) when usable; ink
   above the next slide's top never moves down; bursts of writing stay together; with no
   usable time, ink chained to the ink above defers to the slide above.
3. Any other layout uses a proximity classifier that says "cannot tell" rather than
   forcing a fit.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from pipelines.transcribe_notes.framed_explainer.ink import (
    INK_GAP_X, INK_GAP_Y, Bounds, box_gap, cluster_ink, merge_fragments)

ZONE_FRAC, LEAD, TAIL_HEIGHTS, REACH_WIDTHS = 0.25, 1, 6, 5
SLACK, MAX_MISFIT, BURST_GAP = 120000, 0.15, 10000
ACCEPT, SCALE, NULL_WEIGHT = 0.6, 0.35, math.exp(-3)


@dataclass
class Assignment:
    mode: str                                   # "column" | "row" | "proximity"
    by_slide: dict[str, list[str]] = field(default_factory=dict)
    loose: list[str] = field(default_factory=list)   # unassigned / cannot tell


def _transpose(e: dict) -> dict:
    return {**e, "x": e["y"], "y": e["x"], "width": e["height"], "height": e["width"]}


def _is_column(slides: list[dict]) -> bool:
    s = sorted(slides, key=lambda e: e["y"])
    return all(s[i]["y"] + s[i]["height"] <= s[i + 1]["y"] for i in range(len(s) - 1))


def _finite(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _trusted(strokes: list[dict]):
    count = Counter(s["created"] for s in strokes if _finite(s.get("created")))
    return lambda s: _finite(s.get("created")) and count[s["created"]] == 1


def _time_split(early: list[float], late: list[float]) -> dict | None:
    if len(early) < 3 or len(late) < 3:
        return None
    med = lambda a: sorted(a)[len(a) // 2]
    forward = med(early) <= med(late)
    first, second = (early, late) if forward else (late, early)
    times = sorted(set(first) | set(second))
    cuts = []
    for i in range(len(times) - 1):
        cut = (times[i] + times[i + 1]) / 2
        cuts.append((cut, sum(t > cut for t in first) + sum(t <= cut for t in second)))
    if not cuts:
        return None
    best = min(err for _, err in cuts)
    if best / (len(early) + len(late)) > MAX_MISFIT:
        return None
    good = [c for c, err in cuts if err == best]
    return {"cut": good[len(good) // 2], "forward": forward, "lo": times[0], "hi": times[-1]}


def _b(e: dict) -> Bounds:
    return Bounds(e["x"], e["y"], e["width"], e["height"])


def _near(a: dict, b: dict) -> bool:
    ax, bx = _b(a), _b(b)
    gx = max(0, ax.x - bx.right, bx.x - ax.right)
    gy = max(0, ax.y - bx.bottom, bx.y - ax.bottom)
    return gx <= INK_GAP_X and gy <= INK_GAP_Y


def _assign_bands(slides: list[dict], strokes: list[dict]) -> tuple[dict[str, list[str]], list[str]]:
    sl = sorted(slides, key=lambda s: (s["y"], s["id"]))
    h = max(s["height"] for s in sl)
    w = max(s["width"] for s in sl)
    zone, top = ZONE_FRAC * h, [s["y"] for s in sl]
    lo, hi = min(s["x"] for s in sl), max(s["x"] + s["width"] for s in sl)
    last = sl[-1]
    cy = lambda s: s["y"] + s["height"] / 2
    in_reach = lambda s: (s["x"] + s["width"] >= lo - REACH_WIDTHS * w
                          and s["x"] <= hi + REACH_WIDTHS * w
                          and top[0] - LEAD * h <= cy(s) <= last["y"] + last["height"] + TAIL_HEIGHTS * h)
    cand = [s for s in strokes if in_reach(s)]
    loose = [s["id"] for s in strokes if not in_reach(s)]

    def band_of(y: float) -> int:
        k = 0
        for i, t in enumerate(top):
            if y >= t:
                k = i
        return k

    base = {s["id"]: band_of(cy(s)) for s in cand}
    owner = dict(base)
    trusted = _trusted(cand)
    for k in range(len(sl) - 1):
        edge = top[k + 1]
        in_zone = lambda s: abs(cy(s) - edge) <= zone
        above = [s for s in cand if base[s["id"]] == k and not in_zone(s)]
        below = [s for s in cand if base[s["id"]] == k + 1 and not in_zone(s)]
        amb = [s for s in cand if in_zone(s) and base[s["id"]] in (k, k + 1)]
        if not amb:
            continue
        split = _time_split([s["created"] for s in above if trusted(s)],
                            [s["created"] for s in below if trusted(s)])
        burst_up: set[str] = set()
        burst: list[dict] = []
        last_t = None

        def flush():
            nonlocal burst
            if any(base[s["id"]] == k for s in burst):
                burst_up.update(s["id"] for s in burst)
            burst = []
        for s in sorted((s for s in amb if trusted(s)), key=lambda s: s["created"]):
            if last_t is not None and s["created"] - last_t > BURST_GAP:
                flush()
            burst.append(s)
            last_t = s["created"]
        flush()
        pending, chain = [], []
        for s in amb:
            if base[s["id"]] == k:
                chain.append(s)
                continue
            if s["id"] in burst_up:
                owner[s["id"]] = k
                chain.append(s)
                continue
            if (split and trusted(s) and split["lo"] - SLACK <= s["created"] <= split["hi"] + SLACK):
                early = s["created"] <= split["cut"]
                owner[s["id"]] = k if early == split["forward"] else k + 1
            else:
                pending.append(s)
        reached: set[str] = set()
        queue = [s for s in above if cy(s) >= edge - zone - INK_GAP_Y * 2]
        while queue:
            cur = queue.pop()
            for s in pending + chain:
                if s["id"] not in reached and _near(cur, s):
                    reached.add(s["id"])
                    queue.append(s)
        for s in pending:
            owner[s["id"]] = k if s["id"] in reached else base[s["id"]]
    by_slide: dict[str, list[str]] = {}
    for s in cand:
        by_slide.setdefault(sl[owner[s["id"]]]["id"], []).append(s["id"])
    return by_slide, loose


def _proximity(slides: list[dict], strokes: list[dict]) -> tuple[dict[str, list[str]], list[str]]:
    by_slide: dict[str, list[str]] = {}
    loose: list[str] = []
    for region in merge_fragments(cluster_ink(strokes)):
        weights = []
        for s in slides:
            d = box_gap(_b(s), region.bounds)
            weights.append((math.exp(-d / (SCALE * s["width"])), s["id"]))
        total = sum(wt for wt, _ in weights) + NULL_WEIGHT
        weights.sort(key=lambda t: (-t[0], t[1]))
        if weights[0][0] / total < ACCEPT:
            loose.extend(region.stroke_ids)
            continue
        by_slide.setdefault(weights[0][1], []).extend(region.stroke_ids)
    return by_slide, loose


def assign_strokes(slides: list[dict], strokes: list[dict]) -> Assignment:
    """Assign each stroke to a slide id, or leave it loose (cannot tell). Slides and
    strokes are Excalidraw element dicts (id, x, y, width, height; strokes may carry
    `created`)."""
    if not slides:
        return Assignment("proximity", {}, [s["id"] for s in strokes])
    if _is_column(slides):
        mode, by_slide, loose = "column", *_assign_bands(slides, strokes)
    elif _is_column([_transpose(s) for s in slides]):
        mode = "row"
        by_slide, loose = _assign_bands([_transpose(s) for s in slides],
                                        [_transpose(s) for s in strokes])
    else:
        mode, (by_slide, loose) = "proximity", _proximity(slides, strokes)
    return Assignment(mode, {k: sorted(v) for k, v in by_slide.items()}, sorted(loose))
