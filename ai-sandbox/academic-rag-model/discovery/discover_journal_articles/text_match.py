"""
text_match.py
Plain-text normalization shared by reconcile_needs_manual.py and
audit_metadata.py -- promoted out to a small standalone module (rather
than one importing it from the other) specifically because
reconcile_needs_manual.py's own main() now calls into audit_metadata.py
(spec S2), which would otherwise create an import cycle.
"""
from __future__ import annotations

import re

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize(text: str) -> str:
    return _NON_ALNUM_RE.sub("", text.lower())
