"""New folder names become one review item each (hub-path-resilience P4, Task 5)."""
from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path

import pytest

from core.indexer import reconcile_apply
from core.indexer.review_envelope import _digest, vocab_name_to_item
from tools import hub_review
from tools.corpus_health.cli import main
from tools.corpus_health.state import StateStore


@pytest.fixture(autouse=True)
def _no_model_client(monkeypatch):
    import core.env.gemini_utils as gemini_utils
    from google import genai

    def boom(*args, **kwargs):
        raise AssertionError("no model client may be constructed or called")

    monkeypatch.setattr(gemini_utils, "get_gemini_client", boom)
    monkeypatch.setattr(genai, "Client", boom)


@pytest.fixture(autouse=True)
def _fake_lock(monkeypatch):
    @contextlib.contextmanager
    def fake(roots, action, **kw):
        yield None

    monkeypatch.setattr(reconcile_apply, "corpus_write_lock", fake)


def _file(hub: Path, rel: str) -> None:
    path = hub / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")


def _hub(tmp_path: Path) -> Path:
    hub = tmp_path / "hub"
    (hub / "hub_config.json").parent.mkdir(parents=True, exist_ok=True)
    (hub / "hub_config.json").write_text(json.dumps({"names": {}}, indent=2) + "\n", encoding="utf-8")
    for course in ("econ", "micro"):
        _file(hub, f"academic_notes/{course}/exam_kits/a.md")  # two courses -> category candidate
    _file(hub, "academic_notes/econ/2026/a.md")                 # year-shaped -> group candidate
    _file(hub, "academic_notes/econ/Recitation Notes/a.md")     # one course -> unclassified
    return hub


def _cfg(tmp_path: Path, hub: Path) -> Path:
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"version": 1, "academic_hub_root": str(hub), "academic_notes_root": None,
                               "required_roots": [], "markdown_policies": []}), encoding="utf-8")
    return cfg


def _scan(tmp_path, hub, capsys=None):
    state = tmp_path / "state"
    main(["scan", "--config", str(_cfg(tmp_path, hub)), "--state-dir", str(state)])
    if capsys:
        capsys.readouterr()
    return StateStore(state)


def _vocab_entries(store):
    return {e["finding"]["title"]: e for e in store.entries(kinds={"vocab_name"})}


def _open_names(hub, store):
    return {i.subject_ids[0]: i for i in hub_review.collect(str(hub), store, raise_items=False)
            if i.type == "vocab_name"}


def test_new_folder_name_raises_one_item(tmp_path, capsys):
    hub = _hub(tmp_path)
    store = _scan(tmp_path, hub, capsys)
    entries = _vocab_entries(store)
    assert set(entries) == {"exam_kits", "2026", "Recitation Notes"}
    assert entries["exam_kits"]["finding"]["fingerprint"] == _digest("vocab_name", "exam_kits")
    items = _open_names(hub, store)
    assert set(items) == set(entries)
    cands = items["exam_kits"].candidates
    assert [c["kind"] for c in cands] == ["category", "group", "ignore"]
    assert [c["proposed"] for c in cands] == [True, False, False]
    assert cands[0]["courses"] == ["econ", "micro"]
    assert items["exam_kits"] == vocab_name_to_item("exam_kits", ["econ", "micro"], "category")
    _scan(tmp_path, hub, capsys)  # rescan: still one entry per name, not duplicated
    assert len(store.entries(kinds={"vocab_name"})) == 3


def test_unclassified_single_course_name_is_raised_without_proposal(tmp_path, capsys):
    hub = _hub(tmp_path)
    items = _open_names(hub, _scan(tmp_path, hub, capsys))
    cands = items["Recitation Notes"].candidates
    assert [c["kind"] for c in cands] == ["category", "group", "ignore"]
    assert not any(c["proposed"] for c in cands)
    assert [c["proposed"] for c in items["2026"].candidates] == [False, True, False]


def test_confirmed_name_not_raised_again(tmp_path, capsys):
    hub = _hub(tmp_path)
    store = _scan(tmp_path, hub, capsys)
    results = hub_review.apply_decisions(
        str(hub), [{"item_id": _digest("vocab_name", "exam_kits"), "action": "accept", "chosen": "category"}],
        store=store)
    assert results[0]["outcome"] == "applied"
    store = _scan(tmp_path, hub, capsys)
    assert "exam_kits" not in _open_names(hub, store)
    assert _vocab_entries(store)["exam_kits"]["status"] in {"vanished", "applied"}
    pending = [e["finding"]["title"] for e in store.pending() if e["finding"]["kind"] == "vocab_name"]
    assert "exam_kits" not in pending


def test_declined_name_stays_declined_across_scans(tmp_path, capsys):
    hub = _hub(tmp_path)
    store = _scan(tmp_path, hub, capsys)
    iid = _digest("vocab_name", "recitation notes")
    results = hub_review.apply_decisions(str(hub), [{"item_id": iid, "action": "decline"}], store=store)
    assert results[0]["outcome"] == "applied"
    store = _scan(tmp_path, hub, capsys)
    assert _vocab_entries(store)["Recitation Notes"]["status"] == "declined"
    assert "Recitation Notes" not in _open_names(hub, store)
    assert "Recitation Notes" not in [e["finding"]["title"] for e in store.pending()]
    assert json.loads((hub / "hub_config.json").read_text(encoding="utf-8")) == {"names": {}}


def test_accept_writes_hub_config_via_confirm(tmp_path, capsys):
    hub = _hub(tmp_path)
    store = _scan(tmp_path, hub, capsys)
    iid = _digest("vocab_name", "2026")
    dry = hub_review.apply_decisions(str(hub), [{"item_id": iid, "action": "accept", "chosen": "group"}],
                                     dry_run=True, store=store)
    assert dry[0]["outcome"] == "would_apply"
    assert json.loads((hub / "hub_config.json").read_text(encoding="utf-8")) == {"names": {}}
    bad = hub_review.apply_decisions(str(hub), [{"item_id": iid, "action": "accept", "chosen": "nonsense"}],
                                     store=store)
    assert bad[0]["outcome"] == "error"
    ok = hub_review.apply_decisions(str(hub), [{"item_id": iid, "action": "accept", "chosen": "group"}],
                                    store=store)
    assert ok[0]["outcome"] == "applied"
    data = json.loads((hub / "hub_config.json").read_text(encoding="utf-8"))
    assert data["names"]["2026"] == {"kind": "group", "source": "owner"}
    assert "impact of '2026' as group" in capsys.readouterr().out


def test_defer_keeps_item_listed_as_deferred(tmp_path, capsys):
    hub = _hub(tmp_path)
    store = _scan(tmp_path, hub, capsys)
    iid = _digest("vocab_name", "exam_kits")
    assert hub_review.apply_decisions(str(hub), [{"item_id": iid, "action": "defer"}],
                                      store=store)[0]["outcome"] == "deferred"
    assert _open_names(hub, store)["exam_kits"].status == "deferred"


def test_accepted_vocab_finding_does_not_crash_corpus_health_apply():
    from tools.corpus_health.actions import _blocked_reason
    assert "hub_review" in _blocked_reason("vocab_name")


def test_scan_never_writes_hub_config(tmp_path, capsys):
    hub = _hub(tmp_path)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (hub / "hub_config.json",)}
    mtime = (hub / "hub_config.json").stat().st_mtime_ns
    _scan(tmp_path, hub, capsys)
    main(["scan", "--config", str(_cfg(tmp_path, hub)), "--no-state"])
    capsys.readouterr()
    hub_review.export(str(hub), _scan(tmp_path, hub), raise_items=False)
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    assert (hub / "hub_config.json").stat().st_mtime_ns == mtime
