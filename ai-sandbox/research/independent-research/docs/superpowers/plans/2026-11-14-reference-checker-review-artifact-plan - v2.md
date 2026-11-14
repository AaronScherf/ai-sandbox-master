# Reference checker: review artifact plan, v2 (decisions recorded)

Date: 2026-11-14. Supersedes only section 6 of `2026-11-14-reference-checker-review-artifact-plan.md` (kept unchanged); every other section of that file stands. Design only.

## Decisions (Aaron, 2026-11-14)

1. **Review unit: one row per distinct DOI per note.** The row shows all of that DOI's mentions in the note. (The Memo: 18 mentions, 9 DOIs, so 9 rows.)
2. **"Same work" carries across notes.** Keyed on (identifier, normalized citation text). A reviewer decides each real citation once; the same citation in another note is dismissed automatically. A changed citation text for the same identifier is a new row. "Wrong work" does not carry: it is a defect in one note and is reported per note.
3. **Claim pre-sorting is approved in principle.** An agent may pre-sort PLAUSIBLE rows with a quote-anchored check, and Aaron then confirms. It stays out of scope until the quote-anchored span design exists; it never becomes an automatic pass. The pre-sort only orders and annotates the queue; every PLAUSIBLE row is still decided by a human.

## Effect on the plan

- Section 2 and section 5 row key: per DOI per note, with mentions listed inside the row. The ledger key is (note path, identifier) for the row and (identifier, normalized citation) for the cross-note dismissal.
- Section 4: "Same work" writes a dismissal that applies to any note with the same (identifier, normalized citation). "Wrong work" writes a per-note defect only.
- Section 7: no change to the order of work.
