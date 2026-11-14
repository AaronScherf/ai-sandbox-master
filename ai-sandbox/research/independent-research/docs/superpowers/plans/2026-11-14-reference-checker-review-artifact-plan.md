# Reference checker: review artifact and gate placement (plan)

Date: 2026-11-14. Author: Claude (architecture). Design only; nothing built, no code changed. Builds on `2026-11-14-reference-checker-identity-tiers-decision - v2.md` (three tiers plus the linking pass) and `... claude-review-handoff - v5.md`.

Evidence labels: **read** = Claude read the file this session; **assumed** = inferred, needs the builder to confirm.

## 1. Where the checker sits (gate placement)

Two different surfaces need two different hooks. Do not merge them.

| Surface | What it is | Hook | Basis |
|---|---|---|---|
| **A. Evidence-kind projects** (reprokit) | Cited sources live in `evidence/manifest.yaml` with `identifier`, `title`, `year`, `verification_status`; `synthesis.md` cites by `[@id]`. | `reprokit verify-sources`, the network step that is already specified as separate from `validate` and "never in the 30-second test path". It should set `verification_status` from the checker. `validate` already fails if a cited entry is not `source-verified`. | read: `specs/2026-11-06-reprokit-evidence-kind-design.md` sections 4 and 6. Whether `verify-sources` has been built beyond DOI/OpenAlex resolution: **assumed**, not checked. |
| **B. Free-form research notes** (Gemini novelty notes, the Literature Gap Memo, handoffs) | Markdown with inline author-year citations and, sometimes, a reference list. No manifest. | The checker's own CLI, run by the agent that wrote the note and again by the integrator before a note is tagged `[source-verified]` or merged into the research tree. Not in CI at first. | assumed: no existing gate for these notes was found; the only existing control is the reviewer's judgment (which missed 3 `[source-verified]` wrong DOIs). |

Consequence for surface A: the manifest already carries a `title`, so the linking pass is unnecessary there; compare the manifest title with the registry title. Rows with no manifest title are PLAUSIBLE. The linking pass (tiers decision v2) is for surface B.

Rule for both: **only CONFIRMED may become `source-verified` without a human.** PLAUSIBLE, REVIEW, AMBIGUOUS, WRONG_WORK and NOT_FOUND cannot.

## 2. What goes to the review artifact

| Row state | Goes to review? | Reviewer's question |
|---|---|---|
| CONFIRMED | no (logged only) | none |
| PLAUSIBLE (no title anywhere) | yes | Is this the paper the note means? |
| REVIEW (title < 0.5 or year differs) | yes | Same work with a different title or year, or a wrong DOI? |
| AMBIGUOUS (one surname overlap) | yes | Same question |
| WRONG_WORK, NOT_FOUND | no review needed; report as defects to the author | none; these need a fix in the note, not a decision |
| UNCHECKED (URL entries, no identifier) | listed once per note, not per row | Is a registry record expected? |

Queue size is the main design risk: most free-form notes use author-year citations, so PLAUSIBLE will dominate. Two mitigations are already decided (the linking pass; sort order below). A third is open (section 6).

## 3. What the reviewer sees, per row

Everything needed to decide without opening another tab:

1. The cited text exactly as in the note, with the note name and line number (a link back).
2. The registry record the identifier points to: title, all authors, year, venue, volume, pages.
3. The row's tier and the reason it is in the queue (for example "no title in note; first author and year agree" or "title score 0.31").
4. For PLAUSIBLE rows with several candidate list entries: the candidates and their title scores.
5. The claim sentence the citation supports, when it can be extracted without an LLM (the same table row or sentence). Shown as context, not verified.

No full-text excerpts and no abstract are stored (rights; the public repo). The artifact shows the registry's own metadata only.

Order of the queue: REVIEW first (likeliest wrong), then AMBIGUOUS, then PLAUSIBLE grouped by note so one note's rows are decided together.

## 4. Decisions and what each one does

Follows the repo convention in `academic-rag-model/CLAUDE.md` (read): a checkbox page with decisions in the artifact's `db` collection, applied by the pipeline's own resolve and reject functions. The ledger pattern to copy is `core/indexer/offering_links.py` (read: `review.json`, `resolve_pending`, `reject_pending`, a dismissals file so a resolved item does not return).

| Decision | Meaning | Effect on apply |
|---|---|---|
| **Same work** | The registry record is the paper the note means. | Row recorded as human-confirmed; may become `source-verified`. Dismissal stored so the same (note, identifier, normalized citation) is not queued again. |
| **Wrong work** | The identifier points to a different paper. | Row reported as a defect; stays out of `source-verified`; the author is told to fix the note. Never edits the note itself. |
| **Can't tell** | The reviewer cannot judge from the shown metadata. | Stays unresolved; remains in the queue next run; counts toward an "unresolved" total. |
| **Not a citation** | Extraction error (a claim cell, a quoted correction). | Row dropped and recorded as an extractor false positive, which feeds the test fixtures. |

The apply step reads decisions from the artifact `db` and calls the ledger functions; the artifact itself never writes to the notes. Humans decide; code applies. Aaron's "Can't tell" and "Wrong work" choices are never silently turned into passes.

## 5. Ledger and storage

- **Ledger file** (assumed location): `.reference_checker_review/review.json` and `dismissals.json` beside the checker's other ignored outputs, mirroring `offering_links`. Gitignored. It holds metadata only: note path, line, cited text, identifier, tier, decision, timestamp.
- **Row key:** hash of (note path, identifier, normalized citation text). Re-running the checker must not resurrect a dismissed row, and must re-queue a row whose citation text changed.
- **Review envelope:** `offering_links` imports `core.indexer.review_envelope.is_unresolved`. Reuse it if its shape fits; whether it does is **assumed**, not checked.
- **Privacy:** the checker already sends only DOIs and up to 200 characters of citation text to registries. The artifact adds nothing outbound beyond hosting its page; the page contains cited text and registry metadata, no source note bodies.

## 6. Open decisions for Aaron

1. **Reviewing unit.** One row per mention, or one row per distinct DOI per note? Per DOI cuts the queue (the Memo: 18 mentions, 9 DOIs). Recommended: per distinct DOI per note, showing all its mentions.
2. **Auto-dismiss rule for "Same work".** Should a human "Same work" on (identifier, citation) carry across notes (the same citation appearing in several notes)? Recommended: yes, keyed on (identifier, normalized citation), so reviewers decide each real citation once.
3. **Who reviews.** Aaron only, or can Claude pre-sort PLAUSIBLE rows by a quote-anchored check that Aaron then confirms? Claude pre-sorting is out of scope until the quote-anchored span design exists.

## 7. Suggested order of work (nothing started)

1. Codex lands the checker (v5), then adds the tiers, the linking pass and the `evidence` field (tiers decision v2). Schema migration plan first.
2. Add the ledger functions and the row key, with tests (Codex; follows the `offering_links` pattern).
3. Build the artifact page from the ledger (Claude or Codex; needs the artifact design and capabilities skills at build time).
4. Wire surface A (`verify-sources`) and surface B (agent and integrator procedure) as separate small changes.

## 8. Out of scope

Implementation, any LLM call, editing notes automatically, CI wiring, paid API use.
