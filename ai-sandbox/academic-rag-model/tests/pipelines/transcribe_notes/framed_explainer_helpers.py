"""Test helpers: build a minimal .excalidraw.md scene in tmp dirs."""
from __future__ import annotations

import json

from lzstring import LZString

SLIDE_A = "a" * 40
SLIDE_B = "b" * 40
MD_C = "c" * 40


def el(id, type, x=0, y=0, w=10, h=10, **extra):
    base = {"id": id, "type": type, "x": x, "y": y, "width": w, "height": h,
            "isDeleted": False, "version": 1}
    base.update(extra)
    return base


def slide(id, x, y, file_id=SLIDE_A, **extra):
    return el(id, "image", x, y, 907, 510, fileId=file_id, **extra)


def stroke(id, x, y, w=20, h=20, **extra):
    return el(id, "freedraw", x, y, w, h, points=[[0, 0]], **extra)


def scene_text(elements, registry=None, newline="\n"):
    registry = registry if registry is not None else {
        SLIDE_A: "[[slide-1.png]]", SLIDE_B: "[[slide-2.png]]", MD_C: "markdown-image"}
    payload = json.dumps({"type": "excalidraw", "elements": elements, "appState": {}})
    packed = LZString.compressToBase64(payload)
    lines = ["---", "excalidraw-plugin: parsed", "---", "",
             "# Excalidraw Data", "", "## Text Elements", "", "## Embedded Files"]
    for fid, link in registry.items():
        lines.append(f"{fid}: {link}")
        lines.append("")
    lines += ["%%", "## Drawing", "```compressed-json", packed, "```", "%%", ""]
    return newline.join(lines)


def write_scene(path, elements, registry=None, newline="\n"):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(scene_text(elements, registry, newline))
    return str(path)
