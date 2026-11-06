from __future__ import annotations

import io
import sys

from tools.corpus_health.cli import _use_utf8_streams


def test_streams_become_utf8_so_combining_accents_print(monkeypatch):
    raw_out, raw_err = io.BytesIO(), io.BytesIO()
    out = io.TextIOWrapper(raw_out, encoding="cp1252", newline="
")
    err = io.TextIOWrapper(raw_err, encoding="cp1252", newline="
")
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)

    _use_utf8_streams()
    print("Lecture é.md")  # would raise UnicodeEncodeError under cp1252
    print("bad ́", file=sys.stderr)
    out.flush()
    err.flush()

    assert raw_out.getvalue().decode("utf-8") == "Lecture é.md\n"
    assert raw_err.getvalue().decode("utf-8") == "bad ́\n"
