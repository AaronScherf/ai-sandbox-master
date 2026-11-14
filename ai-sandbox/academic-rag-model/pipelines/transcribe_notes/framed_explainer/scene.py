# pipelines/transcribe_notes/framed_explainer/scene.py
"""Read-only parser/classifier for .excalidraw.md scenes. Mirrors the JS
`classify` in Auto-Frame Slides.md; never writes a scene."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from lzstring import LZString


class SceneFormatError(ValueError):
    """The file has no decodable compressed-json drawing section."""


@dataclass
class Scene:
    path: str
    sha1: str
    elements: list[dict]
    registry: dict[str, str]


@dataclass
class Classified:
    slides: list[dict]
    explanations: list[dict]
    ink: list[dict]
    frames: list[dict]
    other: list[dict]
    cards: list[dict] = field(default_factory=list)


_EMBEDDED = re.compile(
    r"^## Embedded Files[^\r\n]*\r?\n([\s\S]*?)(?=^## |^%%|^# |(?![\s\S]))", re.M)
_PAIR = re.compile(r"^([0-9a-f]{40}):\s*(?:\[\[(.*?)\]\]|markdown-image)", re.I)
_DRAWING = re.compile(r"```compressed-json\s*(.*?)```", re.S)


def _registry(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    m = _EMBEDDED.search(text)
    if not m:
        return result
    for line in re.split(r"\r?\n", m.group(1)):
        pair = _PAIR.match(line)
        if pair:
            result[pair.group(1)] = pair.group(2) or "markdown-image"
    return result


def load_scene(path: str) -> Scene:
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8")
    m = _DRAWING.search(text)
    if not m:
        raise SceneFormatError(f"no compressed-json drawing section in {path}")
    packed = "".join(m.group(1).split())
    unpacked = LZString.decompressFromBase64(packed)
    if not unpacked:
        raise SceneFormatError(f"compressed-json did not decode in {path}")
    try:
        elements = json.loads(unpacked)["elements"]
    except (ValueError, KeyError) as exc:
        raise SceneFormatError(f"drawing JSON invalid in {path}: {exc}") from exc
    sha1 = hashlib.sha1(raw.replace(b"\r\n", b"\n")).hexdigest()
    return Scene(path=path, sha1=sha1, elements=elements, registry=_registry(text))


def _is_slide(e: dict, link: str) -> bool:
    w, h = e["width"], e["height"]
    sized = abs(w - 907) <= 25 and abs(h - 510) <= 20
    wide = w >= 700 and h > 0 and abs(w / h - 16 / 9) < 0.035
    four_three = w >= 500 and h > 0 and abs(w / h - 4 / 3) < 0.035
    return (sized or wide or four_three) and link.lower().endswith(".png")


def classify(scene: Scene) -> Classified:
    out = Classified([], [], [], [], [])
    for e in scene.elements:
        if e.get("isDeleted"):
            continue
        t = e["type"]
        if t == "frame":
            out.frames.append(e)
        elif t == "freedraw":
            out.ink.append(e)
        elif t != "image":
            out.other.append(e)
        else:
            link = scene.registry.get(e.get("fileId"), "")
            if (e.get("customData") or {}).get("autoExplainKey"):
                out.cards.append(e)
            elif link == "markdown-image" or (e.get("customData") or {}).get("markdownImage"):
                out.explanations.append(e)
            elif _is_slide(e, link):
                out.slides.append(e)
            else:
                out.other.append(e)
    return out
