"""After a proposal is accepted or merged, point the facts that proposed it at the vocabulary term."""
from __future__ import annotations

from . import schema
from .compare import reconcile
from .proposals import Proposals
from .store import RecordStore
from .transcript import normalize


def _facet_lists(record: dict):
    for facet, vocab_name in schema.FACETS.items():
        if record["core"].get(facet) is not None:
            yield facet, vocab_name, record["core"]
    for module, facets in schema.MODULE_FACETS.items():
        box = (record.get("modules") or {}).get(module) or {}
        for facet, vocab_name in facets.items():
            if box.get(facet) is not None:
                yield facet, vocab_name, box


def _remap_pass(record: dict, label: str, file_id: str, resolutions: dict, vocabs: dict, renamed: dict) -> int:
    changed = 0
    for facet, vocab_name, box in _facet_lists(record):
        vocab = vocabs.get(vocab_name)
        kept, seen = [], set()
        for fact in box[facet]:
            if fact.get("proposed"):
                term = resolutions.get((file_id, vocab_name, normalize(fact.get("value", ""))))
                if term and vocab is not None and term in vocab.terms:
                    renamed[(facet, "proposed:" + normalize(fact["value"]), label)] = term
                    fact = {k: v for k, v in fact.items() if k != "proposed"} | {"vocab_id": term}
                    changed += 1
            if fact.get("vocab_id") and fact["vocab_id"] in seen:
                continue  # two wordings now name one term
            seen.add(fact.get("vocab_id"))
            kept.append(fact)
        box[facet] = kept
    return changed


def remap_record(records: RecordStore, proposals: Proposals, vocabs: dict, file_id: str) -> int:
    """Facts changed across both passes; the pair is compared again afterwards. The checker's verdicts live in
    pass a's record but name facts of either pass, so they follow the rename too."""
    resolutions = proposals.resolutions()
    loaded = {label: records.read(file_id, label) for label in ("a", "b")}
    renamed: dict = {}
    total, touched = 0, set()
    for label, record in loaded.items():
        if record is not None and (n := _remap_pass(record, label, file_id, resolutions, vocabs, renamed)):
            total += n
            touched.add(label)
    if not total:
        return 0
    a = loaded["a"]
    for block in ("verification", "verification_full"):
        for item in ((a or {}).get(block) or {}).get("items", []):
            item["shown"] = renamed.get((item["facet"], item["shown"], item["pass"]), item["shown"])
    touched.add("a") if a is not None else None
    for label in sorted(touched):
        records.write(loaded[label], label)
    reconcile(records, file_id, vocabs)
    return total
