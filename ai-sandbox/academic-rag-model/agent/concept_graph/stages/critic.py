"""Stage critic: a blind second look at each proposed edge. The checker sees the claim and fresh passages only,
never the drafter's explanation or citations, so it cannot simply agree with them."""
from __future__ import annotations

from ..ipguard import check_prose
from ..store import GraphStore
from ..tasks import Task
from .common import edge_sentence, passage_texts, with_ids

STAGE = "critic"
VERDICTS = ("supports", "weak", "unsupported")
ALLOWED = {"verdict", "note"}

INSTRUCTIONS = """\
Check whether the offered passages support this claim about how two concepts relate. You have NOT been shown how the
claim was justified; judge it only from the passages and your own knowledge of the subject.

Verdicts:
  supports     the passages (or standard theory they reflect) state this, including the stated condition
  weak         plausible, but the passages do not state it, or the condition looks incomplete or too strong/weak
  unsupported  the passages contradict it, or it is false as stated (say why in the note)

Rules: write the `note` in your own words (8 or more consecutive words shared with a passage is rejected). A note
is required for weak and unsupported. Be strict about conditions: a true implication under the wrong assumptions
is a wrong claim.

Result: one YAML mapping:
  verdict: supports | weak | unsupported
  note: <short reason; required unless supports>
"""


def make_tasks(store: GraphStore, retriever, *, section: str | None = None, nodes: list[str] | None = None,
               redo: bool = False, top_k: int = 6, **_ignored) -> list[Task]:
    graph = store.read_all()
    by_id = {n.id: n for n in graph.nodes}
    names = {n.id: n.name for n in graph.nodes}
    tasks = []
    for e in graph.edges:
        if e.status == "verified" or (e.critic is not None and not redo):
            continue
        ends = [by_id.get(e.source), by_id.get(e.target)]
        if any(n is None for n in ends):
            continue
        if nodes is not None and not ({e.source, e.target} & set(nodes)):
            continue
        if section and section not in {n.section for n in ends}:
            continue
        s, t = ends
        claim = edge_sentence(e, names)
        context = "\n".join([
            f"Claim to check: {claim}", "",
            f"{s.name} (id: {s.id}): {s.gist or '(no summary)'}",
            f"{t.name} (id: {t.id}): {t.gist or '(no summary)'}",
        ])
        query = f"{s.name} {t.name} {e.condition or ''}".strip()
        tasks.append(Task(id=f"critic-{e.id}", stage=STAGE, subject={"edge": e.id}, instructions=INSTRUCTIONS,
                          context=context, passages=with_ids(retriever.retrieve(query, top_k))))
    return tasks


def validate_result(entry: dict, result: dict, store: GraphStore) -> list[str]:
    problems = []
    unknown = sorted(set(result) - ALLOWED)
    if unknown:
        problems.append(f"unknown key(s) {unknown}; allowed: {sorted(ALLOWED)}")
    verdict, note = result.get("verdict"), result.get("note")
    if verdict not in VERDICTS:
        problems.append(f"verdict: must be one of {', '.join(VERDICTS)}")
    if verdict in ("weak", "unsupported") and not (isinstance(note, str) and note.strip()):
        problems.append(f"note: required when the verdict is {verdict}")
    if note is not None and not isinstance(note, str):
        problems.append("note: must be text")
    elif isinstance(note, str):
        problems += check_prose({"note": note}, passage_texts(entry))
    return problems


def apply_result(store: GraphStore, entry: dict, result: dict, provenance: dict) -> str | None:
    edge_id = entry["subject"]["edge"]
    edge = next((e for e in store.read_all().edges if e.id == edge_id), None)
    if edge is None:
        return f"edge {edge_id!r} no longer exists"
    if edge.status == "verified":
        return f"edge {edge_id!r} is verified now; left unchanged"
    store.update_item("edge", edge_id, {"critic": {"verdict": result["verdict"], "note": (result.get("note") or "").strip()}})
    return None
