# Transferability follow-up brainstorm handoff (for a codex research brainstorming session)

Written 2026-11-06 by the Claude session that reorganized the independent-research notes. This is a brief for a brainstorming session, not a build plan. Nothing here asks for code, pipelines or data downloads. Confirm scope with Aaron at the start.

## Why this exists

Aaron sent Gemini an RCT replication and transportability idea note. Gemini replied with a long technical map (DML, LIML, JIVE, hierarchical Bayes, Bai-Ng factor models). Aaron then asked three follow-up questions. The saved transcript ends with those questions repeated back and **no answer**. This session answers them.

## Read first (all on `main`)

Folder: `ai-sandbox/research/independent-research/notes/03_rct-transportability/`

| File | Why |
| --- | --- |
| `RCT Replication and Transportability - Gemini Brainstorm.md` | The idea note, Gemini's reply, and the three unanswered questions (lines 181-185). |
| `Brainstorming Transcript - Transferability of Crisis Interventions.md` | Earlier session (Oct 14-20) that first laid out RQ 3 and Sprint 2. Aaron's own views are in his turns. |
| `Cross-Group Connections.md` | Where the same ideas already appear in other notes; lists the open items. |

Then, as needed: `projects/empirical_sprints/sprint_02_geospatial_evaluation_matcher.md`, `01_compound-shocks-panel/review-gate/Review Gate - Data Audit Review.md` (what the panel does and does not contain), and the 3R plan in `00_overview-and-strategy/`.

## The three questions (Aaron's wording)

1. "First I wanted some frank analysis / critique on whether these ideas make any sense together, and whether there is sufficient panel data available from RCTs to support it."
2. "Next I'm curious if there is enough data from RCTs beyond just progresa or other well known interventions, especially in a complex conflict or natural disaster environment."
3. "Finally I'm curious how well these map to the concept of transfer learning / causal transportability for conflict / disaster settings."

## What the notes already establish (do not re-derive)

- The idea has four steps: replicate a geocoded RCT; add locality covariates and proxy outcomes (night lights, NDVI, later displacement); test whether proxies detect the effect without panel survey data; project impact to new places by matching covariates and proxies. A companion idea pools several RCTs in a hierarchical Bayes model with leave-one-site-out checks.
- Aaron's stated view in the earlier transcript: naive RCT extrapolation is already well studied; novelty is more likely in conflict and disaster contexts, delivery rails, and practitioner usefulness. Success is same sign and similar magnitude, not statistical elegance. He warned against models "too dense for anyone to actually use" and against locking in methods before touching data.
- The compound-shocks panel has no geocoded RCT sites and no cash-transfer locations. Its dense columns are rainfall and conflict; prices and displacement are sparse.
- Project 03 (3R plan) uses "transferability" in the policy sense; this brainstorm is the statistical sense. RQ 3 is the bridge.

## What the session should produce

A new note in `03_rct-transportability/`, for example `Follow-up - Data Availability and Transportability Critique.md`, with:

1. **Critique** (question 1): do the four steps and the pooling idea hang together; which assumptions carry the load (overlap, conditional independence of effect modifiers, proxy validity); where Gemini's reply over-reaches. Treat the "LIML is essential" claim as a hypothesis to test, not a fact.
2. **Data availability** (questions 1 and 2): which RCTs with geocoded sites and usable panel or repeated outcome data exist beyond PROGRESA and GiveDirectly, with a focus on conflict, displacement and disaster settings. Give counts or a short list per source (3ie, J-PAL, AEA Registry, World Bank and IPA data archives), and say what is public versus restricted. If counts cannot be established, say so.
3. **Mapping** (question 3): how the design corresponds to transfer learning and causal transportability (selection diagrams, covariate-shift and domain-adaptation framings, transport formulas). Say where the correspondence breaks, especially for conflict and disaster settings where the target context may sit outside the source support.
4. **Verdict and go/no-go test**: a green / yellow / red check, in the style of `projects/empirical_sprints/empirical_sprints_overview.md`, that could be run cheaply before any estimator is built. Name the likely home: standalone methods paper (Direction III), a section of Project 03, or a later chapter. Aaron decides; give a recommendation.

Keep it a brainstorm record: Aaron's prompts, the answers, and a short synthesis. Aim for the length of a normal note, not another 500 lines.

## Ground rules

- **Verify, don't recite.** Every citation (Egger et al. 2022, Meager 2019, Athey et al. 2019, Bai and Ng 2008, and any new ones) must be checked against the source before it is relied on. Mark anything unchecked "unverified". The earlier Gemini output contains unverified citations.
- **Evidence over assertion** on data availability. Link the registry entries or datasets you count.
- **No code, no downloads, no changes to existing notes.** Add one new file. Updating `03_rct-transportability/Cross-Group Connections.md` open item 1 afterwards is fine.
- **Do not decide for Aaron:** research question choice (the compound-shocks Options A/B/C), Sudan scope, or ACLED vs UCDP GED are open and separate.
- Follow the repo's worktree and landing procedure (`docs/WORKTREE_WORKFLOW.md`, `docs/WORKTREE_LANDING.md`): a `codex/<task>` branch and worktree, stage explicit paths, land through `tools.land_branch`.
