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


def test_recitation_material_offers_its_statements_and_headings(tmp_path):
    # Econometrics' TA notes hold most of the course's labelled statements (111 against the instructor's 15).
    hub = econ_hub(tmp_path)
    write(hub / "academic_notes" / ECON / "ta_notes/processed_outputs/TA2.md",
          "# Sampling\n\nDefinition 4 (Statistic). A statistic is a function of a sample.\n")
    _, passages = seed.outline_context(str(hub), ECON)
    rec = "\n".join(p.text for p in passages if p.source == "recitation")
    assert "Matrix algebra review" in rec and "Definition 4 (Statistic). A statistic is a function of a sample." in rec


def test_recitation_is_capped_at_fifteen_files(tmp_path):
    hub = econ_hub(tmp_path)
    for i in range(20):
        write(hub / "academic_notes" / ECON / f"ta_notes/processed_outputs/{i:02d}-topic.md", f"# Distinct topic number {i}\n")
    _, passages = seed.outline_context(str(hub), ECON)
    assert len([p for p in passages if p.source == "recitation"]) == 15


def test_a_near_duplicate_syllabus_is_offered_once(tmp_path):
    # econometrics has the syllabus twice: a Markdown copy and the conversion of its PDF, with different line breaks.
    hub = econ_hub(tmp_path)
    body = ("Introduction to Econometrics. Part A consists of 13 classes. Evaluation: 2 problem sets, two 30 minute "
            "exams and a final exam. Topics: linear regression model, hypothesis testing and model selection, "
            "Bayesian estimation, time series regression and forecasting.")
    write(hub / "academic_notes" / ECON / "syllabus/ECON6411_syllabus.md", "#syllabus\n\n" + body)
    write(hub / "academic_notes" / ECON / "syllabus/processed_outputs/ec6411A.md",
          "---\nsource_pdf: x.pdf\n---\n\n<!-- page 1 -->\n\n" + body.replace(". ", ".\n"))
    _, passages = seed.outline_context(str(hub), ECON)
    assert len([p for p in passages if p.source == "syllabus"]) == 1


def test_an_earlier_offerings_deck_that_repeats_this_years_is_listed_but_not_offered_again(tmp_path):
    hub = econ_hub(tmp_path)
    n = hub / "academic_notes" / ECON
    deck = "Definition 1 (OLS). The least squares estimator minimizes the sum of squared residuals over b.\n"
    write(n / "professor_notes/processed_outputs/slides1.md", deck)
    write(n / "class_2024/Slides/processed_outputs/slides1.md", deck)
    record_decision(hub, ECON, f"academic_notes/{ECON}/class_2024/Slides/processed_outputs/slides1.md",
                    role="instructor", format="slides", offering="2024")
    context, passages = seed.outline_context(str(hub), ECON)
    assert not [p for p in passages if p.source == "slides-2024"]
    assert "2024 offering slide sets (in order): slides1" in context


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


def test_an_earlier_offering_keeps_its_late_topics(tmp_path):
    # microecon 2024 has pre- and post-lecture versions of each deck plus proofs (about 21 decks); the late topics
    # (risk and uncertainty) are why earlier offerings are offered at all, so a cap must not cut them off.
    from core.course_materials import Catalog, Material

    hub = tmp_path / "hub"
    mats = []
    for i in range(1, 12):
        for kind in ("pre", "post"):
            rel = f"academic_notes/{ECON}/class_2024/{kind}/processed_outputs/{i}.Topic_{i}_{kind}.md"
            write(hub / rel, f"Definition\nConcept {i} {kind} is defined here\n")
            mats.append(Material(path=rel, role="instructor", format="slides", offering="2024", order=[i, "", rel]))
    _, passages = seed.outline_context(str(hub), ECON, catalog=Catalog(course=ECON, materials=mats))
    refs = {p.ref for p in passages if p.source == "slides-2024"}
    assert "Topic 11 post" in refs and "Topic 11 pre" in refs


def test_an_earlier_offering_offers_instructor_material_of_any_format(tmp_path):
    # microecon's 2024/2025 "Course Intro" and "Failures Of Rationality" decks have portrait pages (format typeset):
    # page shape must not decide which instructor material reaches the card.
    from core.course_materials import Catalog, Material

    hub = tmp_path / "hub"
    rel = f"academic_notes/{ECON}/class_2024/deck/processed_outputs/1.Course_Intro.md"
    write(hub / rel, "Definition\nA course is a sequence of lectures on one subject\n")
    cat = Catalog(course=ECON, materials=[Material(path=rel, role="instructor", format="typeset", offering="2024")])
    context, passages = seed.outline_context(str(hub), ECON, catalog=cat)
    assert any(p.source == "slides-2024" and p.ref == "Course Intro" for p in passages)
    assert "2024 offering slide sets (in order): Course Intro" in context
