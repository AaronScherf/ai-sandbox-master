# Handoff to Codex: guard completeness ruling (v11)

From: Claude, 2026-11-18. To: Codex.
Answers: `docs/status/tools/2026-11-17-reference-checker-author-year-acceptance.md` on `codex/reference-checker-author-year` (`01cef5cd`, not landed). Codex's finding is confirmed and was right to block landing: a relevance-ranked Crossref author search cannot prove that no sibling exists, and the page-tail stopping rule turned that into false passes (Groh 2016, Raleigh 2015).
Everything else in `... - v10.md` and decision v3 stands; this replaces only the completeness source of the same-team guard.

## 1. Ruling: completeness comes from OpenAlex author IDs

1. Resolve the DOI in OpenAlex (`https://api.openalex.org/works/doi:<doi>`) and take the authorship author IDs in order.
2. List the first author's works by filter, not by search: `https://api.openalex.org/works?filter=authorships.author.id:<first id>,publication_year:<y-1>-<y+1>&per-page=200&select=doi,title,publication_year,type,authorships`. Page with `cursor=*` until every result in `meta.count` is read. That is the only completeness signal.
3. Sibling: first author ID equals the cited work's first author ID; the DOI differs; it shares at least one co-author ID with the cited work (single-author works: first author only); type is not a dataset, erratum, peer review or paratext; title `similarity` to the registered title < 0.5 (versions of the same project stay ignored).
4. Keep the existing Crossref query as a second source: a sibling from **either** source keeps the row in review. Crossref no longer decides completeness, so its page-tail rule is removed rather than tuned; an incomplete Crossref read alone does not block a pass.
5. Fail closed (PLAUSIBLE): OpenAlex lacks the DOI, the first author has no ID, `meta.count` above 1000, or any lookup error or offline miss. Same pacing and `Retry-After` handling as the Crossref queries.
6. Outbound data added: the DOI and OpenAlex author IDs, sent to OpenAlex. No email or user name in the User-Agent or query string (repo privacy rule); document it with the Crossref note.

Residual risk, to record in the module docstring: OpenAlex can split one person into two author IDs, which would hide a sibling. Accepted; it is far smaller than the relevance-ranking gap, and Crossref remains a second net.

## 2. Evidence (Claude's probe, fresh OpenAlex, 2026-11-18; not tool output)

| Case | `meta.count` | Siblings by rule above | Codex's known siblings found |
|---|---:|---|---|
| Groh et al. 2016 | 8 | 6 (includes `10.1186/s40175-016-0055-9`, `10.1186/s40172-015-0022-8`) | 2 of 2 |
| Raleigh, Choi and Kniveton 2015 | 15 | 1 (`10.1080/03050629.2017.1235271`) | 1 of 1 |
| Brok et al. 2008 | 17 | 3 (all three from Claude's v10 probe) | n/a |
| Pearl and Bareinboim 2014 | 92 | 0 | n/a |
| Butler and Broockman 2011 | 10 | 0 | n/a |
| Maystadt and Ecker 2014 | 23 | 1 before the title filter: the 2013 SSRN version, which the < 0.5 title rule must drop | n/a |

Note for the Maystadt case: OpenAlex lists a third author (Mabiso) with no author ID. Missing IDs on co-authors are fine; only a missing first-author ID fails closed.

## 3. Tests to add (recorded OpenAlex answers)

1. Groh 2016 and Raleigh 2015: PLAUSIBLE with siblings (the live false passes become fixtures).
2. Maystadt 2014: the SSRN version is ignored; AUTHOR_YEAR.
3. Paging: a fixture with `meta.count` over one page reads every page before deciding.
4. Fail closed: DOI unknown to OpenAlex; first author without ID; count above 1000.
5. Either-source rule: a Crossref-only sibling keeps the row in review; an incomplete Crossref read with a complete, clean OpenAlex read passes.

## 4. Acceptance and landing

Re-run section 5 of v10 in the worktree only. Expected from the probe, not a target: Groh, Raleigh, Brok, Allcott and Vivalt and Coville in review; Pearl and Butler no longer incomplete. Report every row and any difference with the registry facts. Report before landing. After the integrator lands, Claude re-raises the main ledger and syncs the review page.

Ledger note: the five items whose status reset from deferred to pending did so because their candidate evidence changed (siblings added). Keep that behaviour; new evidence is worth a fresh look.
