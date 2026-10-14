"""Seed stage: the richer outline (statements, headings), the stricter card, and required-concept validation."""
from agent.concept_graph.schema import SeedConfig
from agent.concept_graph.scaffold import scaffold
from agent.concept_graph.stages import seed
from agent.concept_graph.store import GraphStore
from cg_helpers import entry_for

PROV = {"driver": "agent", "agent": "test-agent", "run": "r1"}

SLIDES = """Utility maximization

Axiom α (AKA Independence of Irrelevant Alternatives) If x ∈ C(B) and x ∈ A ⊆ B then x ∈ C(A)

Axiom β If x, y ∈ C(A), A ⊆ B and y ∈ C(B) then x ∈ C(B)

Theorem

A choice function satisfies WARP if and only if it satisfies alpha and beta

Definition
A utility function represents a preference relation

Axiom α (AKA Independence of Irrelevant Alternatives) If x ∈ C(B) and x ∈ A ⊆ B then x ∈ C(A)

Theorem

## Related notes
- [[somewhere|current: a title]]
"""

GOOD = {
    "topics": ["preferences"],
    "sections": [{"id": "s01-preferences", "title": "Preferences", "order": 1, "state": "taught", "lectures": ["2026-09-07"]}],
    "nodes": [{"id": "preference-relation", "name": "Preference relation", "kind": "object", "section": "s01-preferences",
               "topic": "preferences", "gist": "How a person ranks alternatives."},
              {"id": "utility-function", "name": "Utility function", "kind": "function", "section": "s01-preferences",
               "topic": "preferences"}],
}


def rich_hub(tmp_path):
    notes = tmp_path / "hub" / "academic_notes" / "microecon"
    files = {
        "syllabus/processed_outputs/Syllabus.md": "Course topics: preferences and choice, utility maximization, demand.",
        "professor_notes/processed_outputs/2.Utility_Maximization_1.md": SLIDES,
        "lecture_notes/processed_outputs/Microeconomics 2026-09-17 10.12.38.excalidraw.rag.md":
            "Some prose.\n\nDefinition\nA budget set contains the bundles a consumer can afford\n",
        "textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/01_preference_and_choice.rag.md":
            "# Preference and Choice\n\n## 1.A Introduction\n\n## 1.B Preference Relations\n\n### Utility Functions\n\n## Related notes\n",
        "textbooks/processed_outputs/Press_Microeconomic_Theory_2011/chapters/02_consumer_choice.rag.md":
            "# Consumer Choice\n\n## 2.B Commodities\n",
    }
    for rel, text in files.items():
        path = notes / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path / "hub"


def empty_store(tmp_path):
    root = tmp_path / "empty-graph"
    scaffold(root, "someone/g", "Some One", 2026, fetch_text=lambda url: "license")
    return GraphStore(root)


def write_seed_config(store, text):
    (store.root / "config" / "seed.yaml").write_text(text, encoding="utf-8")


def task_for(tmp_path, **kw):
    store = empty_store(tmp_path)
    task = seed.make_tasks(store, None, hub_root=str(rich_hub(tmp_path)), course="microecon", **kw)[0]
    return store, task, entry_for(task)


def test_statement_anchors_keep_a_label_with_its_statement_and_drop_repeats_and_bare_labels():
    anchors = seed.statement_anchors(SLIDES)
    assert any(a.startswith("Axiom α (AKA Independence of Irrelevant Alternatives)") for a in anchors)
    assert sum(1 for a in anchors if a.startswith("Axiom α")) == 1
    assert any(a.startswith("Axiom β If x, y") for a in anchors)
    assert any(a.startswith("Theorem A choice function satisfies WARP") for a in anchors)
    assert any(a.startswith("Definition A utility function represents") for a in anchors)
    assert "Theorem" not in anchors
    assert not any("Related notes" in a or "somewhere" in a for a in anchors)


def test_statement_anchors_are_capped():
    text = "\n".join(f"Definition\nConcept number {i} is defined carefully here" for i in range(50))
    assert len(seed.statement_anchors(text, limit=7)) == 7


def test_section_headings_are_levels_one_to_three_without_boilerplate():
    text = "# Preference and Choice\n## 1.A Introduction\n### Utility Functions\n#### too deep\n## Related notes\n## 1.A Introduction\n"
    assert seed.section_headings(text) == ["Preference and Choice", "1.A Introduction", "Utility Functions"]


def test_outline_offers_slide_and_lecture_statements_as_passages(tmp_path):
    _, passages = seed.outline_context(str(rich_hub(tmp_path)), "microecon")
    slides = next(p for p in passages if p.source == "slides" and "Utility Maximization 1" in p.ref)
    assert "Axiom β If x, y" in slides.text
    lecture = next(p for p in passages if p.source == "lecture")
    assert "A budget set contains the bundles" in lecture.text


def test_textbook_section_headings_appear_only_for_configured_chapters(tmp_path):
    hub = str(rich_hub(tmp_path))
    _, plain = seed.outline_context(hub, "microecon")
    assert not any("1.B Preference Relations" in p.text for p in plain)
    _, scoped = seed.outline_context(hub, "microecon", config=SeedConfig(textbook_chapters={"mwg": [1]}))
    joined = "\n".join(p.text for p in scoped)
    assert "1.B Preference Relations" in joined and "Utility Functions" in joined
    assert "2.B Commodities" not in joined and "Related notes" not in joined


def test_the_card_explains_kinds_shows_a_format_example_and_ends_with_a_self_check(tmp_path):
    store, task, _ = task_for(tmp_path)
    assert "Self-check" in task.instructions and "example-concept" in task.instructions
    assert "Eponymous" in task.instructions  # concept names with people in them are fine; instructors are not
    assert "do not include names of people" not in (task.instructions + task.context).lower()
    assert "- property:" in task.context and "- theorem:" in task.context  # glossary for the vocabulary's kinds


def test_scope_and_required_concepts_are_on_the_card_and_in_the_manifest_subject(tmp_path):
    store = empty_store(tmp_path)
    write_seed_config(store, "scope: Choice theory only; no game theory.\nmust_include:\n  - Preorder\n  - [GARP, Generalized axiom of revealed preference]\n")
    task = seed.make_tasks(store, None, hub_root=str(rich_hub(tmp_path)), course="microecon")[0]
    assert "Choice theory only; no game theory." in task.context
    assert "Preorder" in task.context and "GARP" in task.context
    assert task.subject["must_include"] == ["Preorder", ["GARP", "Generalized axiom of revealed preference"]]


def test_additive_mode_lists_existing_names_and_says_to_add_only_what_is_missing(tmp_path):
    store = empty_store(tmp_path)
    seed.apply_result(store, {}, GOOD, PROV)
    task = seed.make_tasks(store, None, hub_root=str(rich_hub(tmp_path)), course="microecon", redo=True)[0]
    assert "Preference relation" in task.context and "s01-preferences" in task.context
    assert "already in the graph" in task.context.lower() and "only what is missing" in task.instructions.lower()


def test_missing_required_concepts_are_bounced_and_aliases_count(tmp_path):
    store, task, entry = task_for(tmp_path)
    entry["subject"]["must_include"] = ["Utility function", ["GARP", "Generalized axiom of revealed preference"], "Preorder"]
    msgs = seed.validate_result(entry, GOOD, store)
    assert len(msgs) == 1 and "GARP" in msgs[0] and "Preorder" in msgs[0] and "Utility function" not in msgs[0]
    extra = dict(GOOD, nodes=GOOD["nodes"] + [
        {"id": "garp", "name": "Generalized Axiom of Revealed Preference (GARP)", "kind": "axiom", "section": "s01-preferences", "topic": "preferences"},
        {"id": "preorder", "name": "Preorder", "kind": "object", "section": "s01-preferences", "topic": "preferences"}])
    assert seed.validate_result(entry, extra, store) == []


def test_required_concepts_already_in_the_graph_are_satisfied(tmp_path):
    store, task, entry = task_for(tmp_path)
    seed.apply_result(store, entry, GOOD, PROV)
    entry["subject"]["must_include"] = ["Preference relation"]
    more = {"nodes": [{"id": "x1", "name": "Another concept", "kind": "object", "section": "s01-preferences", "topic": "preferences"}]}
    assert seed.validate_result(entry, more, store) == []


def test_duplicate_names_are_bounced_even_with_different_ids_or_punctuation(tmp_path):
    store, task, entry = task_for(tmp_path)
    dup = dict(GOOD, nodes=GOOD["nodes"] + [{"id": "pref-rel-2", "name": "preference  RELATION!", "kind": "object",
                                              "section": "s01-preferences", "topic": "preferences"}])
    assert any("duplicates" in m for m in seed.validate_result(entry, dup, store))
    seed.apply_result(store, entry, GOOD, PROV)
    again = {"nodes": [{"id": "pr3", "name": "Preference Relation", "kind": "object", "section": "s01-preferences", "topic": "preferences"}]}
    assert any("already" in m and "Preference relation" in m for m in seed.validate_result(entry, again, store))


def test_outline_offers_earlier_years_post_lecture_slides_under_their_own_source(tmp_path):
    hub = rich_hub(tmp_path)
    for year, folder in (("2024", "Post lecture notes"), ("2025", "Post-Lecture Notes")):
        d = hub / "academic_notes" / "microecon" / f"{year}_class" / folder / "processed_outputs"
        d.mkdir(parents=True)
        (d / "8.Production.md").write_text("Production\n\nDefinition\nA production set is a set of feasible input-output plans\n",
                                           encoding="utf-8")
    context, passages = seed.outline_context(str(hub), "microecon")
    assert {p.source for p in passages if p.source.endswith(("2024", "2025"))} == {"slides-2024", "slides-2025"}
    assert any(p.source == "slides-2025" and p.ref == "Production" for p in passages)
    assert "2024 class slide sets (in order): Production" in context
