You are a Gemini (Antigravity) session. Task: verify three headline "scale" figures against their primary sources, so they can go on the opening slide of a PhD peer talk. This is a read-and-verify task. Follow docs/WORKTREE_WORKFLOW.md (your own worktree for the note you write; explicit-path staging; never `git add -A`). Do not commit or push without reporting to Aaron.

Why. Claude found these figures through a web-search summary, not the primary pages. They must be checked before they are shown. Do not rely on news coverage, blogs or search-engine summaries; use the issuing organization's own report or data page.

The three claims to verify (wording as it will appear on the slide)
1. **World Bank:** a growing share of the world's extreme poor lives in fragile and conflict-affected situations; the World Bank's 2025 projection is roughly 435 million people, nearly 60 percent of the extreme poor, by 2030.
   - Find the primary report or data page (the June 2025 World Bank report on fragile and conflict-affected situations and/or its Poverty, Prosperity and Planet or Poverty and Shared Prosperity material). Record: the exact figure and the share; the year the projection refers to; **which international poverty line** it uses and in which PPP year; how "fragile and conflict-affected situations" is defined (the World Bank FCS list for which fiscal year); and whether the report says the share is sensitive to the poverty line.
2. **UNHCR:** about seven in ten refugees are in protracted situations (UNHCR Global Trends, 2025 data).
   - Find the Global Trends report for the 2025 data year. Record: the exact share; the definition of "protracted" (for example exile of five or more years) and any recent change to the definition or to the minimum-size threshold for a "situation"; the reference date; and whether the figure refers to refugees only or also to other displaced groups.
3. **OCHA:** about 239 million people need humanitarian assistance (Global Humanitarian Overview 2026).
   - Find the GHO 2026 document or the OCHA data page. Record: the exact number of people in need; the number targeted; the funding requirement; the date of publication; and the geographic scope (the countries and plans covered).

Optional, only if a primary source states it plainly: how long crises last (for example the share of humanitarian appeals that run for five or more years, or the average length of an appeal). Say "not found" rather than estimate.

Rules
- For each claim, give: the primary source (title, issuing body, date, URL), the page or table, a short quotation (under 25 words) with the page number, the verdict (SUPPORTED / PARTLY / NOT SUPPORTED / NOT FOUND), and the exact wording the slide should use if the figure is different.
- Tags: FULL-TEXT-READ only for what you actually read; use LANDING-PAGE-ONLY, UNVERIFIED where that applies.
- Do not paste long passages from reports. Do not use paywalled or blocked pages; if a page returns 403, say so and give the URL.
- Report any discrepancy between the claim and the source, even a small one (rounding, the year, the line).
- Do not edit Claude's slide files, review notes or the tracker.

Output
Write one note, `Slide Evidence Check - Scale Figures - v1.md`, in `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/` in your own worktree, with a one-line verdict table at the top and a section per claim. Report back to Aaron with the verdicts and a clickable file:// link to the note (keep the backslash before `.worktrees` where it applies).
