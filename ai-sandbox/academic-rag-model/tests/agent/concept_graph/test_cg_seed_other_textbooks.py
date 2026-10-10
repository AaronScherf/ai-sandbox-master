from agent.concept_graph.schema import SeedConfig
from agent.concept_graph.stages import seed


def hub_with_an_unlisted_textbook(tmp_path):
    book = tmp_path / "hub" / "academic_notes" / "econometrics" / "textbooks" / "processed_outputs" / "Hayashi_Econometrics_2000" / "chapters"
    book.mkdir(parents=True)
    (book / "01_finite_sample_properties_of_ols.rag.md").write_text("# Finite-Sample Properties of OLS\n\n## 1.1 The Classical Linear Regression Model\n", encoding="utf-8")
    (book / "02_large_sample_theory.rag.md").write_text("# Large-Sample Theory\n\n## 2.1 Asymptotics\n", encoding="utf-8")
    return str(tmp_path / "hub")


def test_a_textbook_the_classifier_does_not_know_can_be_scoped_by_its_folder_name(tmp_path):
    hub = hub_with_an_unlisted_textbook(tmp_path)
    _, passages = seed.outline_context(hub, "econometrics", config=SeedConfig(textbook_chapters={"Hayashi_Econometrics_2000": [1]}))
    heads = [p for p in passages if "section headings" in p.text.lower()]
    assert len(heads) == 1 and "1.1 The Classical Linear Regression Model" in heads[0].text
    assert "Asymptotics" not in "\n".join(p.text for p in passages)


def test_folder_name_matching_ignores_case(tmp_path):
    hub = hub_with_an_unlisted_textbook(tmp_path)
    _, passages = seed.outline_context(hub, "econometrics", config=SeedConfig(textbook_chapters={"hayashi_econometrics_2000": [2]}))
    assert "2.1 Asymptotics" in "\n".join(p.text for p in passages)


def test_unlisted_books_still_get_a_table_of_contents(tmp_path):
    _, passages = seed.outline_context(hub_with_an_unlisted_textbook(tmp_path), "econometrics")
    toc = next(p for p in passages if p.ref == "table of contents")
    assert "1. Finite sample properties of ols" in toc.text and "2. Large sample theory" in toc.text
