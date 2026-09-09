# Research RAG Agent Design (Brainstorm)

This spec outlines a dedicated Research RAG Agent designed to synthesize information across the `research/` corpus, distinct from the Tutoring Agent. 

## 1. Problem & goals

The existing RAG tutor is optimized for conversational pedagogy, defensive anti-hallucination guardrails, and explaining individual concepts. A research agent needs a peer-expert persona and synthesis capabilities optimized for broader literature review, gap analysis, and multi-article synthesis.

**Primary Goals:**
*   **Literature Review Synthesis:** Grouping findings across 5-10 articles by theme, methodology, or result.
*   **Gap Analysis:** Identifying research questions not addressed in the retrieved corpus.
*   **Methodological Support:** Comparing and contrasting different research approaches across multiple papers.

## 2. Cost & Model Selection

*   **Retrieval:** Reuses `gemini-embedding-001` (same as indexer).
*   **Generation:** Recommended `gemini-2.0-flash` or `gemini-1.5-pro`. Given the task involves synthesizing high-density journal PDFs, larger context handling is prioritized over minimal latency.
*   **Cost Estimate:** Synthesis of a 10-article lit review is projected at ~$0.02–$0.05 per query—negligible for high-value research support.

## 3. Proposed Architecture

New module `research_rag/research_agent.py`, importing from `common/` and `indexer/`.

```python
@dataclass
class ResearchTask:
    task_type: str # "summary" | "lit_review" | "gap_analysis"
    query: str
    target_topics: list[str]

def synthesize_research(
    task: ResearchTask, 
    retrieved_passages: list[PassageResult]
) -> str:
    # Logic to route to specialized prompt templates based on task_type
    pass
```

## 4. Key Workflow Components (Comparison)

| Feature | Tutoring Agent | Research Agent |
| :--- | :--- | :--- |
| **Retrieval** | High precision (top 3-5) | High recall (top 20+) |
| **Diversification** | By file | By publication year/theme/method |
| **Prompt Focus** | "Explain this concept" | "Compare these findings" |
| **Output** | Conversational Q&A | Structured Technical Markdown |

## 5. Potential "Superpower" Features

*   **Citation-Matrix:** Automatically generate a table mapping retrieved passages against themes/methodologies.
*   **Graph-Connector:** Querying the `retag` tag-graph to suggest articles in the corpus that are contextually related even if they don't share keyword similarity.
*   **Multi-Agent Mode:** A "Brainstorming" sub-agent that asks *you* probing questions about potential research directions based on the identified gaps.

## 6. Next Steps

1.  **Skeleton Implementation:** Create `research_rag/` with basic `research_agent.py`.
2.  **Prompt Engineering:** Draft specialized prompt templates for "Summary" and "Literature Review" tasks.
3.  **Validation:** Test against the existing indexed journal articles corpus.
