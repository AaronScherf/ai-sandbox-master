"""Stable `hub_id` identity for authored notes (hub-path-resilience P3).

The id lives in frontmatter (`.md`, including `.excalidraw.md`) or, for plain
`.excalidraw` JSON, as a top-level `"hub_id"` key. Writes are byte-level
insertions so BOM, CRLF, key order and formatting are preserved. An existing
id is never overwritten. The content hash ignores the frontmatter line (see
index_card.NOTE_IDENTITY_FIELDS).
"""

import json
import re
import uuid

_BOM = b"\xef\xbb\xbf"
_FM_ID = re.compile(rb"^hub_id\s*:\s*(.*?)\s*$")


def new_hub_id() -> str:
    return uuid.uuid4().hex[:12]


def _is_json_scene(path: str) -> bool:
    return path.lower().endswith(".excalidraw")


def _frontmatter_end(lines: list[bytes]) -> int | None:
    if not lines or lines[0].removeprefix(_BOM).rstrip(b"\r") != b"---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip(b"\r") == b"---":
            return i
    return None


def read_hub_id(path: str) -> str | None:
    with open(path, "rb") as f:
        data = f.read()
    if _is_json_scene(path):
        try:
            value = json.loads(data.decode("utf-8-sig")).get("hub_id")
        except (ValueError, AttributeError):
            return None
        return value if isinstance(value, str) and value else None
    lines = data.split(b"\n")
    end = _frontmatter_end(lines)
    if end is None:
        return None
    for line in lines[1:end]:
        m = _FM_ID.match(line.rstrip(b"\r"))
        if m:
            value = m.group(1).strip(b"\"'").decode("utf-8", "replace")
            return value or None
    return None


def check_stampable(path: str, data: bytes | None = None) -> None:
    """Raise ValueError if write_hub_id would refuse this file (empty
    frontmatter block). Lets a dry run report exactly what --apply skips."""
    if _is_json_scene(path):
        return
    if data is None:
        with open(path, "rb") as f:
            data = f.read()
    lines = data.split(b"\n")
    end = _frontmatter_end(lines)
    if end is not None and not any(l.strip() for l in lines[1:end]):
        raise ValueError(f"cannot stamp hub_id: empty frontmatter block in {path}")


def replace_hub_id(path: str) -> str:
    """Give a (possibly copied) note a fresh hub_id, replacing any existing
    one in place, and return it. For clones, which must not share the
    canonical's identity."""
    with open(path, "rb") as f:
        data = f.read()
    lines = data.split(b"\n")
    end = _frontmatter_end(lines)
    if end is not None and not _is_json_scene(path):
        for i in range(1, end):
            if _FM_ID.match(lines[i].rstrip(b"\r")):
                hub_id = new_hub_id()
                cr = b"\r" if lines[i].endswith(b"\r") else b""
                lines[i] = b"hub_id: " + hub_id.encode("ascii") + cr
                with open(path, "wb") as f:
                    f.write(b"\n".join(lines))
                return hub_id
    return write_hub_id(path)


def write_hub_id(path: str, hub_id: str | None = None) -> str:
    """Stamp `hub_id` into the file and return it. Returns the existing id
    (file untouched) if one is already present.

    Raises ValueError, leaving the file untouched, if the file has a literal
    empty frontmatter block (`---` fences with no key lines): stamping it would
    change the content hash, since that block is indistinguishable from one
    created for a bare note. Callers (the write_hub_ids tool) must catch this
    and report the file as skipped."""
    existing = read_hub_id(path)
    if existing:
        return existing
    with open(path, "rb") as f:
        data = f.read()
    check_stampable(path, data)
    hub_id = hub_id or new_hub_id()
    if _is_json_scene(path):
        new = _insert_json_key(data, hub_id)
    else:
        new = _insert_frontmatter(data, hub_id)
    with open(path, "wb") as f:
        f.write(new)
    return hub_id


def _insert_frontmatter(data: bytes, hub_id: str) -> bytes:
    eol = b"\r\n" if b"\r\n" in data else b"\n"
    line = b"hub_id: " + hub_id.encode("ascii") + eol
    lines = data.split(b"\n")
    end = _frontmatter_end(lines)
    if end is None:
        bom = _BOM if data.startswith(_BOM) else b""
        return bom + b"---" + eol + line + b"---" + eol + data.removeprefix(_BOM)
    for i in range(1, end):
        if _FM_ID.match(lines[i].rstrip(b"\r")):
            # Existing but empty `hub_id:` line: fill it in place, no duplicate key.
            cr = b"\r" if lines[i].endswith(b"\r") else b""
            lines[i] = b"hub_id: " + hub_id.encode("ascii") + cr
            return b"\n".join(lines)
    # Insert before the closing fence (line `end`), keeping every other byte.
    before = b"\n".join(lines[:end]) + b"\n"
    return before + line + b"\n".join(lines[end:])


def _insert_json_key(data: bytes, hub_id: str) -> bytes:
    start = data.find(b"{")
    if start < 0 or data[:start].removeprefix(_BOM).strip():
        raise ValueError("not a JSON object scene")
    rest = data[start + 1:]
    key = b'"hub_id": ' + json.dumps(hub_id).encode("ascii")
    sep = b"" if rest.lstrip().startswith(b"}") else b","
    return data[: start + 1] + key + sep + rest
