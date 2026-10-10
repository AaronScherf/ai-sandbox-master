import pytest

from agent.concept_graph.scaffold import scaffold
from agent.concept_graph.stages import seed
from agent.concept_graph.store import GraphStore
from agent.concept_graph.validate import errors, validate
from cg_helpers import copy_sample, entry_for

PROV = {"driver": "agent", "agent": "test-agent", "run": "r1"}


SYLLABUS = """---
source_pdf: academic_resources/microecon/syllabus/Syllabus.pdf
routing: gemini_accumulating
---

<!-- page 1 -->

**GR6211: Microeconomic Analysis I Part I**

**Professor:** Jane Q. Professor

**Email:** jane.professor@example.test

**Office Hours:** {hours}

**Teaching Assistant:** Some Assistant

**Website:** http://www.example.test/~jqp

<u>**Course Description**</u>

Course topics: preferences and choice, utility maximization, demand and producer theory, then risk.
"""


def make_hub(tmp_path):
    notes = tmp_path / "hub" / "academic_notes" / "microecon"
    files = {
        "syllabus/processed_outputs/Syllabus.md": SYLLABUS.format(hours="Wednesdays 3:00-4:00"),
        "syllabus/processed_outputs/Syllabus (1).md": SYLLABUS.format(hours="Thursdays 4:00-5:00"),
        "textbooks/processed_outputs/Rubenstein_Lecture_Notes_2026/chapters/00_front_matter.rag.md": "front matter text",
        "textbooks/processed_outputs/Rubenstein_Lecture_Notes_2026/chapters/01_introduction.rag.md": "intro",
        "textbooks/processed_outputs/Rubenstein_Lecture_Notes_2026/chapters/02_preferences.rag.md": "prefs",
        "lecture_notes/processed_outputs/Microeconomics 2026-09-07.excalidraw.rag.md": "notes",
        "lecture_notes/processed_outputs/Microeconomics 2026-09-10 10.09.33.excalidraw.rag.md": "notes",
        "lecture_notes/Microeconomics 2026-09-29 10.07.07.excalidraw.md": "raw note, not yet processed",
        "professor_notes/processed_outputs/2.Utility_Maximization_1.md": "slides",
        "professor_notes/processed_outputs/10.Late_Topic.md": "slides",
        "professor_notes/processed_outputs/1.Course_Intro.md": "slides",
        "professor_notes/processed_outputs/2.Utility_Maximization_1_Proofs.md": "proofs",
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


GOOD = {
    "topics": ["preferences"],
    "sections": [
        {"id": "s01-preferences", "title": "Preferences", "order": 1, "state": "taught", "lectures": ["2026-09-07"]},
        {"id": "s02-utility", "title": "Utility", "order": 2, "state": "planned"},
    ],
    "nodes": [
        {"id": "preference-relation", "name": "Preference relation", "kind": "object", "section": "s01-preferences",
         "topic": "preferences", "gist": "How a person ranks alternatives."},
        {"id": "utility-function", "name": "Utility function", "kind": "function", "section": "s02-utility", "topic": "rational-choice"},
    ],
}


def task_for(tmp_path, store=None):
    store = store or empty_store(tmp_path)
    task = seed.make_tasks(store, None, hub_root=str(make_hub(tmp_path)), course="microecon")[0]
    return store, task, entry_for(task)


def test_outline_context_lists_chapters_and_dates_from_a_tmp_hub(tmp_path):
    context, passages = seed.outline_context(str(make_hub(tmp_path)), "microecon")
    assert "2026-09-07" in context and "2026-09-10" in context and "Utility Maximization 1" in context
    toc = next(p for p in passages if p.source == "rubinstein")
    assert "Introduction" in toc.text and "Preferences" in toc.text and "front matter" not in toc.text.lower()


def test_seed_refuses_when_the_graph_already_has_taught_sections(tmp_path):
    store = GraphStore(copy_sample(tmp_path))
    hub = str(make_hub(tmp_path))
    with pytest.raises(ValueError, match="already"):
        seed.make_tasks(store, None, hub_root=hub, course="microecon")
    assert len(seed.make_tasks(store, None, hub_root=hub, course="microecon", redo=True)) == 1


def test_task_card_tells_the_agent_the_vocabulary_and_existing_ids(tmp_path):
    store, task, entry = task_for(tmp_path)
    assert "object" in task.context and "order-theory" in task.context
    assert task.subject["stage"] == "seed" and task.subject["must_include"] == []


def test_valid_result_is_accepted(tmp_path):
    store, task, entry = task_for(tmp_path)
    assert seed.validate_result(entry, GOOD, store) == []


def test_empty_result_and_unknown_keys_are_bounced(tmp_path):
    store, task, entry = task_for(tmp_path)
    assert any("nothing" in m for m in seed.validate_result(entry, {"sections": [], "nodes": []}, store))
    assert any("unknown" in m for m in seed.validate_result(entry, dict(GOOD, extra=1), store))


def test_duplicate_or_reused_ids_are_bounced(tmp_path):
    store, task, entry = task_for(tmp_path)
    twice = dict(GOOD, nodes=GOOD["nodes"] + [GOOD["nodes"][0]])
    assert any("twice" in m for m in seed.validate_result(entry, twice, store))
    sample = GraphStore(copy_sample(tmp_path / "again"))
    reused = {"sections": [{"id": "s01-binary-relations", "title": "x", "order": 9, "state": "planned"}], "nodes": []}
    assert any("already" in m for m in seed.validate_result(entry, reused, sample))


def test_bad_slugs_orders_and_states_are_bounced(tmp_path):
    store, task, entry = task_for(tmp_path)
    bad = {"sections": [{"id": "Bad Id", "title": "x", "order": 1, "state": "taught"},
                        {"id": "s02-ok", "title": "y", "order": 1, "state": "done"}], "nodes": []}
    msgs = seed.validate_result(entry, bad, store)
    assert any("slug" in m for m in msgs) and any("order" in m for m in msgs) and any("state" in m for m in msgs)


def test_node_in_unknown_section_and_unknown_kind_and_unknown_topic_are_bounced(tmp_path):
    store, task, entry = task_for(tmp_path)
    node = {"id": "n1", "name": "N", "kind": "gizmo", "section": "s99", "topic": "astrology"}
    msgs = seed.validate_result(entry, {"sections": [GOOD["sections"][0]], "nodes": [node]}, store)
    assert any("section" in m for m in msgs) and any("kind" in m for m in msgs) and any("topic" in m for m in msgs)


def test_copied_gist_is_bounced(tmp_path):
    store, task, entry = task_for(tmp_path)
    long_gist = "course topics preferences and choice utility demand and then some more of the same syllabus words"
    entry["passages"].append({"id": "P9", "source": "other", "ref": "syllabus", "text": long_gist, "path": ""})
    msgs = seed.validate_result(entry, dict(GOOD, nodes=[dict(GOOD["nodes"][0], gist=long_gist)]), store)
    assert any("gist" in m for m in msgs)


def test_apply_adds_vocab_sections_and_skeleton_nodes_as_proposed(tmp_path):
    store, task, entry = task_for(tmp_path)
    assert seed.apply_result(store, entry, GOOD, PROV) is None
    g = store.read_all()
    assert "preferences" in g.vocab.topics
    assert [s.id for s in g.sections] == ["s01-preferences", "s02-utility"]
    node = next(n for n in g.nodes if n.id == "preference-relation")
    assert node.status == "proposed" and node.explanation == "" and node.provenance.run == "r1"
    assert g.node_files["utility-function"] == "s02-utility"


def test_seeded_graph_validates_apart_from_unfilled_warnings(tmp_path):
    store, task, entry = task_for(tmp_path)
    seed.apply_result(store, entry, GOOD, PROV)
    issues = validate(store.read_all())
    assert errors(issues) == []
    assert {i.code for i in issues} <= {"orphan", "unfilled"}


def test_syllabus_excerpt_drops_contact_details_and_file_metadata_and_is_not_duplicated(tmp_path):
    context, passages = seed.outline_context(str(make_hub(tmp_path)), "microecon")
    syllabi = [p for p in passages if p.source == "other"]
    assert len(syllabi) == 1  # the two near-identical syllabi differ only in office hours
    text = syllabi[0].text
    assert "Course topics: preferences and choice" in text
    for gone in ("@", "Professor:", "Jane", "Assistant", "Office Hours", "source_pdf", "routing", "http", "<!-- page"):
        assert gone not in text, gone


def test_context_points_to_the_passages_instead_of_repeating_them(tmp_path):
    context, passages = seed.outline_context(str(make_hub(tmp_path)), "microecon")
    assert "Course topics" not in context and "1. Introduction" not in context
    assert "offered passages" in context.lower()


def test_lecture_dates_include_notes_that_have_not_been_processed_yet(tmp_path):
    context, _ = seed.outline_context(str(make_hub(tmp_path)), "microecon")
    assert "2026-09-29" in context


def test_slide_sets_are_in_numeric_course_order_and_proofs_are_left_out(tmp_path):
    context, _ = seed.outline_context(str(make_hub(tmp_path)), "microecon")
    line = next(l for l in context.splitlines() if l.startswith("Professor slide sets"))
    assert line.index("Course Intro") < line.index("Utility Maximization 1") < line.index("Late Topic")
    assert "Proofs" not in line
