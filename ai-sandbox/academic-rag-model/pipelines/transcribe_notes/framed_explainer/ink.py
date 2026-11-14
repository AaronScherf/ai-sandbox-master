# pipelines/transcribe_notes/framed_explainer/ink.py
"""Ink regions, nearest-slide fallback and section anchoring. `cluster_ink`
ports the framer's JS clusterInk (same RULES); a parity test guards drift."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

INK_GAP_X, INK_GAP_Y, INK_MAX_W, INK_MAX_H = 75, 55, 1200, 850
ROW_Y = 250  # the framer's RULES.rowY, reused as the reading-order row band


@dataclass(frozen=True)
class Bounds:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h


@dataclass
class Region:
    region_id: str
    bounds: Bounds
    stroke_ids: list[str] = field(default_factory=list)


def _box(e: dict) -> Bounds:
    return Bounds(e["x"], e["y"], e["width"], e["height"])


def _union(a: Bounds, b: Bounds) -> Bounds:
    x, y = min(a.x, b.x), min(a.y, b.y)
    return Bounds(x, y, max(a.right, b.right) - x, max(a.bottom, b.bottom) - y)


def _axis_gap(a: Bounds, b: Bounds) -> tuple[float, float]:
    return (max(0, a.x - b.right, b.x - a.right), max(0, a.y - b.bottom, b.y - a.bottom))


def box_gap(a: Bounds, b: Bounds) -> float:
    gx, gy = _axis_gap(a, b)
    return math.hypot(gx, gy)


def cluster_ink(strokes: list[dict]) -> list[Region]:
    regions: list[Region] = []
    for s in sorted(strokes, key=lambda s: (s["y"], s["x"], s["id"])):
        b = _box(s)
        best, best_score = -1, math.inf
        for i, r in enumerate(regions):
            gx, gy = _axis_gap(r.bounds, b)
            u = _union(r.bounds, b)
            if gx > INK_GAP_X or gy > INK_GAP_Y or u.w > INK_MAX_W or u.h > INK_MAX_H:
                continue
            if gx + gy < best_score:
                best, best_score = i, gx + gy
        if best < 0:
            regions.append(Region(f"r{len(regions) + 1}", b, [s["id"]]))
        else:
            regions[best].bounds = _union(regions[best].bounds, b)
            regions[best].stroke_ids.append(s["id"])
    return regions


def _ranked(region: Region, slides: list[dict]) -> list[tuple[float, dict]]:
    return sorted(((box_gap(region.bounds, _box(s)), s) for s in slides),
                  key=lambda t: (t[0], t[1]["id"]))


def _between(a: Bounds, b: Bounds) -> Bounds | None:
    """The rectangle between the facing edges of a and b, if separated on an axis."""
    gx, gy = _axis_gap(a, b)
    if gx == 0 and gy == 0:
        return None
    x0 = min(a.right, b.right) if gx else max(a.x, b.x)
    x1 = max(a.x, b.x) if gx else min(a.right, b.right)
    y0 = min(a.bottom, b.bottom) if gy else max(a.y, b.y)
    y1 = max(a.y, b.y) if gy else min(a.bottom, b.bottom)
    return Bounds(x0, y0, max(0, x1 - x0), max(0, y1 - y0))


def _overlaps(a: Bounds, b: Bounds) -> bool:
    return a.x < b.right and a.right > b.x and a.y < b.bottom and a.bottom > b.y


def fallback_slide(region: Region, slides: list[dict], all_regions: list[Region],
                   margin: float = 0.5) -> str | None:
    """Nearest slide id when clearly nearest and nothing intervenes, else None."""
    if not slides:
        return None
    ranked = _ranked(region, slides)
    d1, nearest = ranked[0]
    if len(ranked) > 1 and not d1 < margin * ranked[1][0]:
        return None
    gap_box = _between(region.bounds, _box(nearest))
    if gap_box is not None and gap_box.w > 0 and gap_box.h > 0:
        for other in all_regions:
            if other.region_id != region.region_id and _overlaps(other.bounds, gap_box):
                return None
    return nearest["id"]


def anchor_for(region: Region, slides: list[dict],
               max_slide_widths: float = 1.5) -> tuple[str | None, str | None]:
    """(anchor slide id or None for standalone, near-tie second slide id or None)."""
    if not slides:
        return None, None
    ranked = _ranked(region, slides)
    d1, nearest = ranked[0]
    if d1 > max_slide_widths * nearest["width"]:
        return None, None
    also = None
    if len(ranked) > 1:
        d2, second = ranked[1]
        if d2 <= max_slide_widths * second["width"] and d1 > 0.5 * d2:
            also = second["id"]
    return nearest["id"], also


def reading_order(regions: list[Region]) -> list[Region]:
    ordered, rows = sorted(regions, key=lambda r: (r.bounds.y, r.bounds.x, r.region_id)), []
    for r in ordered:
        if rows and r.bounds.y - rows[-1][0] <= ROW_Y:
            rows[-1][1].append(r)
        else:
            rows.append((r.bounds.y, [r]))
    return [r for _, row in rows for r in sorted(row, key=lambda r: (r.bounds.x, r.region_id))]
