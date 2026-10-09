# tests/agent/study_guide/test_study_guide_revise_cost.py
import pytest

from agent.study_guide.revise.checkpoint import Checkpoint
from agent.study_guide.revise.cost import CostCapReached, cost_usd, estimate_cost
from rv_helpers import ScriptedLLM
from sg_helpers import make_spec, root  # noqa: F401 (fixtures)
from test_study_guide_revise_run import env  # noqa: F401 (fixture)

U = {"prompt_tokens": 1_000_000, "cached_tokens": 400_000, "output_tokens": 100_000, "thinking_tokens": 200_000}


def test_cost_bills_cached_prompt_at_the_cache_rate_and_thinking_as_output():
    # 0.6M fresh * 0.75 + 0.4M cached * 0.075 + 0.3M output+thinking * 3.75
    assert cost_usd(U, "gemini-3.8-flash") == pytest.approx(0.45 + 0.03 + 1.125)


def test_an_unknown_model_is_priced_like_the_default_so_the_cap_still_protects():
    assert cost_usd(U, "some-new-model") == cost_usd(U, "gemini-3.8-flash")


def test_estimate_uses_the_per_call_average_of_a_prior_run_and_falls_back_to_defaults():
    prior = {"correctness": {"calls": 2, "prompt_tokens": 20_000, "output_tokens": 2_000, "thinking_tokens": 20_000, "cached_tokens": 0}}
    with_prior = estimate_cost({"correctness": 4}, "gemini-3.8-flash", prior)
    assert with_prior == pytest.approx(2 * cost_usd(prior["correctness"], "gemini-3.8-flash"))
    assert estimate_cost({"correctness": 4}, "gemini-3.8-flash", None) > 0
    assert estimate_cost({}, "gemini-3.8-flash", None) == 0


def test_a_unit_that_pushes_spend_over_the_cap_stops_the_run_and_keeps_its_work(env, tmp_path):  # noqa: F811
    _, spec, guide = env
    from agent.study_guide import cli
    from agent.study_guide.cli import plan_path_for
    from agent.study_guide.revise.run import build_report
    from rv_helpers import bag_embed
    from test_study_guide_revise_run import CHUNKS, EVIDENCE, VOCAB
    plan = cli.load_plan(plan_path_for(str(guide.parents[3]), spec))
    cp = Checkpoint(tmp_path / "p.json", "k")
    kw = dict(stages=("relevance", "organization"), embed=bag_embed(VOCAB), evidence=EVIDENCE, chunks=CHUNKS, checkpoint=cp)
    with pytest.raises(CostCapReached, match="organization"):
        build_report(spec, str(guide), plan, llm=ScriptedLLM([{"edits": []}]), max_cost=1e-9, **kw)
    again = ScriptedLLM([])
    report = build_report(spec, str(guide), plan, llm=again, max_cost=1.0, **kw)
    assert again.calls == [] and report.usage["organization"]["calls"] == 1


def test_a_rerun_audits_only_the_sections_whose_text_or_sources_changed(make_spec, root, tmp_path):  # noqa: F811
    from pathlib import Path
    from agent.study_guide import cli
    from agent.study_guide.cli import cmd_plan, plan_path_for
    from agent.study_guide.revise.run import build_report
    from agent.study_guide.spec import load_spec
    from rv_helpers import bag_embed
    from sg_helpers import CARDS, CHUNKS, StubSearch, hit
    from test_study_guide_revise_run import EVIDENCE, GUIDE, HEADER, SPEC, VOCAB
    make_spec(SPEC.replace('["relevance", "organization"]', '["correctness"]'), header=HEADER)
    spec_file = tmp_path / "spec.toml"
    assert cmd_plan(str(spec_file), root, search=StubSearch({"textbook": [hit("cam-1", .9)]}), chunks=CHUNKS, cards=CARDS) == 0
    spec = load_spec(spec_file)
    guide = Path(root) / "academic_notes" / "econ" / "summaries" / "demo.md"
    guide.write_text(GUIDE, encoding="utf-8")
    plan = cli.load_plan(plan_path_for(root, spec))
    cache = Checkpoint(tmp_path / "audit-cache.json", "audit-cache-v1")
    kw = dict(stages=("correctness",), embed=bag_embed(VOCAB), evidence=EVIDENCE, chunks=CHUNKS, audit_cache=cache)
    first = ScriptedLLM([{"findings": []}])
    build_report(spec, str(guide), plan, llm=first, **kw)
    assert len(first.calls) == 1
    guide.write_text(GUIDE + "\n## Extra\n\nnew words here\n", encoding="utf-8")  # a different guide, same Wald section
    second = ScriptedLLM([])
    report = build_report(spec, str(guide), plan, llm=second, **kw)
    assert second.calls == [] and report.usage["correctness:Wald"]["calls"] == 0
    guide.write_text(GUIDE.replace("wald statistic words", "wald statistic changed", 1), encoding="utf-8")
    third = ScriptedLLM([{"findings": []}])
    build_report(spec, str(guide), plan, llm=third, **kw)
    assert len(third.calls) == 1
