"""
generate_quiz_guide.py
Generates an extensive, exam-focused study guide for hypothesis testing in econometrics,
grounded in the course materials from the last two weeks (transcribed Excalidraw notes,
question sidecars, professor lecture notes, recitations, and textbooks).

Specifically tailored for quiz preparation involving parameter-based test statistic
calculations, linear restrictions, the Delta method, and exam problems like Question 3.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.env.gemini_utils import call_with_retries, get_gemini_client, load_dotenv_override
from core.indexer.index_search import search_passages
from agent.rag.rag_agent import TUTOR_MODEL

# Corpus root
HUB_ROOT = Path(r"C:\Users\theaa\ai-sandbox-master\ai-sandbox\academic-hub").resolve()

# Output destination in notes vault
OUTPUT_DIR = HUB_ROOT / "academic_notes" / "econometrics" / "summaries"
OUTPUT_FILE = OUTPUT_DIR / "wald_hypothesis_testing_quiz_prep.enhanced.md"

SECTION_SPECS = [
    {
        "title": "Theoretical Foundations: Wald Tests for Linear & Non-Linear Hypotheses",
        "query": "Wald test linear nonlinear restrictions matrix R beta covariance chi-square degrees of freedom",
        "instruction": (
            "Explain the theoretical foundations of the Wald test for both linear restrictions "
            "(R' beta = r) and general non-linear restrictions (r(beta) = 0). Detail the quadratic form, "
            "asymptotic distribution, degrees of freedom, the role of the robust asymptotic covariance matrix "
            "V_hat = (1/n) V_beta, and its relationship to the t-test when testing a single restriction."
        ),
        "prefer_keywords": ["Wald", "9.10", "7.2", "restriction"],
    },
    {
        "title": "The Delta Method, Asymptotic Variance, and Non-Linear Confidence Intervals",
        "query": "Delta method nonlinear restrictions gradient Taylor expansion asymptotic variance confidence interval",
        "instruction": (
            "Explain the Delta method for nonlinear functions of estimated parameters theta = g(beta). "
            "Show the Taylor series expansion, the gradient vector G = nabla_beta g, the asymptotic variance "
            "formula Var_hat(theta_hat) = G' V_hat G, standard error computation, construction of 95% Wald confidence "
            "intervals, and the known non-invariance pathology of the Wald test for nonlinear parameterizations."
        ),
        "prefer_keywords": ["Delta", "gradient", "Taylor", "invariance"],
    },
    {
        "title": "The Testing Trinity: Comparative Analysis of Wald, Likelihood Ratio, and LM (Score) Tests",
        "query": "Wald likelihood ratio Lagrange multiplier score test trinity comparison inequality restricted unrestricted",
        "instruction": (
            "Compare the classical testing trinity: Wald, Likelihood Ratio (LR), and Lagrange Multiplier (LM/score) tests. "
            "Explain what estimates each requires (unrestricted vs restricted), what each statistic measures geometrically "
            "and analytically, their shared asymptotic chi-square reference distribution under H_0, the numerical inequality "
            "W >= LR >= LM in the classical normal linear regression model, and how to choose among them in applied exams."
        ),
        "prefer_keywords": ["Lagrange", "score", "Likelihood", "trinity", "inequality"],
    },
    {
        "title": "Exam-Style Problem Walkthrough 1: Wage Equation Parameter Estimation and Test Statistics",
        "query": "log wage equation education experience return maximum confidence interval Wald test",
        "instruction": (
            "Provide a complete, rigorous, step-by-step walkthrough of the exam question from previous years:\n"
            "Estimation of a wage equation with n = 1000 observations:\n"
            "log(wage)^ = 0.118 EDU + 0.016 EXP - 0.022 (EXP^2 / 100) + 0.947\n"
            "with robust standard errors (0.008), (0.006), (0.012), (0.157) which are square roots of V_hat = (1/n) V_beta.\n"
            "Let V_hat_ij be the (i, j) entry of V_hat.\n"
            "Solve each part with exact analytical derivations, intermediate arithmetic, and final formulas:\n"
            "Part i: Let theta_1 = 100 beta_1. Find theta_1^ and its standard error.\n"
            "Part ii: Let theta_2 = 100 beta_2 + 20 beta_3 be the percentage return to 10 years of experience. Construct a Wald test for H_0: theta_2 = 1.\n"
            "Part iii: Let theta_3 be the level of EXP that maximizes expected log wage. Construct a 95% confidence interval for theta_3 using the Delta method."
        ),
        "prefer_keywords": ["wage", "experience", "0.016", "0.118", "Delta"],
    },
    {
        "title": "Exam-Style Problem Walkthrough 2: Joint Linear Hypotheses with 2x2 Matrix Inversion",
        "query": "joint linear hypothesis Wald test 2 restrictions matrix inversion chi-square critical value",
        "instruction": (
            "Provide a step-by-step worked example of testing a joint hypothesis with q = 2 restrictions (e.g. H_0: beta_1 = 0 and beta_2 + beta_3 = 0) "
            "from given parameter estimates and a 2x2 covariance submatrix. Show the explicit setup of R', discrepancy vector, matrix inversion, "
            "quadratic form calculation, degrees of freedom, and critical value decision rule at alpha = 0.05."
        ),
        "prefer_keywords": ["joint", "restrictions", "inversion", "matrix"],
    },
    {
        "title": "Exam-Style Problem Walkthrough 3: Testing Non-Linear Ratio Restrictions and Invariance Sensitivity",
        "query": "ratio restriction Wald test invariance non-linear Gregory Veall Delta method",
        "instruction": (
            "Walk through an exam problem testing a nonlinear ratio restriction H_0: beta_1 / beta_2 = 1 versus its linear counterpart "
            "H_0: beta_1 - beta_2 = 0. Derive the gradient, calculate both test statistics from sample parameters, and explain why the Wald "
            "statistic is sensitive to the formulation while the Likelihood Ratio test is invariant."
        ),
        "prefer_keywords": ["ratio", "invariance", "Gregory", "Veall"],
    },
    {
        "title": "Quiz Quick-Reference Cheatsheet: Formulas, Gradients, and Decision Rules",
        "query": "Wald test statistic formula cheatsheet chi-square critical values delta method variance",
        "instruction": (
            "Create a compact, high-yield summary table and cheatsheet for fast quiz recall: "
            "1. Core test statistic formulas for Wald, t, LR, and LM tests.\n"
            "2. Variance expansion rules for scalar, linear combination (2 variables), and general matrix forms.\n"
            "3. Common Delta method gradient formulas (ratios, products, quadratic peaks).\n"
            "4. Asymptotic reference distributions, degrees of freedom rules, and critical values (e.g. chi-square at 1, 2, 3 df for alpha=0.05 and 0.01; normal 1.96, 2.576).\n"
            "5. Common student traps and pitfalls to avoid during the quiz."
        ),
        "prefer_keywords": ["cheatsheet", "formula", "critical value", "pitfalls"],
    },
]


def retrieve_grounding_passages(client, spec: dict, top_k: int = 15) -> list:
    query = f"Econometrics: {spec['query']}. {spec['instruction']}"
    results = search_passages([str(HUB_ROOT)], query, client, course="econometrics", top_k=top_k)
    return results


def synthesize_section(client, model: str, title: str, instruction: str, passages: list) -> str:
    excerpts_text = "\n\n".join(f"[{p.citation}]\n{p.text}" for p in passages)
    prompt = f"""You are an expert econometrics professor preparing a comprehensive, highly thorough, mathematically rigorous study guide for a graduate student preparing for an upcoming exam/quiz on hypothesis testing.

Use the provided course excerpts (which include textbook chapters, class lecture notes from 2026, question sidecars, and recitations) to thoroughly explain and answer the topic below.

Topic: {title}

Instructions:
{instruction}

Formatting and Quality Requirements:
1. Ensure all mathematics is rendered cleanly using standard LaTeX ($...$ for inline, $$...$$ for display math).
2. For worked problems, show every step of algebraic simplification and numerical arithmetic explicitly. State the null and alternative hypotheses, the test statistic formula, degrees of freedom, distribution under H_0, and rejection decision rule.
3. When referencing ideas or concepts from the excerpts, cite them inline using their citation tag (e.g. `[§9.10 WALD TESTS, p. 268]` or `[Econometrics 2026-09-30]`).
4. Ground the explanation in the provided excerpts.

Excerpts from course materials:
{excerpts_text}

Provide the section text in clean GitHub markdown (no surrounding ```markdown fence):"""

    response = call_with_retries(lambda: client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": 0.2},
    ))
    return (response.text or "").strip()


def run_pipeline():
    load_dotenv_override()
    client = get_gemini_client("PAID_GEMINI_KEY")
    if client is None:
        print("ERROR: PAID_GEMINI_KEY is not available.", file=sys.stderr)
        sys.exit(1)

    print(f"Generating quiz study guide into {OUTPUT_FILE}...")
    all_refs = []
    seen_chunks = set()
    section_blocks = []

    model = "gemini-3.8-flash"  # high-capability tier for math reasoning and long synthesis

    for i, spec in enumerate(SECTION_SPECS, 1):
        print(f"[{i}/{len(SECTION_SPECS)}] Retrieving for: {spec['title']}...")
        passages = retrieve_grounding_passages(client, spec, top_k=12)
        print(f"    Retrieved {len(passages)} passages.")

        # Track passages for frontmatter
        for p in passages:
            if p.chunk_id not in seen_chunks:
                seen_chunks.add(p.chunk_id)
                all_refs.append({
                    "root": str(HUB_ROOT),
                    "path": p.path,
                    "file_id": p.file_id,
                    "chunk_id": p.chunk_id,
                    "citation": p.citation,
                })

        print(f"    Synthesizing section text with {model}...")
        body = synthesize_section(client, model, spec["title"], spec["instruction"], passages)

        # Source list for section
        sources_md = "\n".join(f"- [{p.citation}] `{p.path}`" for p in passages[:8])
        section_md = f"## {spec['title']}\n\n{body}\n\n**Retrieved course sources:**\n\n{sources_md}"
        section_blocks.append(section_md)

    frontmatter = {
        "title": "Wald, LM, and LR Hypothesis Testing: Exam & Quiz Preparation Guide",
        "course": "ECON G6411 Econometrics",
        "llm_generated": True,
        "content_kind": "quiz_preparation_study_guide",
        "generated_by": "academic-rag-model/agent/rag/generate_quiz_guide.py",
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "topics": [s["title"] for s in SECTION_SPECS],
        "target_assessment": "Econometrics Quiz (Hypothesis Testing & Test Statistic Calculations)",
        "source_basis": [
            "Econometrics Lecture Notes 2026-09-30 (Wald Test) and 2026-10-05 (Hypothesis Testing Trinity)",
            "Question Resolver Sidecars (2026-09-30 & 2026-10-05)",
            "Professor Lecture Notes (092126, 092826, 093026)",
            "Recitation 5 (Delta Method & Nonlinear Wald Tests)",
            "Cameron & Trivedi, Microeconometrics (2013), Chapter 7",
            "Hansen, Econometrics (2022), Chapter 9",
        ],
        "indexer_source_refs": all_refs,
    }

    frontmatter_yaml = "---\n" + json.dumps(frontmatter, indent=2) + "\n---\n\n"
    # Convert json dump in frontmatter to yaml-compatible text
    yaml_header = f"""---
title: "Wald, LM, and LR Hypothesis Testing: Exam & Quiz Preparation Guide"
course: "ECON G6411 Econometrics"
llm_generated: true
content_kind: "quiz_preparation_study_guide"
generated_by: "academic-rag-model/agent/rag/generate_quiz_guide.py"
model: "{model}"
generated_at: "{datetime.now(timezone.utc).isoformat()}"
target_assessment: "Econometrics Quiz (Hypothesis Testing & Parameter Calculations)"
indexer_source_refs: {json.dumps(all_refs)}
---

# Wald, LM, and LR Hypothesis Testing: Exam & Quiz Preparation Guide

*Comprehensive study guide geared specifically for quiz preparation on parameter-based test statistic calculations, linear and nonlinear restrictions, the Delta method, and testing trinity comparisons. Synthesized directly from your course materials (transcribed lecture notes, resolved formula questions, recitations, professor slides, and textbooks).*

---

"""

    full_content = yaml_header + "\n\n---\n\n".join(section_blocks) + "\n"

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(full_content, encoding="utf-8")
    print(f"\nSuccessfully wrote expanded study guide to:\n  {OUTPUT_FILE}")
    print(f"Total size: {OUTPUT_FILE.stat().st_size:,} bytes")


if __name__ == "__main__":
    run_pipeline()
