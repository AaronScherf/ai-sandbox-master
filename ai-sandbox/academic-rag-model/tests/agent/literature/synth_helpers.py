"""Fixture builder for the stage 3 tests: several papers, each extracted twice with a given result."""
import copy
from pathlib import Path

from agent.literature import stage
from agent.literature.papers import eligible_papers
from agent.literature.proposals import Proposals
from agent.literature.store import RecordStore
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS, good, make_index

PROV = {"driver": "agent", "agent": "antigravity", "run": "r1"}
F1, F2, F3 = "a" * 16, "b" * 16, "c" * 16


def with_sector(result):
    out = copy.deepcopy(result)
    out["core"]["sector"] = [{"value": "social protection", "vocab_id": "sector.social_protection",
                              "quote": "We study cash transfers in rural Somalia", "locator": 1}]
    return out


def build(root, results: dict):
    for fid in results:
        make_index(root, fid, title=f"Paper {fid}", card_extra={"publication_year": 2019})
    records = RecordStore(Path(root) / ".index" / "study_records")
    target = stage.Target(str(root), records, VOCABS, Proposals(records.dir))
    papers, _ = eligible_papers(str(root))
    for label in ("a", "b"):
        tasks, _ = stage.make_tasks(target, papers, pass_label=label, redo=True)
        for t in tasks:
            stage.apply_result(target, task_entry(t), results[t.subject["file_id"]], PROV)
    return target, papers


def three_papers():
    """F1 and F3 are social protection papers on cash transfers; F2 is a voucher paper with no sector."""
    voucher = copy.deepcopy(good())
    voucher["core"]["intervention"][0].update(vocab_id="intervention.voucher", value="vouchers")
    return {F1: with_sector(good()), F2: voucher, F3: with_sector(good())}
