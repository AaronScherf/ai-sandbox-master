import shutil
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[3] / "agent" / "concept_graph" / "sample_data"


def copy_sample(dest: Path) -> Path:
    """Copy the sample graph into dest/graph and return that directory."""
    target = Path(dest) / "graph"
    shutil.copytree(SAMPLE, target, ignore=shutil.ignore_patterns("index.html", "build"))
    return target


from agent.concept_graph.sources import Passage  # noqa: E402
from agent.concept_graph.work import task_entry  # noqa: E402

PASSAGE_TEXT = "A preorder is a binary relation that is reflexive and transitive and nothing more, so ties are allowed."


class FakeRetriever:
    """Returns fixed passages (and records the queries it was asked)."""

    def __init__(self, passages=None):
        self.queries = []
        self.passages = passages if passages is not None else [
            Passage(id="", source="rubinstein", ref="ch. 2, p. 12", text=PASSAGE_TEXT, path="r.md"),
            Passage(id="", source="mwg", ref="ch. 1", text="Choice behaviour can be consistent without preferences.", path="m.md"),
        ]

    def retrieve(self, query, top_k):
        self.queries.append(query)
        return list(self.passages[:top_k])


def blank_explanations(store, ids):
    for i in ids:
        store.update_item("node", i, {"explanation": ""})


def entry_for(task):
    return task_entry(task)
