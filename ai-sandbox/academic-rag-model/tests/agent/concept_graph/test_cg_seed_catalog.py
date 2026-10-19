"""Seed evidence built from the course-materials catalog: headings, instructor notes, caps, decisions, authority."""
from agent.concept_graph.schema import SeedConfig
from agent.concept_graph.stages import seed
from core.course_materials import record_decision

ECON = "econometrics"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def econ_hub(tmp_path):
    hub = tmp_path / "hub"
    n = hub / "academic_notes" / ECON
    write(n / "professor_notes/processed_outputs/slides2.md",
          "# Properties of OLS\n\n# Gauss Markov Theorem\n\n**Assumption 4.**\nE[e|X] = 0 holds here\n\n# Omitted variables bias\n")
    write(n / "professor_notes/processed_outputs/092126.md",
          "<!-- page 1 -->\n\nSept 21\n\nAssumptions 7.1 $n = \\text{sample size}$.\n\n(1) iid\n")
    for stamp, text in (("10.19.22", "# Delta method\n"), ("14.16.17", "# Wald test\n")):
        write(n / f"lecture_notes/processed_outputs/Econometrics 2026-10-07 {stamp}.excalidraw.rag.md",
              "---\nsource_excalidraw: x\n---\n\n" + text)
    write(n / "ta_notes/processed_outputs/TA1.md", "Recitation 1\n\n# Matrix algebra review\n")
    return hub


def test_slide_headings_and_numbered_assumptions_reach_the_card(tmp_path):
    _, passages = seed.outline_context(str(econ_hub(tmp_path)), ECON)
    text = "\n".join(p.text for p in passages)
    assert "Gauss Markov Theorem" in text and "Omitted variables bias" in text
    assert "Assumption 4 E[e|X] = 0 holds here" in text
    assert "Assumptions 7.1 $n" in text


def test_dated_instructor_notes_join_the_lecture_timeline(tmp_path):
    hub = econ_hub(tmp_path)
    record_decision(hub, ECON, f"academic_notes/{ECON}/professor_notes/processed_outputs/092126.md",
                    role="instructor", format="handwritten")
    context, passages = seed.outline_context(str(hub), ECON)
    assert "2026-09-21" in context.split("Lecture dates with notes: ")[1].splitlines()[0]
    assert any(p.source == "notes" and p.ref == "2026-09-21" for p in passages)


def test_two_lecture_notes_on_one_date_are_both_offered(tmp_path):
    _, passages = seed.outline_context(str(econ_hub(tmp_path)), ECON)
    lecture = [p for p in passages if p.source == "lecture" and p.ref == "2026-10-07"]
    assert len(lecture) == 1 and "Delta method" in lecture[0].text and "Wald test" in lecture[0].text


def test_recitation_material_offers_headings_only(tmp_path):
    _, passages = seed.outline_context(str(econ_hub(tmp_path)), ECON)
    rec = [p for p in passages if p.source == "recitation"]
    assert rec and "Matrix algebra review" in rec[0].text


def test_role_caps_limit_instructor_passages(tmp_path, monkeypatch):
    hub = econ_hub(tmp_path)
    for i in range(5):
        write(hub / "academic_notes" / ECON / f"professor_notes/processed_outputs/{i}.Deck.md", f"# Topic {i}\n")
    monkeypatch.setitem(seed.ROLE_CAPS, "instructor", 2)
    _, passages = seed.outline_context(str(hub), ECON)
    assert len([p for p in passages if p.source in ("slides", "notes")]) == 2


def test_a_book_key_decision_scopes_textbook_chapters(tmp_path):
    hub = tmp_path / "hub"
    book = hub / "academic_notes" / ECON / "textbooks/processed_outputs/Hansen_ECONOMETRICS_2022"
    write(book / "chapters/01_intro.rag.md", "# Intro\n\n## 1.1 What is econometrics\n")
    write(book / "chapters/04_least_squares.rag.md", "# Least squares\n\n## 4.2 Projection\n")
    record_decision(hub, ECON, str(book), book="hansen22")
    _, passages = seed.outline_context(str(hub), ECON, config=SeedConfig(textbook_chapters={"hansen22": [4]}))
    joined = "\n".join(p.text for p in passages)
    assert "4.2 Projection" in joined and "1.1 What is econometrics" not in joined
    assert {p.source for p in passages} == {"hansen22"}


def test_class_material_comes_before_the_students_notes(tmp_path):
    _, passages = seed.outline_context(str(econ_hub(tmp_path)), ECON)
    sources = [p.source for p in passages]
    assert sources.index("slides") < sources.index("lecture") and sources.index("recitation") < sources.index("lecture")


def test_the_seed_card_says_class_material_outranks_the_students_notes(tmp_path):
    from agent.concept_graph.scaffold import scaffold
    from agent.concept_graph.store import GraphStore

    root = tmp_path / "g"
    scaffold(root, "someone/g", "Some One", 2026, fetch_text=lambda url: "license")
    task = seed.make_tasks(GraphStore(root), None, hub_root=str(econ_hub(tmp_path)), course=ECON)[0]
    text = task.instructions.lower()
    assert "authoritative" in text and "may contain mistakes" in text
