# Spot check of Gemini's novelty-check notes (v1)

*Claude, 2026-11-11. Checks Gemini's four notes (`Novelty Check - Summary / RQ1 / RQ2 / RQ3 - v1.md`, in the worktree `gemini-nexus-novelty-check`) against the [handoff](../../../docs/superpowers/plans/2026-11-10-novelty-literature-check-handoff.md)'s evidence standard. I did not edit Gemini's files. This is a spot check, not a full audit.*

**Tags.** **[C]** checked by me against Crossref or a search result. **[S]** from a web-search summary, not opened at the source. **[I]** my inference or prior knowledge, unverified.

## 1. Method and limits

- **DOI check [C].** I extracted every `doi.org` link from the four notes (38 unique) and resolved each against Crossref, comparing Crossref's title, authors, journal, year and pages with Gemini's citation text.
- **Claim checks [S].** Five web searches on the claims that carry the most weight.
- **Limits.** Crossref does not hold arXiv or some DataCite DOIs, so those return 404 for a benign reason. My extraction truncated one DOI that contains parentheses (Claxton 1999). I did not check references listed without a DOI, and did not read the RQ2 note beyond grepping. A DOI that resolves to a different paper is wrong, but the paper itself usually exists.

## 2. Result: the [VERIFIED] tags are not reliable

Gemini tagged every reference **[VERIFIED]**. Of the 38 DOIs:

| Outcome | Count | Meaning |
|---|---|---|
| DOI resolves to the cited paper | **13** | Correct (a few have slightly wrong titles) |
| DOI resolves to a **different paper** | **13** | Wrong DOI; the cited paper may or may not exist |
| DOI not found in Crossref | **12** | At least 3 are benign (arXiv, a truncated DOI, a possible DataCite record); the rest are likely wrong |

### DOIs that resolve to a different paper [C]

| Gemini's citation | What the DOI actually is |
|---|---|
| Brown, Salisbury & Ball (2025), AEA P&P (`pandp.20251068`) | A paper on corporate ownership and the gender asset gap. The search shows the real DOI is `10.1257/pandp.20251021` [S]. The paper itself exists. |
| Claxton & Sculpher (2006), PharmacoEconomics (`...200624110-00002`) | A Weinstein paper on decision-analytic modelling, pp. 1043–1053 |
| Fenwick, Claxton & Sculpher (2008), Med Decis Making | An Etzioni et al. paper on PSA screening |
| Lopez et al. (2020), Int J Disaster Risk Reduction | A Felsenstein & Grinberger paper on labor-market effects |
| Kok (2009), Env Modelling & Software | A Vivanco et al. air-quality paper |
| Dahabreh et al. (2020), Am J Epidemiology | "Editorial Consultants" |
| DellaVigna & Pope (2018), JPE | A Philosophy of Science paper (Lean) |
| Hotz, Imbens & Mortimer (2005), J Econometrics | A Vogelsang & Franses paper |
| Kastner et al. (2009), BMC Med Res Methodol | A Takahashi-Omoe et al. paper on journal selection |
| Meager (2019), AEJ: Applied | The right DOI for the microcredit paper, but Gemini's title ("Six Randomised Trials of Social Programs") is wrong |
| Pritchett & Sandefur (2015), AER | An Ambuehl, Niederle & Roth paper |
| Rosenzweig & Udry (2020), REStud | A Cooley, Marimon & Quadrini paper |
| Vivalt (2020), JEEA | A Bennett & Ouazad paper |

### DOIs not found in Crossref [C]

Claxton 1999 (truncation artifact), Coughlan de Perez 2015, Andrews et al. 2013, Barbrook-Johnson & Penn 2021, Ben-Haim 2006, Bowen et al. 2020, Hausmann et al. 2008, Hummelbrunner 2010, Montiel Olea et al. 2023 (arXiv), Saran & White 2018, Crost et al. 2016, Gechter 2023.

### Citations with substantive errors beyond the DOI [C, S]

- **Crost et al. (2016).** Gemini: "Crost, Felter & **Mansour**, *American Economic Review* 106(1), 171–210," and describes it as showing cash-transfer rollout **increased** insurgent violence. Search results show the paper is by Crost, Felter and **Johnston**, in the ***Journal of Development Economics*** 118 (2016), pp. 171–182, DOI 10.1016/j.jdeveco.2015.08.005 [S]. The reported finding is the **opposite**: the transfer program reduced insurgent influence and conflict incidents in treated villages [S]. I did not open the paper. Gemini may have confused this with the same authors' 2014 *Aid under Fire* result on development projects [I].
- **Gechter.** Gemini: JBES 41(3), 839–851, 2023. The search shows JBES **42**(2), 801–811, **2024**, DOI 10.1080/07350015.2023.2241529 [S]. The substance (bounds on effects across contexts, India application) matches.

## 3. The claims the summary leads with

| Gemini's claim | My check | Assessment |
|---|---|---|
| Surprise 1: formal value of information is "totally absent" from operational aid programming and "never adapted" to development programme design | The note's own RQ1 text cites GiveWell's VOI model (Brown et al., which I confirmed exists [S]) and IDinsight's decision-focused evaluations. A further search found **IDinsight's simulation-based value-of-information work on whether an evaluation is worth commissioning for a scale-up decision** [S], which is a direct adaptation to development. I found no worked humanitarian-commissioning case [S]. | **Overstated.** The defensible claim is narrower: no worked VOI for humanitarian or transition programme design found, and the nearest prior work (IDinsight, GiveWell) should be read closely. The summary also contradicts its own "partly answered" verdict. |
| Surprise 2: participatory mapping (loops) conflicts with DAGs, and "virtually no literature" bridges them | Not searched. The mathematics of identification is for acyclic graphs, but cyclic structural causal models and time-unrolled graphs exist [I, unverified; I believe Bongers, Forré, Peters and Mooij cover cycles]. | **Plausible practical gap, overstated as "mathematically impossible."** Unchecked. |
| Surprise 3: no one has pre-registered a statistical transport prediction and tested it against a built-in trial in a crisis | One search found related work but no match: a registered model prediction of replication outcomes (Social Science Replication Project), CEGA's pre-registered forecasts of RCT effects, and an external-validity function used to choose experiment sites [S]. None is a transport model tested in a crisis. | **Not refuted, but rests on absence in a short search.** Say "I found no example," not "never." |
| "None of the evidence gap maps have stopping rules or capture-recapture saturation metrics" | Not searched. Gemini's own RQ3 note says capture-recapture has been applied to literature searches (Kastner et al.), and that citation's DOI is wrong. | **Unchecked and strong.** Treat as a lead. |
| Verdicts: all three RQs "partly answered" | Directionally consistent with what I found for RQ1. RQ2 and RQ3 not independently assessed. | **Plausible, not verified.** |

## 4. What this means

1. **Do not quote the novelty summary or use its "surprises" in a talk yet.** The headline claims are the least reliable part.
2. **The notes remain useful as a reading list.** Most cited papers do exist (Vivalt 2020, Pritchett and Sandefur, Rosenzweig and Udry, Hotz et al., Claxton, Hjort et al.). The failure is in identifiers and in a few descriptions, not in the whole picture.
3. **The earlier warning repeated.** The handoff said earlier Gemini output had unverifiable references, and required opening every source. The result suggests references were assembled from memory and tagged verified without checking.
4. **RQ1 is closer to existing practice than the summary says.** IDinsight's work is the nearest prior art and needs a careful read before RQ1's contribution is stated.

## 5. Suggested next steps

1. Send Gemini this note and require a **correction pass**: for each reference, find the paper at the publisher, give a working link, and re-tag. Ask for the two substantive fixes (Crost, Gechter) first.
2. Have **Codex write a small reusable reference checker** for the repo (resolve DOIs against Crossref and DataCite, flag title/author mismatches, flag unresolved links). It is code maintenance and would catch this class of error in every future handoff. My script was a one-off and is not in the repo.
3. Then re-read the three RQ notes for substance, starting with RQ1 and IDinsight's value-of-information work.
