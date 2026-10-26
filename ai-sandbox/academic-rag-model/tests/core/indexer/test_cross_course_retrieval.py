"""
Cross-course foundational retrieval validation.

docs/trackers/academic_hub_to_do.md ("Cross-course foundational retrieval
testing", added 2026-10-04): validate that index_search.search()/
search_passages() actually surface a *different* course's passage when a
query is phrased in one course's vocabulary but the grounding material
lives in another course indexed under the same --root.

Real-corpus search (2026-10-25): both econometrics and math-camp ARE
indexed under ai-sandbox/academic-hub/.index/ (econometrics.json,
math-camp.json). A genuine real-world pairing exists:
  - academic_notes/econometrics/professor_notes/processed_outputs/091426.md
    (card file_id 18b4d47f...) -- OLS derivation that USES the projection
    matrix P = X(X'X)^-1 X' and the residual-maker M = I - P, relying on
    their idempotency, without re-deriving the idempotent-matrix lemma.
  - academic_notes/math-camp/recitation_slides/processed_outputs/
    "Math_Camp_Recitation_2 with solution.md" (card file_id caa0f05b...) --
    works the idempotent-matrix lemma itself (A^2 = A and its consequences)
    as a linear-algebra exercise.

That is the tracker's "Econometrics needs Math Camp matrix algebra" case,
with a real course pair instead of a hypothetical one.

HOWEVER, two things block testing this with the real cards directly:
  1. Neither course has been through `index_search.py chunk` yet -- there
     is no ai-sandbox/academic-hub/.index/chunks/{econometrics,math-camp}.json
     on disk, so search_passages() would just silently return [] for both
     (by design -- see its docstring), telling us nothing about ranking.
     Running `chunk` for real would mean paid Gemini embedding calls across
     two courses' full content, which is a cost-guard call this test suite
     should not make unilaterally.
  2. Embedding the real card/chunk text verbatim here would mean committing
     excerpts of real class materials (professor's handwritten notes, a
     recitation's worked solution) into this public repo as test fixtures.

So these tests use synthetic fixtures that are structurally identical to
the real cards (same course names, same file_id/path shape, same
doc_type/source_kind vocabulary) but with short, generic, non-copied text
ONLY describing the general mathematical fact at stake (idempotent
matrices square to themselves) -- not the real notes' own wording,
derivations, or exercise framing. The embeddings are hand-assigned numeric
vectors (clients are mocked; no real embedding/LLM call is made), chosen so
cosine similarity reflects the intended "this chunk is the true grounding
passage" vs. "this chunk is same-course but not the grounding passage"
relationship.
"""
import tempfile
import unittest

from core.indexer.chunk_index import save_chunks
from core.indexer.index_card import recompute_course_entry, save_shard
from core.indexer.index_search import search, search_passages

from tests.core.indexer.test_index_search import _card, _fake_query_client


# A query phrased entirely in econometrics vocabulary. Nothing in the
# wording names math-camp or linear algebra -- the only reason a
# cross-course retrieval should surface the math-camp lemma is that it is
# the actual grounding passage for the "why" behind the econometrics claim.
QUERY = "Why is the OLS residual-maker matrix M = I - P idempotent?"

# Query embedding and the three card/chunk embeddings below are synthetic
# unit-ish vectors chosen purely to control cosine-similarity ranking in
# the mocked embed_content() call -- they carry no semantic meaning beyond
# "aligned with the query" (axis 0) vs. "not" (axis 1/2).
QUERY_EMBEDDING = [1.0, 0.0, 0.0]

# math-camp: the real grounding lemma (idempotent matrices), most aligned.
MATH_CAMP_LEMMA_EMBEDDING = [0.98, 0.0, 0.2]

# econometrics: a same-course decoy that mentions OLS/residuals generally
# but is NOT the idempotency lemma itself -- should rank below the
# cross-course lemma despite sharing the econometrics course filter.
ECON_DECOY_EMBEDDING = [0.6, 0.8, 0.0]


def _econometrics_decoy_card(file_id="econ-decoy", **overrides):
    overrides.setdefault("course", "econometrics")
    overrides.setdefault("doc_type", "handwritten_notes")
    overrides.setdefault(
        "summary",
        "Derives the OLS estimator and its residual vector from the normal "
        "equations; states that the residual-maker matrix is idempotent "
        "without proving the general lemma.",
    )
    return _card(file_id, ECON_DECOY_EMBEDDING, **overrides)


def _math_camp_lemma_card(file_id="mathcamp-lemma", **overrides):
    overrides.setdefault("course", "math-camp")
    overrides.setdefault("doc_type", "ta_notes")
    overrides.setdefault(
        "summary",
        "Linear-algebra lemma: a matrix A is idempotent if A^2 = A; works "
        "through the consequence that an idempotent matrix's eigenvalues "
        "are only 0 or 1, and that I minus an idempotent matrix is also "
        "idempotent.",
    )
    return _card(file_id, MATH_CAMP_LEMMA_EMBEDDING, **overrides)


class TestCrossCourseFileLevelSearch(unittest.TestCase):
    """search() over a single --root holding two courses."""

    def test_surfaces_the_math_camp_lemma_above_the_same_course_decoy(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "econometrics", [_econometrics_decoy_card()])
            save_shard(tmp, "math-camp", [_math_camp_lemma_card()])
            recompute_course_entry(tmp, "econometrics")
            recompute_course_entry(tmp, "math-camp")

            results = search([tmp], QUERY, client=_fake_query_client(QUERY_EMBEDDING))

            self.assertGreaterEqual(len(results), 2)
            self.assertEqual(results[0].file_id, "mathcamp-lemma")
            self.assertEqual(results[0].course, "math-camp")
            # The same-course decoy is still returned (not dropped) -- just
            # ranked below the cross-course grounding passage.
            self.assertIn("econ-decoy", [r.file_id for r in results])
            self.assertGreater(results[0].score, next(
                r.score for r in results if r.file_id == "econ-decoy"
            ))

    def test_without_cross_course_root_only_the_decoy_is_available(self):
        # Control: querying a root that never indexed math-camp at all
        # (e.g. an agent invocation that forgot --root math-camp, or a
        # corpus where it genuinely isn't indexed) can only ever return
        # the same-course decoy -- demonstrating why multi-root search
        # specifically matters for this query, not just that ranking works.
        with tempfile.TemporaryDirectory() as tmp:
            save_shard(tmp, "econometrics", [_econometrics_decoy_card()])
            recompute_course_entry(tmp, "econometrics")

            results = search([tmp], QUERY, client=_fake_query_client(QUERY_EMBEDDING))

            self.assertEqual([r.file_id for r in results], ["econ-decoy"])


class TestCrossCoursePassageLevelSearch(unittest.TestCase):
    """search_passages() -- the three-stage funnel agent/rag/rag_agent.py's
    retrieve_passages() ultimately calls. Chunks mirror the real chunk
    schema (chunk_id/file_id/tier/page_range/embedding/content_hash)."""

    def _seed(self, tmp):
        save_shard(tmp, "econometrics", [_econometrics_decoy_card()])
        save_shard(tmp, "math-camp", [_math_camp_lemma_card()])
        recompute_course_entry(tmp, "econometrics")
        recompute_course_entry(tmp, "math-camp")
        save_chunks(tmp, "econometrics", [{
            "chunk_id": "econ-decoy-000", "file_id": "econ-decoy", "chunk_index": 0,
            "tier": "page", "heading_path": None, "problem_label": None,
            "page_range": [1, 1],
            "text": "The OLS residual vector is e = y - X*beta_hat, and the "
                    "residual-maker matrix M = I - X(X'X)^-1 X' is idempotent.",
            "embedding": ECON_DECOY_EMBEDDING, "embedding_model": "m", "content_hash": "h",
        }])
        save_chunks(tmp, "math-camp", [{
            "chunk_id": "mathcamp-lemma-000", "file_id": "mathcamp-lemma", "chunk_index": 0,
            "tier": "page", "heading_path": None, "problem_label": None,
            "page_range": [1, 1],
            "text": "Lemma: if A^2 = A (A is idempotent), then for any vector v, "
                    "A(Av) = Av, and I - A is also idempotent.",
            "embedding": MATH_CAMP_LEMMA_EMBEDDING, "embedding_model": "m", "content_hash": "h",
        }])

    def test_surfaces_the_cross_course_lemma_passage_above_the_decoy_passage(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._seed(tmp)

            results = search_passages(
                [tmp], QUERY, client=_fake_query_client(QUERY_EMBEDDING), file_top_k=5,
            )

            self.assertGreaterEqual(len(results), 2)
            self.assertEqual(results[0].file_id, "mathcamp-lemma")
            self.assertEqual(results[0].course, "math-camp")
            self.assertIn("A^2 = A", results[0].text)
            decoy_result = next(r for r in results if r.file_id == "econ-decoy")
            self.assertGreater(results[0].score, decoy_result.score)

    def test_course_filter_to_econometrics_alone_cannot_find_the_lemma(self):
        # Adversarial control: if a caller (or a future rag_agent change)
        # pins course="econometrics", the cross-course grounding passage is
        # unreachable no matter how the ranking works -- passing roots
        # alone is not sufficient, course must also be left unset or
        # widened. This documents that constraint rather than asserting
        # a bug: it is expected/correct behavior for an explicit course
        # filter to narrow this way.
        with tempfile.TemporaryDirectory() as tmp:
            self._seed(tmp)

            results = search_passages(
                [tmp], QUERY, client=_fake_query_client(QUERY_EMBEDDING),
                course="econometrics", file_top_k=5,
            )

            self.assertEqual([r.file_id for r in results], ["econ-decoy"])


if __name__ == "__main__":
    unittest.main()
