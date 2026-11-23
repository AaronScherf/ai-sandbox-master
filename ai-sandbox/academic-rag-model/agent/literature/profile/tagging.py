"""3ie intervention / outcome tagging by staged descent of the unmodified taxonomy (spec A, step 3).

Round 1 offers the sectors, round 2 the children of the sectors chosen in round 1, round 3 the children of the
branches chosen in round 2. Every tag needs a verbatim quote that the page text confirms. A leaf implies its
ancestors at read time; a branch-only tag never counts toward a leaf.
"""

from dataclasses import dataclass
from pathlib import Path

from agent.literature.profile.review import effective_value
from agent.literature.profile.taxonomy import ancestors, rollup
from agent.literature.stage import MAX_CARD_CHARS
from agent.literature.transcript import check_quote, split_pages
from agent.literature.vocab import Vocabulary
from core.agent_tasks.tasks import Passage, Task
from core.indexer.index_card import find_card_by_file_id
from core.indexer.research_profile import RESEARCH_REPORT_TYPES, derive_applicability, set_research_profile

STAGE = "tag"
PROMPT_VERSION = "tag-v3"
KINDS = ("intervention", "outcome")

INSTRUCTIONS = """\
You are tagging one research document against a fixed taxonomy of {kind}s. Use only the pages on the card.
The card lists the terms you may choose at this level, each with its definition. Choose a term only when the paper
itself evaluates, models or reports that {kind} (not when it is merely mentioned in passing or in the literature
review). Choose nothing when nothing fits; do not stretch a definition to fit.
A paper that reviews or synthesises the evidence on a {kind} (a systematic review, meta-analysis or evidence synthesis) counts as reporting it: tag the {kind}s it synthesises, but not ones it only lists as background.
Tag each kind on its own. A paper that measures an outcome without evaluating or modelling any intervention still gets its outcome tags (an outcome-only paper is a valid and common case), and a paper that evaluates or models an intervention without measuring an outcome still gets its intervention tags. Never leave a kind empty just because the other kind is absent.
Give a `## Result` YAML block:
tags:
  - term_id: <an id from the list>
    quote: <exact words copied from the page, 8 to 300 characters>
    locator: <page number the quote is on>
An empty list (`tags: []`) is a valid answer."""


@dataclass
class Target:
    index_root: str
    vocabs: dict  # {"intervention": Vocabulary, "outcome": Vocabulary}


def depth(vocab: Vocabulary, term_id: str) -> int:
    return len(ancestors(vocab, term_id)) + 1


def _offered(vocab: Vocabulary, level: int, chosen: list[str]) -> list[str]:
    if level == 1:
        return [t.id for t in vocab.terms.values() if depth(vocab, t.id) == 1]
    return [t.id for t in vocab.terms.values() if t.parent in chosen and depth(vocab, t.id) == level]


def _listing(vocab: Vocabulary, ids: list[str]) -> str:
    return "\n".join(f"- {i}: {vocab.terms[i].label}. {vocab.terms[i].definition}".rstrip() for i in ids)


def make_round_tasks(target: Target, cards: list[dict], kind: str, level: int, prior: dict[str, list[str]],
                     *, redo: bool = False):
    """One card per document for this round. Returns (tasks, skipped) with skipped mapping file_id to the reason."""
    vocab = target.vocabs[kind]
    tasks: list[Task] = []
    skipped: dict[str, str] = {}
    for card in cards:
        fid = card["file_id"]
        profile = card.get("research_profile") or {}
        report_type = effective_value(target.index_root, card, "report_type")  # an owner decision outranks the model
        if report_type not in RESEARCH_REPORT_TYPES:
            skipped[fid] = f"not a research document (report_type={report_type!r})"
            continue
        done = profile.get("provenance", {}).get(f"tag_{kind}_L{level}", {})
        if done.get("prompt_version") == PROMPT_VERSION and not redo:
            skipped[fid] = "already tagged at this level with this prompt version"
            continue
        chosen = prior.get(fid, [])
        if level > 1 and not chosen:
            skipped[fid] = "no term was chosen at the previous level"
            continue
        offered = _offered(vocab, level, chosen)
        if not offered:
            skipped[fid] = "the chosen terms have no children to refine"
            continue
        try:
            pages = split_pages((Path(target.index_root) / card["path"]).read_text(encoding="utf-8"))
        except (OSError, KeyError) as exc:
            skipped[fid] = f"cannot read the transcript: {exc}"
            continue
        if not pages:
            skipped[fid] = "transcript has no page markers"
            continue
        size = sum(len(t) for t in pages.values())
        if size > MAX_CARD_CHARS:
            skipped[fid] = f"too_long: {size} characters, over the {MAX_CARD_CHARS} limit for one card"
            continue
        context = "\n".join([f"Paper: {card.get('title') or fid}", f"file_id: {fid}",
                             f"Choose {kind} terms from this list (level {level}):", _listing(vocab, offered)])
        passages = [Passage(id=f"P{n}", source=card.get("title") or fid, ref=f"page {n}", text=text)
                    for n, text in sorted(pages.items())]
        tasks.append(Task(id=f"tag-{kind}-L{level}-{fid}", stage=STAGE,
                          subject={"file_id": fid, "kind": kind, "level": level, "offered": offered,
                                   "prompt_version": PROMPT_VERSION},
                          instructions=INSTRUCTIONS.format(kind=kind), context=context, passages=passages))
    return tasks, skipped


def _pages_of(entry: dict) -> dict[int, str]:
    out: dict[int, str] = {}
    for p in entry.get("passages", []):
        ref = p.get("ref", "")
        if ref.startswith("page "):
            out[int(ref[5:])] = p["text"]
    return out


def validate_result(entry: dict, result: dict, target: Target) -> list[str]:
    tags = result.get("tags")
    if not isinstance(tags, list):
        return ["tags: give a list (an empty list is allowed)"]
    pages, offered = _pages_of(entry), set(entry["subject"]["offered"])
    problems: list[str] = []
    for n, tag in enumerate(tags, 1):
        if not isinstance(tag, dict) or tag.get("term_id") not in offered:
            problems.append(f"tag {n}: term_id {tag.get('term_id') if isinstance(tag, dict) else tag!r} "
                            "was not offered on this card at this level")
            continue
        problem = check_quote(tag.get("quote"), tag.get("locator"), pages)
        if problem:
            problems.append(f"tag {n} ({tag['term_id']}): {problem}")
    return problems


def apply_result(target: Target, entry: dict, result: dict, provenance: dict) -> str | None:
    s = entry["subject"]
    fid, kind, level = s["file_id"], s["kind"], s["level"]
    profile = find_card_by_file_id(target.index_root, fid)[1].get("research_profile") or {}
    # A redo of level N invalidates the deeper tags that were chosen under the old level-N choices.
    kept = [t for t in profile.get(f"{kind}_tags", []) if t["level"] < level]
    new = [{"term_id": t["term_id"], "level": level, "quote": t["quote"].strip(), "quote_locator": t["locator"]}
           for t in result["tags"]]
    tags = sorted(kept + new, key=lambda t: (t["level"], t["term_id"]))
    lists = {"intervention": profile.get("intervention_tags", []), "outcome": profile.get("outcome_tags", [])}
    lists[kind] = tags
    prov = dict(profile.get("provenance") or {})
    prov[f"tag_{kind}_L{level}"] = {"prompt_version": PROMPT_VERSION, **provenance}
    set_research_profile(target.index_root, fid, {
        f"{kind}_tags": tags, "provenance": prov,
        "applicability": derive_applicability(lists["intervention"], lists["outcome"], assessed=True)})
    return None


def covered_terms(vocab: Vocabulary, tags: list[dict]) -> set[str]:
    """Every term a set of tags speaks for: the tagged terms plus their ancestors, never their descendants."""
    return rollup(vocab, [t["term_id"] for t in tags])


def deepest_tags(vocab: Vocabulary, tags: list[dict]) -> list[dict]:
    """The most specific tags: those with no other tag beneath them."""
    ids = {t["term_id"] for t in tags}
    parents = {a for i in ids for a in ancestors(vocab, i)}
    return [t for t in tags if t["term_id"] not in parents]
