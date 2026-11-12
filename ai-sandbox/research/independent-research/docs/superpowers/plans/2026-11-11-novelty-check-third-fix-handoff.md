You are the Gemini (Antigravity) session that wrote `Novelty Check - ... - v3.md` in your worktree `gemini-nexus-novelty-check`. Claude re-resolved every DOI in the v3 notes and all ten earlier problems are fixed. Two small items remain. Write a `- v4` copy of only the notes that change and a `Novelty Check - Correction Log - v3.md`. Do not edit v1, v2 or v3 files; do not commit or push; keep to your worktree.

1. Montiel Olea et al. (2024), arXiv:2408.09187. DataCite returns the title "Externally Valid Selection of Experimental Sites via the k-Median Problem" (authors Montiel Olea, Prallon, Qiu, Stoye). Your notes call it "Externally valid policy choice". Open the arXiv abstract page (arxiv.org/abs/2408.09187), copy the title and authors exactly as shown, and fix every place the title appears. If the arXiv page shows an older title in its version history, say so. Check that the one-sentence description of the paper (site selection as a k-median problem) matches the abstract you opened.

2. Verification tags. v3 tags all 51 references [VERIFIED] and describes the 42 journal papers as "full page audited". Your own report says these were resolved by script against Crossref and DataCite (title and first author matched), not read. Change the tag vocabulary so it says what was done:
   - REGISTRY-MATCHED: DOI resolved at Crossref or DataCite and the registered title and first author match the citation. Nothing read.
   - ABSTRACT-READ: you opened the abstract at a publisher or preprint page and the description in the note matches it.
   - FULL-TEXT-READ: you read the paper's text.
   - INSTITUTIONAL-URL: a book or report whose official page you opened (no DOI check).
   - UNVERIFIED.
   Re-tag every reference with the highest level you actually reached, and give the counts per tag. Do not use FULL-TEXT-READ unless you can name a specific passage you read. For each claim in the notes that depends on what a paper found (not just that it exists), list which tag the paper has. If a claim rests on a REGISTRY-MATCHED reference only, say so beside the claim.

Report back to Aaron with the file list as clickable file:// paths (real absolute paths; keep the backslash before `.worktrees`), counts per tag, and the list of claims that rest on references you have only registry-matched.
