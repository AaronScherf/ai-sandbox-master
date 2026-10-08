# tests/agent/summary_enhance/test_summary_enhance_improve.py
import json

import pytest

from agent.summary_enhance import enhance
from agent.summary_enhance.enhance import run
from agent.summary_enhance.prompt import PROMPT_VERSION, build_topic_prompt
from agent.summary_enhance.source_loader import ExtraSource, load_guide
from conftest import make_topic_json


def _extra(topic, **kw):
    kw.setdefault("doc_type", "ta_notes")
    kw.setdefault("offering", "class_2024")
    kw.setdefault("chunk_id", "notes-1")
    kw.setdefault("file_id", "notes")
    return ExtraSource(topic, path="academic_notes/econ/class_2024/notes.md", citation="Notes p. 3", **kw)


def _out(vault):
    return vault.guide.with_name("guide.enhanced.md")


def test_prompt_version_bumped():
    assert PROMPT_VERSION == "2026-10-05.1"


def test_prompt_includes_only_the_topics_labels(vault):
    guide = load_guide(vault.guide, [_extra("Wald")])
    prompt = build_topic_prompt(guide, "Wald", [], 1400, source_labels={"S4"})
    assert "[S4]" in prompt and "Class notes: the Wald statistic" in prompt
    assert "Cameron: the Wald statistic" not in prompt and "[S1] §7.2.3" not in prompt


def test_prompt_without_labels_includes_everything_in_the_old_format(vault):
    guide = load_guide(vault.guide)
    prompt = build_topic_prompt(guide, "Wald", [], 1400)
    assert '[S1] §7.2.3 Wald Test Statistic, p. 249 -- academic_notes/econ/textbooks/cam.rag.md\n"""' in prompt
    assert "=== DRAFT GUIDE (not a source) ===" in prompt and "IMPROVEMENT" not in prompt


def test_improve_mode_prompt(vault):
    guide = load_guide(vault.guide, [_extra("Wald")])
    prompt = build_topic_prompt(guide, "Wald", [], 1400, mode="improve")
    assert "IMPROVEMENT pass" in prompt and "BASELINE GUIDE" in prompt
    assert "[S4] (class notes/slides, class_2024 offering) Notes p. 3 -- " in prompt
    assert "prefer the textbook" in prompt and "hand-written or transcribed" in prompt
    assert "it is not a source" in prompt


def test_rewrite_mode_has_no_improve_instructions(vault):
    assert "IMPROVEMENT" not in build_topic_prompt(load_guide(vault.guide), "Wald", [], 1400, mode="rewrite")


def _go(vault, llm, extras, **kw):
    kw.setdefault("topics", ["Wald", "LM"])
    kw.setdefault("min_words", 100)
    return run(str(vault.guide), llm=llm, extra_sources=extras, **kw)


def test_extra_sources_flow_end_to_end(vault, make_llm):
    llm = make_llm(make_topic_json("Wald", labels=("S4",)), make_topic_json("LM", labels=("S1",)))
    assert _go(vault, llm, [_extra("Wald"), _extra("LM", chunk_id="cam-1", file_id="cam", doc_type="", offering="")]) == 0
    assert "Class notes: the Wald statistic" in llm.calls[0] and "Class notes" not in llm.calls[1]
    text = _out(vault).read_text(encoding="utf-8")
    front = text.split("\n---\n\n", 1)[0]
    smap = json.loads(next(l for l in front.splitlines() if l.startswith("source_map: "))[len("source_map: "):])
    assert {e["chunk_id"] for e in smap} == {"notes-1", "cam-1"}
    assert next(e for e in smap if e["chunk_id"] == "notes-1")["doc_type"] == "ta_notes"


def test_a_topic_citing_another_topics_source_is_rejected(vault, make_llm):
    # LM's own set is {S1}; citing S4 (Wald's class notes) is invalid for LM, twice -> exit 3
    bad = make_topic_json("LM", labels=("S4",))
    llm = make_llm(make_topic_json("Wald", labels=("S4",)), bad, bad)
    assert _go(vault, llm, [_extra("Wald"), _extra("LM", chunk_id="cam-1", file_id="cam", doc_type="", offering="")]) == 3
    assert not _out(vault).exists()
    assert "unknown label 'S4'" in llm.calls[2]


def test_improve_mode_is_passed_to_every_call(vault, make_llm):
    llm = make_llm(make_topic_json("Wald", labels=("S4",)), make_topic_json("LM", labels=("S4",)))
    assert _go(vault, llm, [_extra("Wald"), _extra("LM")], mode="improve") == 0
    assert all("IMPROVEMENT pass" in c for c in llm.calls)


def test_unknown_mode_is_an_input_error(vault, make_llm):
    llm = make_llm()
    assert _go(vault, llm, None, mode="sideways") == 2 and llm.calls == []


def test_missing_extra_chunk_exits_before_any_call(vault, make_llm):
    llm = make_llm()
    assert _go(vault, llm, [ExtraSource("Wald", "gone-9", "notes", "p", "c")]) == 2
    assert llm.calls == []


def test_dry_run_reports_sources_and_mode(vault, make_llm, capsys):
    assert _go(vault, make_llm(), [_extra("Wald")], mode="improve", dry_run=True) == 0
    out = capsys.readouterr().out
    assert "4 chunks" in out and "mode improve" in out


def test_main_passes_mode(vault, monkeypatch):
    captured = {}
    monkeypatch.setattr(enhance, "run", lambda guide, **kw: captured.update(kw) or 0)
    enhance.main([str(vault.guide), "--mode", "improve"])
    assert captured["mode"] == "improve" and captured["extra_sources"] is None
    enhance.main([str(vault.guide)])
    assert captured["mode"] == "rewrite"


def test_improve_mode_keeps_the_guides_own_sources_visible_to_every_topic(vault, make_llm):
    llm = make_llm(make_topic_json("Wald", labels=("S1", "S4")), make_topic_json("LM", labels=("S2",)))
    assert _go(vault, llm, [_extra("Wald"), _extra("LM", chunk_id="unused-1", file_id="cam")], mode="improve") == 0
    assert "[S1]" in llm.calls[1] and "[S2]" in llm.calls[1] and "[S3]" in llm.calls[1]
    assert "Class notes: the Wald statistic" not in llm.calls[1]


def test_load_guide_can_share_own_refs_across_topics(vault):
    guide = load_guide(vault.guide, [_extra("Wald")], share_own_refs=True)
    assert guide.labels_for("Wald") == {"S1", "S2", "S3", "S4"}
    assert load_guide(vault.guide, [_extra("Wald")]).labels_for("Wald") == {"S4"}


def test_a_reused_label_takes_the_extras_doc_type_and_offering(vault):
    guide = load_guide(vault.guide, [_extra("Wald", chunk_id="cam-1", file_id="cam", doc_type="textbook", offering="")])
    assert guide.sources[0].doc_type == "textbook"
    guide = load_guide(vault.guide, [_extra("Wald", chunk_id="cam-1", file_id="cam", doc_type="ta_notes", offering="class_2024")])
    assert (guide.sources[0].doc_type, guide.sources[0].offering) == ("ta_notes", "class_2024")


def test_enhance_dry_run_sizes_the_real_improve_prompt(vault, make_llm, capsys):
    import re
    def size(extras, **kw):
        _go(vault, make_llm(), extras, dry_run=True, **kw)
        return int(re.search(r"about (\d+) prompt characters", capsys.readouterr().out).group(1))
    extras = [_extra("Wald"), _extra("LM", chunk_id="unused-1", file_id="cam")]
    assert size(extras, mode="improve") > size(extras, mode="rewrite")


SECTIONED = ("# Wald and LM tests\n\n## Wald\n\nWALD-DRAFT-TEXT\n\n### Sub\n\nmore wald\n\n---\n\n"
             "## LM\n\nLM-DRAFT-TEXT\n\n---\n\n## Other\n\nOTHER-DRAFT-TEXT\n")


def _sectioned(vault):
    text = vault.guide.read_text(encoding="utf-8")
    vault.guide.write_text(text.replace("# Wald and LM tests\n\nBody text.\n", SECTIONED), encoding="utf-8")


def test_baseline_section_extracts_one_titled_section():
    from agent.summary_enhance.enhance import baseline_section
    body = "intro\n\n## Wald\n\nWALD\n\n### Sub\n\nmore\n\n---\n\n## LM\n\nLM\n"
    assert baseline_section(body, "Wald") == "## Wald\n\nWALD\n\n### Sub\n\nmore"
    assert baseline_section(body, "  lm ") == "## LM\n\nLM"
    assert baseline_section(body, "Missing") is None


def test_prompt_can_replace_the_baseline_body(vault):
    guide = load_guide(vault.guide, [_extra("Wald")])
    prompt = build_topic_prompt(guide, "Wald", [], 1400, mode="improve", baseline_body="ONLY-THIS-SECTION")
    assert "ONLY-THIS-SECTION" in prompt and "Body text." not in prompt and "BASELINE GUIDE" in prompt


def test_per_topic_baseline_gives_each_topic_only_its_own_section_and_passages(vault, make_llm):
    _sectioned(vault)
    llm = make_llm(make_topic_json("Wald", labels=("S4",)), make_topic_json("LM", labels=("S1",)))
    assert _go(vault, llm, [_extra("Wald"), _extra("LM", chunk_id="cam-1", file_id="cam", doc_type="", offering="")],
               mode="improve", baseline="topic") == 0
    wald, lm = llm.calls[0], llm.calls[1]
    assert "WALD-DRAFT-TEXT" in wald and "LM-DRAFT-TEXT" not in wald and "OTHER-DRAFT-TEXT" not in wald
    assert "LM-DRAFT-TEXT" in lm and "WALD-DRAFT-TEXT" not in lm
    assert "Class notes: the Wald statistic" in wald and "Cameron: the Wald statistic" not in wald


def test_full_baseline_remains_the_default(vault, make_llm):
    _sectioned(vault)
    llm = make_llm(make_topic_json("Wald", labels=("S4",)), make_topic_json("LM", labels=("S1",)))
    assert _go(vault, llm, [_extra("Wald"), _extra("LM", chunk_id="cam-1", file_id="cam", doc_type="", offering="")],
               mode="improve") == 0
    assert "WALD-DRAFT-TEXT" in llm.calls[0] and "OTHER-DRAFT-TEXT" in llm.calls[0]


def test_per_topic_baseline_needs_a_section_for_every_topic(vault, make_llm, capsys):
    _sectioned(vault)
    llm = make_llm()
    assert _go(vault, llm, [_extra("Wald")], mode="improve", baseline="topic", topics=["Wald", "Missing"]) == 2
    assert "Missing" in capsys.readouterr().out and llm.calls == []


def test_unknown_baseline_value_is_rejected(vault, make_llm, capsys):
    assert _go(vault, make_llm(), [_extra("Wald")], mode="improve", baseline="half") == 2
    assert "--baseline" in capsys.readouterr().out


def test_dry_run_prompt_is_smaller_with_a_per_topic_baseline(vault, make_llm, capsys):
    _sectioned(vault)
    extras = [_extra("Wald")]
    _go(vault, make_llm(), extras, mode="improve", dry_run=True)
    full = int(capsys.readouterr().out.split("about ")[1].split(" prompt")[0])
    _go(vault, make_llm(), extras, mode="improve", baseline="topic", dry_run=True)
    topic = int(capsys.readouterr().out.split("about ")[1].split(" prompt")[0])
    assert topic < full
