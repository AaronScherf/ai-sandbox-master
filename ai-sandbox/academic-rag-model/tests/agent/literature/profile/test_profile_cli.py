import json
import re
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from agent.literature.profile import cli, summary
from agent.literature.profile.taxonomy import load_openalex
from agent.literature.vocab import load_vocabularies
from core.agent_tasks import loop
from core.indexer.index_card import find_card_by_file_id, save_shard
from core.indexer.research_profile import set_research_profile

TAX = load_openalex()
ECON = next(label for label in TAX.fields.values() if label.startswith("Economics"))
QUOTES = {"f1": "households received monthly cash transfers", "f2": "farmers adopted drought tolerant seed",
          "f3": "the model simulates a carbon tax"}


def _paper(root: Path, fid: str, title: str, doi: str | None):
    md = root / "journal-articles" / "economics" / "processed_outputs" / f"{fid}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    pages = {1: f"{title}. Abstract.", 2: f"In the study, {QUOTES[fid]} for two years.", 3: "Conclusion."}
    md.write_text("".join(f"\n<!-- page {n} -->\n\n{t}\n" for n, t in pages.items()), encoding="utf-8")
    card = {"file_id": fid, "course": "economics", "title": title, "doc_type": "journal_article",
            "path": f"journal-articles/economics/processed_outputs/{fid}.md", "publication_year": 2019}
    if doi:
        card["doi"] = doi
    return card


def _vocab_file(base: Path, kind: str):
    path = base / "resources" / "3ie" / "vocab" / f"{kind}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"vocabulary": kind, "version": 1, "provenance": "provisional", "source": "test",
                                    "terms": [{"id": f"{kind}.sector", "label": f"{kind} sector", "definition": "d"},
                                              {"id": f"{kind}.branch", "label": f"{kind} branch", "definition": "d",
                                               "parent": f"{kind}.sector"}]}), encoding="utf-8")


@pytest.fixture
def root():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        subprocess.run(["git", "init", "-q", str(base)], check=True)  # the corpus write lock needs a repo
        cards = [_paper(base, "f1", "Cash transfers in Kenya", "10.1/one"),
                 _paper(base, "f2", "Seed adoption in Mali", "10.1/two"),
                 _paper(base, "f3", "A carbon tax model", None)]
        for kind in ("intervention", "outcome"):
            _vocab_file(base, kind)
        save_shard(str(base), "economics", cards)
        save_shard(str(base), "econometrics", [{"file_id": "c1", "course": "econometrics", "title": "Lecture 1",
                                                "doc_type": "lecture", "path": "c1.md"}])
        yield base


def _lookup(doi):
    return {"title": "Cash transfers in Kenya", "authors": ["Ann Smith"], "year": 2019, "journal": "J Dev",
            "doi": doi} if doi == "10.1/one" else None


def _run(root, *argv, **kw):
    return cli.main(["--index-root", str(root), *argv], **kw)


def test_writing_commands_refuse_while_another_writer_holds_the_corpus_lock(root, capsys):
    from core.env.corpus_write_lock import corpus_write_lock
    with corpus_write_lock([root], "other writer"):
        assert _run(root, "refresh-discipline") == 2
        assert "other writer" in capsys.readouterr().out
        assert _run(root, "summary") == 0  # read-only commands never take the lock
        assert _run(root, "folders", "plan") == 0


def _latest_run(root):
    return sorted(p.name for p in (root / ".agent_work").iterdir())[-1]


def _fill(root, answer):
    """Plays the agent: writes answer(task_entry) as the YAML result on every pending card of the latest run."""
    run_id = _latest_run(root)
    manifest = json.loads((root / ".agent_work" / run_id / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["tasks"]:
        path = root / ".agent_work" / run_id / "cards" / f"{entry['id']}.md"
        card = path.read_text(encoding="utf-8")
        path.write_text(card.replace("```yaml\n```", "```yaml\n" + yaml.safe_dump(answer(entry)) + "```"),
                        encoding="utf-8")
    return run_id


def _classify_answer(entry):
    base = {"discipline": ECON, "discipline_confidence": 0.9}
    if entry["subject"]["variant"] == "b":
        return base
    return {**base, "report_type": "journal_article", "subtype": "empirical_study", "publisher_type": "academic", "country": ["Kenya"],
            "method_class": "quantitative", "study_design": "randomized_controlled_trial",
            "orientation": "retrospective", "evidence_role": "primary_evaluation", "intervention_start_year": 2015}


def _tag_answer(entry):
    fid = entry["subject"]["file_id"]
    return {"tags": [{"term_id": entry["subject"]["offered"][0], "quote": QUOTES[fid], "locator": 2}]}


def _pipeline(root):
    assert _run(root, "metadata", lookup=_lookup) == 0
    for variant in ("a", "b"):
        assert _run(root, "classify", "collect", "--variant", variant) == 0
        run_id = _fill(root, _classify_answer)
        assert _run(root, "classify", "submit", run_id) == 0
    for kind in ("intervention", "outcome"):
        assert _run(root, "tag", "collect", "--kind", kind, "--level", "1") == 0
        run_id = _fill(root, _tag_answer)
        assert _run(root, "tag", "submit", run_id) == 0


def _bytes(root):
    return {p.name: p.read_bytes() for p in (root / ".index").glob("*.json")}


def test_full_pipeline_end_to_end_on_three_fake_papers(root, capsys):
    _pipeline(root)
    for fid in ("f1", "f2", "f3"):
        profile = find_card_by_file_id(str(root), fid)[1]["research_profile"]
        assert profile["report_type"] == "journal_article" and profile["discipline"] == ECON
        assert profile["applicability"] == "both" and profile["country_income_group"]
        assert {"classify_a", "classify_b", "tag_intervention_L1", "tag_outcome_L1"} <= set(profile["provenance"])
    assert find_card_by_file_id(str(root), "f1")[1]["research_profile"]["doi_verified"]["match"] == "match"
    capsys.readouterr()
    assert _run(root, "summary") == 0
    assert "documents with a research profile: 3" in capsys.readouterr().out
    assert _run(root, "queue") == 0
    assert _run(root, "folders", "plan") == 0


def test_rerun_with_same_prompt_version_is_idempotent(root, capsys):
    _pipeline(root)
    before = _bytes(root)
    capsys.readouterr()
    assert _run(root, "metadata", lookup=_lookup) == 0
    assert _run(root, "classify", "collect", "--variant", "a") == 0
    assert _run(root, "tag", "collect", "--kind", "intervention", "--level", "1") == 0
    assert "nothing to do" in capsys.readouterr().out
    assert _bytes(root) == before


def test_course_shards_untouched(root):
    before = _bytes(root)["econometrics.json"]
    _pipeline(root)
    assert _bytes(root)["econometrics.json"] == before


def test_file_id_filter_leaves_other_cards_untouched(root):
    assert _run(root, "classify", "collect", "--variant", "a", "--file-id", "f1") == 0
    run_id = _fill(root, _classify_answer)
    assert _run(root, "classify", "submit", run_id) == 0
    assert find_card_by_file_id(str(root), "f1")[1].get("research_profile")
    assert not find_card_by_file_id(str(root), "f2")[1].get("research_profile")


def test_summary_command_matches_direct_counts(root, capsys):
    _pipeline(root)
    capsys.readouterr()
    assert _run(root, "summary", "--json") == 0
    out = json.loads(capsys.readouterr().out)
    cards = find_cards(root)
    vocabs = {k: v for k, v in load_vocabularies(root / "resources" / "3ie" / "vocab").items() if k in ("intervention", "outcome")}
    assert out == json.loads(json.dumps(summary.summarize(cards, None, vocabs)))


def find_cards(root):
    return [c for name in ("economics",) for c in json.loads((root / ".index" / f"{name}.json").read_text(encoding="utf-8"))]


def test_api_mode_without_approval_refuses_and_prints_estimate(root, capsys, monkeypatch):
    assert _run(root, "classify", "collect", "--variant", "a") == 0
    run_id = _latest_run(root)
    monkeypatch.setattr(loop, "FREE_LIMIT", 0.0)
    calls = []
    capsys.readouterr()
    code = _run(root, "classify", "api", run_id, "--model", "m", complete=lambda prompt: calls.append(prompt) or "")
    out = capsys.readouterr().out
    assert code == 2 and not calls
    assert re.search(r"estimated cost \$\d", out) and "--approve-cost" in out
    assert not find_card_by_file_id(str(root), "f1")[1].get("research_profile")


def test_api_mode_applies_answers_when_cost_is_approved(root):
    assert _run(root, "classify", "collect", "--variant", "a", "--file-id", "f1") == 0
    run_id = _latest_run(root)
    reply = "```yaml\n" + yaml.safe_dump(_classify_answer({"subject": {"variant": "a"}})) + "```"
    assert _run(root, "classify", "api", run_id, "--approve-cost", "5", complete=lambda prompt: reply) == 0
    assert find_card_by_file_id(str(root), "f1")[1]["research_profile"]["report_type"] == "journal_article"


def test_openalex_source_stores_work_id_and_topics_on_the_profile(root):
    def lookup(doi):
        return {**_lookup(doi), "openalex_id": "W9", "topics": [{"id": "T1", "score": 0.9}]} if doi == "10.1/one" else None
    assert _run(root, "metadata", "--source", "openalex", lookup=lookup) == 0
    profile = find_card_by_file_id(str(root), "f1")[1]["research_profile"]
    assert profile["openalex_id"] == "W9" and profile["openalex_topics"] == [{"id": "T1", "score": 0.9}]
    assert profile["doi_verified"]["source"] == "openalex"


def test_refresh_discipline_recomputes_secondary_and_fit_without_a_new_run(root, capsys):
    _pipeline(root)
    set_research_profile(str(root), "f1", {"secondary_discipline": None, "discipline_fit": None, "discipline_scores": None})
    assert _run(root, "refresh-discipline") == 0
    profile = find_card_by_file_id(str(root), "f1")[1]["research_profile"]
    assert profile["discipline_fit"] in ("clear", "mixed") and profile["discipline_scores"]
    assert "refreshed 3" in capsys.readouterr().out


def test_project_command_tags_a_folder_and_adds_without_duplicating(root, capsys):
    from agent.literature.profile import review
    cards = review.all_cards(str(root))
    folder, fid = cards[0]["course"], cards[0]["file_id"]
    for _ in range(2):
        assert cli.main(["--index-root", str(root), "project", folder, "nexus-novelty-check"]) == 0
    assert cli.main(["--index-root", str(root), "project", folder, "transferability"]) == 0
    projects = find_card_by_file_id(str(root), fid)[1]["research_profile"]["projects"]
    assert projects == ["nexus-novelty-check", "transferability"]
    assert cli.main(["--index-root", str(root), "project", "no-such-folder", "x"]) == 2


def test_folders_apply_with_file_id_still_counts_every_paper(root):
    _pipeline(root)
    for fid in ("f1", "f2", "f3"):  # the three share a discipline, so each reaches the 3-paper minimum
        (root / "journal-articles" / "economics" / f"{fid}.pdf").write_text(fid, encoding="utf-8")
        card = find_card_by_file_id(str(root), fid)[1]
        card["source_pdf_path"] = f"journal-articles/economics/{fid}.pdf"
        save_shard(str(root), "economics", [card if c["file_id"] == fid else c for c in
                                            __import__("core.indexer.index_card", fromlist=["x"]).load_shard(str(root), "economics")])
    assert _run(root, "folders", "apply", "--all", "--file-id", "f1") == 0
    path = find_card_by_file_id(str(root), "f1")[1]["path"]
    assert "/other/" not in path and "economics-econometrics-and-finance" in path


def test_label_page_writes_a_prediction_free_page_and_its_terms(root, tmp_path):
    set_research_profile(str(root), "f1", {"report_type": "thesis", "subtype": "SECRETSUBTYPE"})
    assert _run(root, "label-page", "--file-id", "f1", "--out", str(tmp_path)) == 0
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Cash transfers in Kenya" in page and "households received" in page
    assert "SECRETSUBTYPE" not in page and "Seed adoption in Mali" not in page
    terms = json.loads((tmp_path / "terms.json").read_text(encoding="utf-8"))
    assert [t["id"] for t in terms["intervention"]] == ["intervention.sector", "intervention.branch"]
    assert terms["intervention"][1] == {"id": "intervention.branch", "label": "intervention branch",
                                        "path": "intervention sector", "definition": "d"}


def test_eval_scores_saved_page_labels(root, tmp_path, capsys):
    set_research_profile(str(root), "f1", {"report_type": "report", "applicability": "intervention_only",
                                          "intervention_tags": [{"term_id": "intervention.branch"}]})
    labels = tmp_path / "labels.json"
    labels.write_text(json.dumps({"f1": {"report_type": "report", "applicability": "both",
                                         "main_intervention": ["intervention.sector"], "main_outcome": []}}),
                      encoding="utf-8")
    assert _run(root, "eval", "--labels", str(labels)) == 0
    out = capsys.readouterr().out
    scores = json.loads(out[:out.rindex("}") + 1])["report"]
    assert scores["report_type_agreement"] == 1.0 and scores["applicability_agreement"] == 0.0
    assert scores["tag_recall"] == 1.0

