# tests/agent/study_guide/test_study_guide_revise_audit.py
from agent.study_guide.revise.audit import (
    audit_section, build_arith_prompt, build_audit_prompt, needs_arithmetic_check, parse_arith, parse_audit,
)
from agent.study_guide.revise.segment import segment
from rv_helpers import ScriptedLLM

BODY = ("# T\n\n## Wald\n\nThe statistic has 3 degrees of freedom and equals 9.17 here.\n\n"
        "### Worked\n\n**Constructed example (not from the sources)** n=100, W = 4/0.436 = 9.17.\n")
PASSAGES = [("S1", "Hansen §9.10, p. 268", "The Wald statistic is chi-square with q degrees of freedom.")]


def _blocks():
    blocks = segment(BODY)
    return blocks, {b.id: b for b in blocks}


def test_prompt_contains_blocks_and_labelled_passages():
    blocks, _ = _blocks()
    prompt = build_audit_prompt("The Wald test", blocks[1:], PASSAGES)
    assert blocks[1].id in prompt and "[S1] Hansen §9.10, p. 268" in prompt and "The Wald test" in prompt


def test_a_contradiction_becomes_a_fix_with_its_source():
    blocks, by_id = _blocks()
    data = {"findings": [{"block": blocks[1].id, "quote": "3 degrees of freedom", "verdict": "contradicted",
                          "explanation": "q, not 3", "source_label": "S1", "replacement": "q degrees of freedom"}]}
    edits, problems = parse_audit(data, by_id, {"S1"}, start=1)
    assert problems == [] and len(edits) == 1
    e = edits[0]
    assert (e.type, e.quote, e.replacement, e.evidence, e.stage, e.id) == (
        "fix", "3 degrees of freedom", "q degrees of freedom", ["S1"], "correctness", "cor-001")


def test_a_finding_without_a_replacement_is_an_advisory_note():
    blocks, by_id = _blocks()
    data = {"findings": [{"block": blocks[1].id, "quote": "equals 9.17", "verdict": "unsupported", "explanation": "no source"}]}
    edits, _ = parse_audit(data, by_id, {"S1"}, start=1)
    assert [e.type for e in edits] == ["note"]


def test_missing_or_ambiguous_quotes_and_unknown_labels_are_reported_not_applied():
    blocks, by_id = _blocks()
    data = {"findings": [
        {"block": blocks[1].id, "quote": "not in the block", "verdict": "unsupported", "explanation": "x"},
        {"block": blocks[1].id, "quote": "the", "verdict": "unsupported", "explanation": "x"},
        {"block": "nope", "quote": "x", "verdict": "unsupported", "explanation": "x"},
        {"block": blocks[1].id, "quote": "3 degrees", "verdict": "contradicted", "explanation": "x",
         "source_label": "S9", "replacement": "q degrees"},
    ]}
    edits, problems = parse_audit(data, by_id, {"S1"}, start=1)
    assert edits == [] and len(problems) == 4


def test_arithmetic_check_applies_to_constructed_and_worked_blocks():
    blocks, _ = _blocks()
    assert needs_arithmetic_check(blocks[2]) and not needs_arithmetic_check(blocks[1])
    assert "Python" in build_arith_prompt(blocks[2])


def test_a_worked_block_with_no_computed_result_needs_no_recheck():
    marker = "**Constructed example (not from the sources)** "
    body = ("# T\n\n## Wald\n\n### Worked A\n\n" + marker + "n=100 with q = 3 restrictions and critical value 3.84.\n\n"
            "### Worked B\n\n" + marker + "W = 4/0.436 = 9.17.\n\n"
            "### Worked C\n\n" + marker + "\\frac{4}{0.436} \\approx 9.17.\n")
    blocks = [b for b in segment(body) if b.constructed]
    assert [needs_arithmetic_check(b) for b in blocks] == [False, True, True]


def test_parse_arith_turns_failures_into_notes():
    blocks, _ = _blocks()
    text = 'Here is the result:\n[{"quote": "4/0.436 = 9.17", "computed": "9.174", "ok": true}, ' \
           '{"quote": "W = 4/0.436", "computed": "10.5", "ok": false}]'
    edits = parse_arith(text, blocks[2], start=1)
    assert [(e.type, e.stage, e.targets) for e in edits] == [("note", "correctness", [blocks[2].id])]
    assert "10.5" in edits[0].rationale
    assert parse_arith("no json here", blocks[2], start=1) == []


def test_audit_section_makes_a_structured_call_and_a_code_call_for_worked_blocks():
    blocks, _ = _blocks()
    llm = ScriptedLLM([{"findings": []}, '[{"quote": "x", "computed": "1", "ok": true}]'])
    edits, problems = audit_section(llm, "The Wald test", blocks[1:], PASSAGES)
    assert llm.kinds == ["structured", "code"] and edits == [] and problems == []
