# tests/agent/summary_enhance/test_summary_enhance_extend.py
"""The extend role: act only on thin sections, write new topics fresh, carry notes and comparisons
through, and record token usage."""
import json

from agent.summary_enhance.enhance import run
from agent.summary_enhance.source_loader import ExtraSource
from conftest import make_topic_json

LONG = " ".join(["word"] * 40)
BODY = ("# Wald and LM tests\n\n## Source note\n\nNOTE-TEXT\n\n---\n\n"
        f"## Wald\n\n{LONG} WALD-LONG\n\n---\n\n## LM\n\nLM-SHORT\n\n---\n\n## Compare\n\nCOMPARE-TEXT\n")


def _guide(vault):
    text = vault.guide.read_text(encoding="utf-8")
    vault.guide.write_text(text.replace("# Wald and LM tests\n\nBody text.\n", BODY), encoding="utf-8")


def _out(vault):
    return vault.guide.with_name("guide.enhanced.md")


def _front(vault, key):
    front = _out(vault).read_text(encoding="utf-8").split("\n---\n\n", 1)[0]
    line = next((l for l in front.splitlines() if l.startswith(key + ": ")), None)
    return None if line is None else json.loads(line[len(key) + 2:])


def _go(vault, llm, **kw):
    kw.setdefault("topics", ["Wald", "LM"])
    kw.setdefault("min_words", 100)
    kw.setdefault("mode", "improve")
    return run(str(vault.guide), llm=llm, **kw)


def test_sections_at_or_above_the_threshold_pass_through_unchanged(vault, make_llm):
    _guide(vault)
    llm = make_llm(make_topic_json("LM", labels=("S1",)))
    assert _go(vault, llm, baseline="topic", only_below=20) == 0
    assert len(llm.calls) == 1 and "LM-SHORT" in llm.calls[0]
    text = _out(vault).read_text(encoding="utf-8")
    body = text.split("\n---\n\n", 1)[1]
    assert f"## Wald\n\n{LONG} WALD-LONG" in body and body.index("## Wald") < body.index("## LM")
    assert _front(vault, "unchanged_topics") == ["Wald"] and _front(vault, "topics") == ["Wald", "LM"]


def test_nothing_to_generate_makes_no_call(vault, make_llm):
    _guide(vault)
    llm = make_llm()
    assert _go(vault, llm, topics=["Wald"], baseline="topic", only_below=20) == 0
    assert llm.calls == [] and "WALD-LONG" in _out(vault).read_text(encoding="utf-8")


def test_only_below_needs_topics_and_a_positive_number(vault, make_llm, capsys):
    _guide(vault)
    assert _go(vault, make_llm(), topics=[], only_below=20) == 2
    assert "--only-below" in capsys.readouterr().out
    assert _go(vault, make_llm(), only_below=0) == 2
    assert "--only-below" in capsys.readouterr().out


def test_dry_run_counts_only_the_calls_that_would_be_made(vault, make_llm, capsys):
    _guide(vault)
    assert _go(vault, make_llm(), baseline="topic", only_below=20, dry_run=True) == 0
    out = capsys.readouterr().out
    assert "1 calls (1 topics)" in out and "1 topic(s) kept unchanged" in out


def test_unchanged_topic_keeps_its_passages_in_the_source_map(vault, make_llm):
    _guide(vault)
    extras = [ExtraSource("Wald", "notes-1", "notes", "academic_notes/econ/class_2024/notes.md", "Notes p. 3",
                          "ta_notes", "class_2024")]
    llm = make_llm(make_topic_json("LM", labels=("S1",)))
    assert _go(vault, llm, baseline="topic", only_below=20, extra_sources=extras) == 0
    smap = _front(vault, "source_map")
    assert {"Wald (unchanged draft section)"} <= {u for e in smap if e["chunk_id"] == "notes-1" for u in e["used_in"]}


def test_a_topic_with_no_baseline_section_is_written_fresh(vault, make_llm, capsys):
    _guide(vault)
    llm = make_llm(make_topic_json("Wald", labels=("S1",)), make_topic_json("Brand new", labels=("S1",)))
    assert _go(vault, llm, topics=["Wald", "Brand new"], baseline="topic") == 0
    assert "WALD-LONG" in llm.calls[0] and "no existing section" in llm.calls[1]
    assert "Brand new" in capsys.readouterr().out.split("NOTE", 1)[1]


def test_notes_and_comparisons_are_carried_around_the_topics(vault, make_llm):
    _guide(vault)
    llm = make_llm(make_topic_json("Wald", labels=("S1",)))
    assert _go(vault, llm, topics=["Wald"], baseline="topic", carry_before=["Source note"], carry_after=["Compare"]) == 0
    body = _out(vault).read_text(encoding="utf-8").split("\n---\n\n", 1)[1]
    assert body.index("NOTE-TEXT") < body.index("## Wald") < body.index("COMPARE-TEXT")
    assert _front(vault, "carried_sections") == ["Source note", "Compare"] and _front(vault, "topics") == ["Wald"]


def test_a_carried_section_missing_from_the_guide_is_an_error(vault, make_llm, capsys):
    _guide(vault)
    llm = make_llm()
    assert _go(vault, llm, topics=["Wald"], carry_after=["No such section"]) == 2
    assert "No such section" in capsys.readouterr().out and llm.calls == []


def test_token_usage_is_recorded_and_printed_when_the_client_tracks_it(vault, make_llm, capsys):
    llm = make_llm(make_topic_json("Wald", labels=("S1",)))
    llm.usage = {"calls": 1, "prompt_tokens": 5000, "output_tokens": 900, "thinking_tokens": 10}
    assert _go(vault, llm, topics=["Wald"]) == 0
    assert _front(vault, "usage") == llm.usage
    assert "1 calls, 5000 prompt tokens, 900 output tokens, 10 thinking tokens" in capsys.readouterr().out


def test_no_usage_key_when_the_client_does_not_track_it(vault, make_llm):
    assert _go(vault, make_llm(make_topic_json("Wald", labels=("S1",))), topics=["Wald"]) == 0
    assert _front(vault, "usage") is None


def test_only_topics_enhances_just_those_sections_and_keeps_the_rest(vault, make_llm):
    _guide(vault)
    llm = make_llm(make_topic_json("LM", labels=("S1",)))
    assert _go(vault, llm, baseline="topic", only_topics=["LM"]) == 0
    assert len(llm.calls) == 1 and "LM-SHORT" in llm.calls[0]
    assert f"## Wald\n\n{LONG} WALD-LONG" in _out(vault).read_text(encoding="utf-8")
    assert _front(vault, "unchanged_topics") == ["Wald"]


def test_only_topics_rejects_a_name_that_is_not_a_topic(vault, make_llm, capsys):
    _guide(vault)
    assert _go(vault, make_llm(), only_topics=["Nope"]) == 2
    assert "Nope" in capsys.readouterr().out
