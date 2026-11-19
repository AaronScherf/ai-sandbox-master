# Reference checker

Checks that each citation in a Markdown research note points at the work it names. It resolves every DOI with the registry that issued it, compares the registered record with how the note cites it, sorts each citation into a tier, and sends anything a machine cannot settle to a person through a review page. A landing gate stops a branch that changes a research note while that note has known-bad or undecided citations.

It exists because an AI writing agent marked every reference in four literature notes as verified. When the 38 `doi.org` links were checked against Crossref, 13 resolved to the cited paper, 13 resolved to a different paper and 12 did not resolve. The agent's correction pass then reported "zero unverified" while still leaving errors. The checker makes that claim mechanical, and the gate makes it unavoidable. The full record is in [HISTORY.md](HISTORY.md).

## What it checks, and what it does not

**Checks:**
- that each DOI or arXiv ID is registered, with Crossref, DataCite or arXiv;
- that the registered work is the one cited: authors, year and title, scored against the citation text;
- for a citation with no title, that its authors and year match, and that the same team published no similar work in the surrounding years that the citation could mean instead;
- for a cited title that does not match the record, whether that title exists anywhere in Crossref or OpenAlex. If it doesn't, the title was invented.

**Does not check:**
- that the paper supports the claim it is cited for (there is no claim check yet);
- URLs that are not DOIs, which it counts but does not resolve;
- page numbers, volume or journal name, beyond the identity score.

## Files

All paths are relative to `ai-sandbox/academic-rag-model/`.

| File | Role |
|---|---|
| `tools/reference_checker.py` | Parses citations, queries registries, assigns tiers. Usable on its own. |
| `tools/reference_review.py` | Ledger: raises review items, applies decisions, records defects, runs the gate. |
| `tools/reference_review_page.html` | Source of the interactive review page (a Claude Artifact). |
| `tools/land_branch.py` | Calls the gate during `check` and again just before `land`. |
| `tests/tools/test_reference_checker*.py`, `test_reference_review.py` | Tests on recorded registry answers; none of them use the network. |
| `.reference_checker_cache/` | Registry response cache (gitignored). |
| `.reference_checker_review/` | Ledger: `review.json`, `dismissals.json`, `defects.json` (gitignored). |

The cache and ledger always live in the main checkout, found through git's common directory, so every worktree shares one set of decisions.

## Running it

From `ai-sandbox/academic-rag-model/`, with the project venv:

```powershell
# Check a note or reference list and print a table (read-only; writes only the cache)
python -m tools.reference_checker "path\to\note.md" --format markdown

# Check notes and update the review ledger; prints open items and defects
python -m tools.reference_review raise "path\to\note.md" ["path\to\other.md" ...]

# Show the ledger
python -m tools.reference_review list --status open

# Apply decisions exported from the review page
python -m tools.reference_review apply decisions.json --dry-run
python -m tools.reference_review apply decisions.json
```

`reference_checker` options:
- `--offline` answers from the cache only;
- `--refresh` ignores the cache;
- `--pace` sets the minimum seconds between requests (default 0.2; the client backs off and honours `Retry-After` on HTTP 429);
- `--exit-nonzero-on-findings` makes it usable in scripts.

## Tiers

| Tier | Meaning | Outcome |
|---|---|---|
| CONFIRMED | Title scores ≥0.92 and the year is within one, or the title scores ≥0.5 and the year matches exactly | Passes |
| AUTHOR_YEAR | No title in the citation; every cited surname is registered; the year matches exactly; Crossref registered the DOI; the same-team search finds no sibling | Passes |
| PLAUSIBLE | No title, and one of the AUTHOR_YEAR conditions fails | Review |
| UNCHECKED | No DOI (plain URL or bare citation); the checker only offers candidates | Counted, not gated |
| UNRESOLVED | A registry lookup failed | Gate fails closed; retry |
| REVIEW / AMBIGUOUS | Same authors, but the title or year disagrees and no rule settles it | Review |
| TITLE_WRONG | Right DOI and authors, but the cited title exists in neither Crossref nor OpenAlex | Defect: fix the title in the note |
| NOT_FOUND | The DOI is not registered | Defect |
| WRONG_WORK | The DOI resolves to a different work | Defect |

**Same-team guard.** This only applies to title-less rows. The checker resolves the DOI in OpenAlex to author IDs, then lists every work by the first author within one year either side of the cited year. A sibling is a work that shares the first author and at least one co-author, and whose title scores below 0.8 against the registered title. Crossref author search can add siblings but cannot clear a row. The guard fails closed: if the first author has no ID, there are more than 1,000 candidates, or a lookup errors, the row stays in review.

## The review loop

1. `raise` turns every row that needs a person into a ledger item: one per DOI per note, showing all of that DOI's mentions.
2. An agent seeds the review page's `items` collection from `list --status open`. The page shows the citation beside the registered record, with links to both, any same-team siblings, and any cited title found elsewhere.
3. The reviewer picks one of five decisions:
   - **Same work:** dismissed. It carries over to the same citation text in other notes.
   - **Wrong work:** recorded as a WRONG_WORK defect for this note.
   - **Title wrong, DOI right:** recorded as a TITLE_WRONG defect with the registered title.
   - **Not found:** recorded as a NOT_FOUND defect.
   - **Can't tell:** deferred, and stays open.
4. The agent reads the page's `decisions` collection and runs `apply`.

Defects clear only when the note's citation text changes. An unchanged citation keeps its defect when the note is raised again.

## The landing gate

`python -m tools.land_branch check` runs the gate after the tests, and `land` runs it again just before merging. In scope are the Markdown files under `ai-sandbox/research/` that the branch adds or modifies. The gate stops with `STOP: citation gate: ...` when any of those notes has a defect, an open review item, or a failed registry lookup, and it names each note with its counts. Branches that touch no research note skip it entirely. There is no override flag.

Agents are told to run `raise` before handing off any note that cites literature, and never to write `[source-verified]`-style tags themselves (see `GEMINI.md`, "Citing literature").

## Data sent to outside services

There are no API keys, and no email address or user name is sent. The User-Agent is `ReferenceChecker/1.0 (bibliographic metadata validation)`. Note bodies never leave the machine.

| Service | What is sent |
|---|---|
| doi.org RA lookup, Crossref, DataCite | the DOI |
| Crossref (no-DOI rows) | the extracted title, or at most 200 characters of the citation |
| Crossref (same-team guard) | up to four registered author surnames and a three-year window |
| OpenAlex (same-team guard) | the DOI, then OpenAlex author IDs and a year range |
| Crossref and OpenAlex (title search) | at most 200 characters of the cited title, plus cited surnames to Crossref |

## Known limits

- **One DOI per row.** When a table cell holds several DOIs, each inherits the same citation text, so a dataset DOI can be judged against paper authors. Review such rows by hand.
- **OpenAlex sometimes splits one person into two author IDs,** which can hide a sibling from the guard. Crossref is a second net, but not a complete one.
- **A transient title-search failure reopens a decided item.** The row's reason changes to "title search unavailable", which makes the item differ from the one decided. Raise the note again once the registries answer.
- **Identity is not the same as support.** A CONFIRMED citation may still be cited for a claim the paper does not make.

## Using it elsewhere

The checker and ledger use only the Python standard library. They have two in-repo imports: `tools.git_workflow.git_common_dir`, which locates the main checkout, and `core.indexer.review_envelope.ReviewItem`, which supplies the ledger's item format. To use them outside this monorepo, copy the two modules and their tests, replace `shared_project_root()` with a fixed path, and vendor `ReviewItem` (a small dataclass). The review page needs Claude Artifacts. Without them, `list` and `apply` work on hand-written JSON decisions. The gate is specific to `land_branch`, but `reference_review.gate(paths, client)` returns per-note counts that any CI step can check.
