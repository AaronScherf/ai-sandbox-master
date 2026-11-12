# Handoff to Codex: reference checker review, round 2 with owner decisions (v3)

From: Claude review session, 2026-11-11. Supersedes `... - v2.md` (v1 and v2 kept unchanged; v2 was committed as `4ac01e87`). v3 changes only the decisions (section 6), the gate wording that depends on them, and the out-of-scope list. Findings and the work order are otherwise as in v2.
To: the Codex session on `codex/reference-checker` (worktree `.worktrees/codex-reference-checker`).
Scope: findings and a work order. Claude changed no Codex files, no Gemini notes and no pipeline code.

## 0. Corrections to v1

- **Mojibake claim withdrawn.** v1 said the Gemini notes contain `308�312` page corruption and asked for Windows-1252 repair. That was wrong. The RQ1 v2 note contains a proper en dash (`308–312`) and zero U+FFFD characters; the "�" came from Claude's console encoding. The addendum's own request to normalize HTML entities and Windows-1252 text stands, but there is no evidence the notes need it. Do not add repair code for this.
- **Gate wording retracted.** v1 section 6 said `SAME_WORK` with `NO_TITLE` passes the future gate. That is too loose; see defect 2 below. The replacement wording is in section 5.

## 1. Round 1 requests: status

Verified in the current code (read, not only trusted from the report):

| v1 step | Status |
|---|---|
| Author-set identity | Done (`compare()`), but see defects 1 and 2. |
| NOT_FOUND vs UNRESOLVED, unsupported agency | Done. Unsupported agency has a distinct reason but classification `UNRESOLVED`. |
| Title-only gaps no longer MISMATCH | Done (`TITLE_DIFFERS`, PARTIAL). |
| All Crossref date fields for year | Done. No one-year tolerance; any miss is `YEAR_DIFFERS`. |
| Tables, multi-DOI bullets, quoted-correction exclusion, coverage + exit 1 | Done. |
| One client per run, atomic writes, corrupt-cache heal, `--refresh`, 7-day negative TTL, 200-char query cap, `.gitignore` | Done. |

Reproduced: 30 passed, 1 skipped offline. Reports show 42 DOI rows: 32 SAME_WORK, 7 WRONG_WORK, 3 NOT_FOUND. The 7 wrong-work and 3 not-found rows are exactly the addendum's. Coverage on the three v2 notes is complete (11/8/23 DOIs attached; 15/13/23 reference bullets all have rows).

## 2. Defects, observed

1. **Identifier-only citation produces a false WRONG_WORK.**
   - In the Literature Gap Memo (`notes/01_compound-shocks-panel/review-gate/Literature Gap Memo.md`) all 16 table rows get the DOI string as `citation`, because the link label is the DOI and the table branch is never reached when a link is present.
   - `YEAR` matches "2023" inside `10.1016/j.gloenvcha.2023.102641`, and fragments of the DOI become author tokens. With a plausible registry record, `compare()` returns WRONG_WORK for that correct DOI; the same DOI with "Thalheimer, Schwarz, & Pretis (2023)" returns SAME_WORK.
2. **`SAME_WORK` rests on author-token overlap alone.** Crafted records show SAME_WORK at title scores 0.24 to 0.40 for: a shared second author, a shared common surname, and the shared particles "der" and "den". `TITLE_DIFFERS` is attached, but any consumer reading `identity` alone passes them. Real rows with thin support:
   - Brown (title 0.37), Lopez (0.44), Montiel Olea (0.43), Rosenzweig and Udry (0.47), White/Saran/Welch (0.29).
   - Montiel Olea's cited title, "Externally valid policy choice", names a different work than the registry's k-Median title. That may be a different real paper; the checker cannot tell.
   - Tested rule: SAME_WORK only if the cited first-author block matches the registry first author, or at least two cited surnames overlap. It keeps 30 of the 32 recorded SAME_WORK rows. The two it rejects are Montiel Olea (compound surname: compare the whole first-author block before the first comma, not its first token) and White/Saran/Welch (the registry lists only Saran, so it is genuinely uncorroborated).
3. **Venue, pages and some title flags are parser artifacts.**
   - 16 of 32 SAME_WORK rows carry `VENUE_DIFFERS`. The "venue" is Gemini's one-line annotation sentence (for example "Meta-analysis of 635 development effect sizes…"). The real venue (`*JEEA*`) sits in the title segment.
   - Hotz's `PAGES_DIFFER` comes from the issue range `125(1–2)` read as pages (`1-2` vs `241-270`).
   - Wetterslev's cited and registry titles are identical but score 0.92, and Gechter's 0.84, because the italic venue stays in the extracted title.
   - Of the 14 `TITLE_DIFFERS` rows, some are real (Brown, Lopez, Haasnoot, Claxton); others come from the Crossref `subtitle` field being ignored (Barbrook-Johnson, "Systems Mapping").
   - Net effect: `text_fidelity` cannot yet separate good citations from bad ones.

Minor and observed: `gap` in `compare()` is unused; `YEAR_DIFFERS` does not report the two years; no test covers the 7-day negative TTL, `--refresh`, atomic write, CLI exit codes, or `text_fidelity` values other than `TITLE_DIFFERS`. The 32 expected SAME_WORK labels in `reference_checker_v2_references.json` cannot be checked against an independent source; the addendum fixes only about 20.

## 3. Possible limitations (code reading or crafted inputs, not seen in data)

- Mueller vs Müller gives a false WRONG_WORK (NFKD folding does not map "ü" to "ue").
- Crossref organization authors use `name`; the code reads `family` and `literal` only, so a corporate author yields an empty author list.
- An unwritable cache (OSError) is not caught in `check()` and aborts the run.
- `--offline` ignores a stale 404 entry.
- The title-search fallback sends up to 200 characters of the extracted line to Crossref. Make it opt-in or document it in the module docstring.
- The CLI exits 0 when rows are WRONG_WORK or NOT_FOUND. Fine for an advisory report, wrong for a gate.
- References with no DOI, URL or APA-style "(YYYY)." pattern are not counted by `coverage()`.

## 4. Work order (tests first; one commit per step; offline tests green at each step)

1. **Identifier-only citations.** Strip DOIs and URLs from `citation` before taking year and author tokens. If no author tokens remain, identity is `UNCHECKED`. For table rows that contain a link, take the cell text next to the link as the citation. Regression: the 16 Literature Gap Memo rows must not return WRONG_WORK; add a recorded fixture for one.
2. **Identity needs corroboration.** SAME_WORK requires first-author-block match, or at least two surname overlaps, or title score at least 0.92. Otherwise report `AMBIGUOUS` (classification PARTIAL). Compare compound surnames by the first-author block. Drop particles ("der", "den", "van", "von", "de", "del", "la", "le", "da", "di") from tokens. Keep `WRONG_WORK` as is. Expected on the recorded set: the 7 wrong-work and 3 not-found rows unchanged, Montiel Olea SAME_WORK, White/Saran/Welch `AMBIGUOUS`. The addendum treated White as unspecified, so reporting it is correct.
3. **Text-fidelity parsing.** Strip markdown italics and the trailing annotation sentence before title, venue and pages; ignore `(n–m)` issue ranges when reading pages; use the Crossref `subtitle` field when scoring titles. Until done, do not emit `VENUE_DIFFERS` or `PAGES_DIFFER`. Add tests that pin `text_fidelity == ["OK"]` for a clean row (Vivalt, Hotz, Wetterslev from the fixtures) and a real title difference (Brown).
4. **Report years in `YEAR_DIFFERS`** ("cited 2020; registry 2019, 2018 online") and remove the unused `gap`.
5. **Coverage and tests.** Tests for 404 expiry, `--refresh`, atomic replace, CLI exit codes. Add an `--exit-nonzero-on-findings` flag (default off) for later gate use.
6. **Hardening, small.** Catch OSError on cache write and degrade to uncached; read Crossref `name` for organization authors; fold ue/oe/ae variants when comparing surnames; make the title-search fallback opt-in or documented.
7. **Rerun** the v2 notes and the Literature Gap Memo and report counts per identity, with the list of rows that changed from round 2.

## 5. Future gate (design only; replaces v1 section 6)

Rule as proposed by Aaron stays: identifiers and bibliographic metadata come from a registry or a source file; an LLM extracts claims only with quote-anchored spans. Gate verdicts, tightened:

- Passes: `SAME_WORK` with `OK`, or with `NO_TITLE` **only if** a human or a registry search chose the DOI, not the LLM.
- Passes after the registry title replaces the note's title: `SAME_WORK` with `TITLE_DIFFERS`.
- Blocks pending a human: `AMBIGUOUS`, `WRONG_WORK`, `NOT_FOUND`, unattached DOIs, and any row whose citation is identifier-only.
- `UNRESOLVED` means retry; never a pass.
- A registry match shows the work exists and is identified. It does not show that the work supports the claim; that stays with the quote-anchored span check.

`AMBIGUOUS` rows route to the interactive review artifact (decision 3). Placement is still inferred from filenames; Claude has not read the evidence-map design docs.

## 6. Decisions (made by Aaron, 2026-11-11; no longer open)

1. **Identity and text fidelity stay separate fields.** Keep `identity` and `text_fidelity` as implemented. `classification` remains the legacy summary derived from them and is not an input to any decision.
2. **Author-year-only citations stay `NO_TITLE`.** They can reach `SAME_WORK` at most and never `MATCH`, unless the note's reference section carries a fuller citation. If it does, extraction should prefer the fuller citation. Whether the v2 notes carry fuller citations has not been checked; investigate before building anything.
3. **`AMBIGUOUS` rows go to the interactive review artifact.** This follows the human-decision rule in `ai-sandbox/academic-rag-model/CLAUDE.md`. The artifact is a later gate concern: in this pass the checker only emits `AMBIGUOUS`, and nothing is built for the artifact.

Effect on the work order: none to steps 1 to 7. Step 2 already introduces `AMBIGUOUS`; decisions 1 and 2 confirm the current field design and `NO_TITLE` behavior, so no step changes them.

## 7. Out of scope

Wiring into any pipeline, the evidence-map flow or CI; building the review artifact for `AMBIGUOUS` rows; any LLM call; editing the Gemini notes.
