# tests/agent/study_guide/test_study_guide_revise_inline.py
"""The inline sweep: out-of-scope sentences inside blocks that are otherwise on topic."""
import pytest

from agent.study_guide.revise.edits import ReviseError
from agent.study_guide.revise.inline import (
    BATCH, build_inline_prompt, inline_candidates, inline_edits, parse_inline, terms_in,
)
from agent.study_guide.revise.segment import segment
from agent.study_guide.spec import SpecError, load_spec
from rv_helpers import ScriptedLLM

BODY = ("# T\n\n## Wald\n\nThe cutoff is 3.84. In MATLAB, c is computed as chi2inv(1-alpha, q). The test then rejects.\n\n"
        "## Score\n\nNothing out of scope here at all.\n\n## Notes\n\nSee Stata or AIC for more. Also the MATLABS thing.\n")
TERMS = ("MATLAB", "Stata", "AIC")


def test_terms_match_whole_words_case_insensitively():
    assert terms_in("In matlab and Stata", TERMS) == ["MATLAB", "Stata"]
    assert terms_in("the MATLABS thing", TERMS) == [] and terms_in("nothing", TERMS) == []


def test_candidates_are_blocks_with_a_term():
    blocks = segment(BODY)
    got = inline_candidates(blocks, TERMS)
    assert [b.heading_path[-1] for b in got] == ["Wald", "Notes"]


def test_prompt_has_the_scope_the_terms_and_the_block_ids():
    blocks = segment(BODY)
    prompt = build_inline_prompt("Only the tests.", [blocks[1]], TERMS)
    assert "Only the tests." in prompt and blocks[1].id in prompt and "MATLAB" in prompt


def test_a_valid_finding_becomes_a_shrinking_fix():
    blocks = segment(BODY)
    by = {b.id: b for b in blocks}
    quote = " In MATLAB, c is computed as chi2inv(1-alpha, q)."
    data = {"findings": [{"block": blocks[1].id, "quote": quote, "replacement": "", "rationale": "software syntax"}]}
    edits, problems = parse_inline(data, by, start=1)
    assert problems == [] and [(e.type, e.quote, e.replacement, e.stage, e.id) for e in edits] == [
        ("fix", quote, "", "inline", "inl-001")]


def test_bad_findings_are_reported_not_applied():
    blocks = segment(BODY)
    by = {b.id: b for b in blocks}
    wald = blocks[1].id
    data = {"findings": [
        {"block": "nope", "quote": "x", "replacement": "", "rationale": "r"},
        {"block": wald, "quote": "absent text", "replacement": "", "rationale": "r"},
        {"block": wald, "quote": "The test then rejects.", "replacement": "The test then rejects the null hypothesis today.", "rationale": "longer"},
    ]}
    edits, problems = parse_inline(data, by, start=1)
    assert edits == [] and len(problems) == 3


def test_inline_edits_batches_and_survives_a_malformed_reply(capsys):
    blocks = segment(BODY)
    llm = ScriptedLLM([{"findings": [{"block": "zzz", "quote": "q", "replacement": "", "rationale": "r"}]}])
    edits, problems = inline_edits(llm, "scope", blocks, TERMS)
    assert BATCH >= 2 and len(llm.calls) == 1 and edits == [] and problems


def test_spec_reads_scope_terms_and_allows_the_inline_criterion(tmp_path):
    base = ('[guide]\nid = "g"\ntitle = "T"\ncourse = "econ"\n\n[[topic]]\ntitle = "A"\ninstruction = "i"\n\n'
            '  [[topic.source]]\n  kind = "file"\n  file = "x"\n\n[revise]\n')
    p = tmp_path / "s.toml"
    p.write_text(base + 'scope_terms = ["Stata", "AIC"]\ncriteria = ["inline"]\n', encoding="utf-8")
    r = load_spec(p).revise
    assert r.scope_terms == ("Stata", "AIC") and r.criteria == ("inline",)
    p.write_text(base, encoding="utf-8")
    r = load_spec(p).revise
    assert r.scope_terms == () and r.criteria == ("relevance", "dedup", "correctness", "organization")
    p.write_text(base + 'criteria = ["sparkle"]\n', encoding="utf-8")
    with pytest.raises(SpecError, match="criteria"):
        load_spec(p)
