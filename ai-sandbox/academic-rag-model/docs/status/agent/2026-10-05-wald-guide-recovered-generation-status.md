# Wald/LR/LM study guide: recovered generation recipe (status)

Date: 2026-10-05 · Package: agent (study_guide, planned) · Kind: provenance record

This documents how the first Wald / likelihood ratio / Lagrange multiplier study guide
(`academic_notes/econometrics/summaries/wald_lm_lr_tests.md`, vault commit `1c002b3`,
2026-10-03) was actually produced, so the process can be reproduced and replaced by the
reusable pipeline in `docs/superpowers/specs/agent/2026-10-05-study-guide-pipeline-design.md`.

## Provenance

The guide was **not** produced by a repository tool. It came from an ad-hoc Python script
run by a Codex session on 2026-10-03 (about 12:02 local), iterated 32 times. Nothing in the
repository docs, git messages, or any Claude session mentions the script. The only record is
the Codex transcript:

`~/.codex/sessions/2026/10/03/rollout-2026-10-03T12-02-39-01a10280-d322-71a3-b711-fde0593e794f.jsonl`

(The final iteration is the last script in that session that contains the
"Source-reference discrepancy" block.) The script wrote the draft to a scratch folder; it
was then moved into the notes vault. A Codex session at 12:53 (commit `80708a9`
`feat(rag): persist markdown summaries in course notes`) made the tutor's Markdown summaries
land in `academic_notes/<course>/summaries/`. Later work added the frontmatter fields
(`llm_generated`, `content_kind`, `generated_by`, and the `indexer_source_refs` back-fill);
this record does not establish exactly which session did which.

**Reliability of the copy below.** The transcript stores the script as an escaped string and
decoded the section sign, dashes and curly quotes to U+FFFD. The script was rebuilt by JSON
decoding and the lost characters were restored by best guess (`§`, en dash, curly quotes).
The result parses as valid Python (`ast.parse`) but was **not re-run**. Prompts are exact
apart from those characters; local absolute paths were replaced by placeholders.

## The recipe

Models: embeddings `gemini-embedding-001` (retrieval only); text synthesis
`gemini-3.1-flash-lite` (`rag_agent.TUTOR_MODEL`, temperature 0.2) through the paid key.
There was no separate extraction or drafting stage: the synthesis model wrote the guide text.

For each of six specs (title, textbook file name, query, section labels, instruction):

1. **Retrieve** with `search_passages(roots, f"Econometrics textbook: {query}. {instruction}",
   client, course="econometrics", top_k=180, file_top_k=80, doc_type="textbook")`.
2. **Filter** to passages from the named textbook file whose rendered `citation` string
   contains any of the section labels (plain substring test). For Cameron's likelihood ratio
   spec, drop citations containing `7.3.5`.
3. **Cap** at the first 12 passages in similarity order. Fail if there are none.
4. **Synthesize** with `rag_agent._generate_answer(question, [], chosen, client)`, where
   `question = f"{title}. {instruction} Use only these excerpts. Cite each substantive claim
   by its exact source label. State plainly where the excerpts do not support an answer."`
   `_generate_answer` wraps the excerpts (`[citation]\ntext`) in the tutor's Q&A prompt
   (`_ANSWER_PROMPT_TEMPLATE`: "tutoring a student using ONLY the excerpts below ... answer
   clearly and thoroughly, the way a good TA would ... cite it inline").
5. **Comparison section:** the first 3 passages from each of five specs (Cameron 7.2, 7.3,
   7.3.5, Hansen 9.10/9.11, Hansen 9.17), de-duplicated by chunk id, synthesized with a
   fixed comparison instruction that also states the known Hansen likelihood ratio gap.
6. **Assemble** a "Source-reference discrepancy" note (static text: the syllabus cites
   Hansen 9.9/9.11/9.16 but the converted chapter has t-ratios, homoskedastic Wald,
   Hausman there), then each section followed by a "Retrieved sources" list, then the
   comparison. Frontmatter named the model "Gemini 3.1 Flash Lite".

## Observed properties and limits (inputs to the new design)

- **No chunk ids at generation time.** Only citation labels and paths were recorded; the
  `indexer_source_refs` were back-filled afterwards, so reproduction relies on the same index.
- **Label filtering is a substring test on the last heading only.** Chunks under a numbered
  parent but with an unnumbered own heading (for example "Likelihood Ratio Test, p. 257")
  carry no section number in `citation`, and a label such as `9.1` would also match `9.10`.
  Matching against the whole `heading_path` with dot-boundary prefixes would be more faithful.
- **Depth is capped by retrieval:** at most 12 passages per section, ranked by similarity
  to a query that includes the instruction, with no guarantee the whole section is covered.
- **The synthesis prompt is the tutor's Q&A prompt,** not a study-guide prompt, so section
  length and structure are whatever the tutor template yields.
- **Hard-coded domain knowledge:** the Hansen likelihood ratio "reference check" spec and
  the discrepancy note were authored by hand after inspecting the chapter headings.
- **Hansen likelihood ratio coverage:** the guide says Hansen has no likelihood ratio
  section, which is true of the Chapter 9 sections the syllabus names; Hansen section 5.13
  ("Likelihood Ratio Test") exists and was never retrieved.
- **Model choice was inherited, not tested** for long-form synthesis: `TUTOR_MODEL` was set
  after a side-by-side on short tutoring answers.

## Recovered script

```python
from pathlib import Path
from core.env.gemini_utils import load_dotenv_override, get_gemini_client
from core.indexer.index_search import search_passages
from agent.rag.rag_agent import _generate_answer, TUTOR_MODEL

load_dotenv_override()
client = get_gemini_client("PAID_GEMINI_KEY")
if client is None:
    raise SystemExit(1)
roots = [r"<ACADEMIC_HUB_ROOT>"]
specs = [
    ("Cameron & Trivedi Section 7.2 — Wald test", "Cameron_Microeconometrics_Methods_and_Applications_2013.rag.md", "Wald test linear nonlinear hypotheses covariance chi-square invariance", ("7.2",), "Explain the Wald test: hypotheses, unrestricted estimation, statistic and covariance, asymptotic distribution, decision rule, examples, and invariance cautions."),
    ("Cameron & Trivedi Section 7.3 — likelihood ratio test", "Cameron_Microeconometrics_Methods_and_Applications_2013.rag.md", "likelihood ratio test restricted unrestricted maximum likelihood chi-square", ("7.3.1", "7.3.2", "7.3.3", "7.3.4"), "Explain the likelihood ratio test: restricted/unrestricted MLE, exact statistic if given, degrees of freedom and asymptotic distribution, decision rule, assumptions, examples, and choice versus Wald/LM."),
    ("Cameron & Trivedi Section 7.3.5 — Lagrange multiplier test", "Cameron_Microeconometrics_Methods_and_Applications_2013.rag.md", "Lagrange multiplier score test restricted estimator score statistic information chi-square", ("7.3.1", "7.3.3", "7.3.5"), "Explain the LM/score test: null-restricted estimator, score and scaling, statistic and asymptotic reference distribution, decision rule, computation, examples, and comparison with LR/Wald."),
    ("Hansen Section 9.10 and 9.11 — Wald tests", "Hansen_ECONOMETRICS_2022.rag.md", "Wald tests general and homoskedastic statistics covariance chi-square F", ("9.10", "9.11"), "Explain Hansen's general and homoskedastic Wald tests: hypotheses, statistic, covariance, distribution and degrees of freedom, critical-value/p-value rule, assumptions and interpretation."),
    ("Hansen Section 9.11 reference check — likelihood ratio test", "Hansen_ECONOMETRICS_2022.rag.md", "Section 9.11 likelihood ratio test compare likelihood statistic restricted unrestricted", ("9.11",), "The course syllabus cites section 9.11 for a likelihood ratio test. Explain what the supplied section 9.11 excerpt actually covers and whether it provides a likelihood ratio test. Do not substitute another test or fill gaps with general knowledge; cite the evidence and state what is unavailable."),
    ("Hansen Section 9.17 — score (Lagrange multiplier) test", "Hansen_ECONOMETRICS_2022.rag.md", "score test restricted estimates gradient Hessian statistic chi-square normal regression", ("9.17",), "Explain the score/LM test: restricted estimation, score and information/Hessian scaling, statistic, decision rule, relation to homoskedastic Wald/F in normal regression, and computational advantage. Cite each point and identify any details not in the excerpts."),
]
answers = {}
used = {}
for title, filename, query, section_ids, prompt in specs:
    query_text = f"Econometrics textbook: {query}. {prompt}"
    results = search_passages(roots, query_text, client, course="econometrics", top_k=180, file_top_k=80, doc_type="textbook")
    book = [p for p in results if Path(p.path).name == filename]
    matching = [p for p in book if any(section_id in p.citation for section_id in section_ids)]
    # Prevent Cameron's LR subsection from being flooded by the adjacent LM subsection.
    if "Cameron" in filename and "likelihood ratio" in query.lower():
        matching = [p for p in matching if "7.3.5" not in p.citation]
    chosen = matching[:12]
    if not chosen:
        raise RuntimeError(f"No section-matched passages for {title}; book hits={len(book)}")
    answer = _generate_answer(f"{title}. {prompt} Use only these excerpts. Cite each substantive claim by its exact source label. State plainly where the excerpts do not support an answer.", [], chosen, client)
    answers[title] = answer
    used[title] = chosen
    print(f"Completed: {title}; passages={len(chosen)}; labels={[p.citation for p in chosen]}", flush=True)

compare_passages = []
seen = set()
for key in (specs[0][0], specs[1][0], specs[2][0], specs[3][0], specs[5][0]):
    for p in used[key][:3]:
        if p.chunk_id not in seen:
            compare_passages.append(p)
            seen.add(p.chunk_id)
comparison = _generate_answer(
    "Compare the Wald, likelihood ratio, and Lagrange multiplier/score tests using only these selected Cameron & Trivedi and Hansen passages. Explain which estimates each requires, what each statistic measures, shared asymptotic relationships where stated, computation choices, and supported cautions. The retrieved Hansen passages do not supply a likelihood ratio section; make that limitation explicit. Cite every substantive comparison and do not fill gaps from outside knowledge.",
    [], compare_passages, client)

def format_section(title, answer, passages):
    source_lines = [f"- [{p.citation}] `{p.path}`" for p in passages]
    return f"## {title}\n\n{answer}\n\n**Retrieved sources**\n\n" + "\n".join(source_lines)

blocks = []
blocks.append("## Source-reference discrepancy\n\nThe course syllabus points to Hansen §§9.9, 9.11, and 9.16 for these tests. In the converted Hansen chapter, the headings identify §9.9 as *t*-ratios and the abuse of testing, §9.10 as Wald tests, §9.11 as homoskedastic Wald tests, §9.16 as Hausman tests, and §9.17 as score tests. Chapter 9 contains no section headed likelihood ratio test; the only matching phrase found in the chapter describes a criterion-based statistic as ‘likelihood-ratio-like.’ The Hansen entries below therefore follow the actual chapter headings and preserve the syllabus mismatch rather than attributing unrelated sections to these tests.")
for spec in specs:
    title = spec[0]
    blocks.append(format_section(title, answers[title], used[title]))
blocks.append(format_section("Comparing and choosing among the three tests", comparison, compare_passages))
header = """---
title: Wald, Lagrange Multiplier, and Likelihood Ratio Tests
course: ECON G6411 Econometrics
source_basis:
  - Cameron and Trivedi, Microeconometrics (2002), sections 7.2, 7.3, 7.3.5
  - Hansen, Econometrics (2022), syllabus references 9.9, 9.11, 9.16; matching chapter sections 9.10, 9.11, 9.17
created_with: academic-rag-model agent/rag/rag_agent.py and core/indexer/index_search.py
model: Gemini 3.1 Flash Lite
---

# Wald, Lagrange Multiplier, and Likelihood Ratio Tests

Each explanation below was generated by the RAG tutor from retrieved passages filtered to the named textbook file and section labels. Retrieved passage citations are listed below each answer. The reference discrepancy in Hansen is flagged explicitly.

"""
out = Path(r"<SCRATCH_DIR>/wald_lm_lr_tests.md")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(header + "\n\n---\n\n".join(blocks) + "\n", encoding="utf-8")
print(f"Wrote {out}; model={TUTOR_MODEL}; chars={out.stat().st_size}")
```
