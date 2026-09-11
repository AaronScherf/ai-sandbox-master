# Ground Truth

*Research Planning Memo*

A synthesis of nineteen statements of purpose and research notes written over the last application cycle — read together for what they keep saying, independent of which school each one was addressed to — mapped onto research directions and first-year projects for a PhD in Sustainable Development at Columbia SIPA.

- 18 SoPs / faculty statements + 1 notes file
- Prepared 2026-08-31
- Source: research/independent-research/notes

> **Revision — first-year plan added.** This pass folds in the actual courseload (a standard micro / macro / econometrics sequence, an added environmental science course, and a seminar on open-source data for conflict analysis), drops the Ukraine agribusiness RCT project entirely — that evaluation was canceled and the underlying material is government-sensitive regardless — and reframes the flagship. Rather than digital finance with displacement as a secondary chapter, **climate adaptation, migration, and cash transfers under conflict** is now the direction the reputation gets built around, with the causal-ML and remote-sensing toolkit serving that agenda rather than standing alone. Two new sections — Outreach and Timeline — turn that into an actual calendar.

> **Cross-linked with the blogging strategy.** The Projects and Timeline sections below drive the publishing calendar in `ai-sandbox/research/independent-research/projects/blogging_strategy/website_blog_plan.md` — its "Research Project Plan" table and "Blog Publishing Plan for 2026" section point back here for the full research and outreach context behind each entry. If a project is added, dropped, or rescheduled here, update that doc in the same sitting, and vice versa if a publishing deadline forces a project's timeline to move.

## 01. Sources & how this was built

Every Markdown file in `processed_outputs/` was read in full: the Columbia SIPA statement of purpose and faculty-alignment note, full-length statements for Stanford (E-IPER, two supplements), Berkeley ARE (two drafts plus a faculty-preference note), MIT, Cornell, Harvard, Northwestern, NYU, Princeton, Michigan (two programs), American, the New School, Tufts/Fletcher, and the free-form `Research Ideas.md` working notes. `Research Ideas.docx` in the parent folder was already converted and current — no re-run of the conversion pipeline was needed.

Because roughly a dozen of these essays are close variants of one core research pitch, adapted school to school, the counts below reflect distinct *essays* that carry a theme, not independent confirmations — repetition across near-duplicate drafts is a sign of how settled an idea is in your thinking, not eighteen separate people agreeing with you. That distinction matters for reading the coverage bars honestly.

## 02. Recurrent themes

Six threads show up often enough to be load-bearing, plus one strand that recurs but pulls in a different methodological direction from the rest.

### 01. Climate-adaptive agriculture for smallholder farmers (12 / 18)

The default subject of nearly every essay: farmers in the global south facing yield loss from drought, heat, and water stress, and the technologies (seeds, irrigation, extension advice) that could offset it. It's the one constant across otherwise very different program pitches — agricultural economics, environment and resources, straight economics.

Cited: Columbia, Stanford E-IPER, Berkeley ARE, Cornell, Fletcher, Northwestern, NYU, Michigan

### 02. Remote sensing & satellite ML as the empirical backbone (14 / 18)

Satellite imagery, MOSAIKS-style embeddings, drone-based land classification, and mobile-phone traces appear as the default source of covariates and outcome proxies almost everywhere, not as a novelty but as infrastructure — the thing that makes every other idea on this list measurable at scale and low cost. Your own applied track record (the Berkeley Food Institute evapotranspiration model, the Colombia land-titling computer-vision pipeline, the wheat-yield thesis) is what makes this credible rather than aspirational.

Cited: Columbia, Faculty Alignment, Berkeley ARE, Cornell, MIT, Northwestern, Princeton, Stanford Supp 1

### 03. Digital credit & insurance for the underbanked (5 / 18)

The application layer that sits on top of themes 01 and 02: fusing geospatial and mobile data into credit scores and insurance pricing so farmers can borrow against a real risk profile instead of collateral they don't have. It's the narrowest and most concrete theme, and it's specifically the one the Columbia SoP is built around — pairing it with Daniel Björkegren's manipulation-robust prediction work and Jack Willis's crop-insurance and value-chain-finance research.

Cited: Columbia, NYU, Northwestern, Cornell, Faculty Alignment

### 04. Causal ML for scaling pilots into national policy (8 / 18)

A specific, recurring methodological stack: fuse RCT panel data with high-dimensional spatiotemporal covariates, estimate heterogeneous treatment effects with double-machine-learning or causal forests, pool related trials through hierarchical meta-analysis (explicitly modeled on CEGA's IDEAL framework), and feed debiased estimates into a Bayesian or general-equilibrium model as priors for out-of-sample prediction. This is the most technically developed idea in the whole set — it shows up with near-identical mechanics in half a dozen essays for different schools, which means it's a settled methodological identity, not a one-off pitch.

Cited: Berkeley ARE, MIT, Cornell, Northwestern, Princeton, Stanford Supp 1

### 05. Climate- and conflict-driven displacement (5 / 18)

Migration and forced displacement as the downstream consequence of the crises above — sharpened by direct experience in Ukraine and Colombia, and echoed in the Michigan and Princeton pitches on migrant integration and cash transfers. Alexander de Sherbinin's climate-forced-displacement work is named specifically in the Columbia faculty-alignment note, so the thread is already partly wired into your Columbia application even though it wasn't the headline there. **It is now** — see Directions below.

Cited: Michigan, Michigan Joint, Princeton, Fletcher, Faculty Alignment

### 06. Practitioner tools over papers alone (7 / 18, explicit)

A recurring commitment, not just a topic: reproducible codebases, an "Adaptation Atlas"-style interactive tool, in-silico policy experiments that let a World Bank or FAO practitioner plug in a location and get a recommendation. It shows up explicitly as a stated deliverable — not implied, but written out — in about a third of the essays, and implicitly in most of the rest.

Cited: Stanford Supp 1, Berkeley ARE, Cornell, NYU, Northwestern, Stanford E&R

> **The strand that doesn't fit the rest.** American University, the New School notes, and the free-form `Research Ideas.md` file describe a genuinely different research identity — post-Keynesian agent-based models, feminist and anti-imperialist critiques of development economics, non-parametric optimization (DEA, shape-constrained estimation) as an alternative to structural econometrics, and a standalone note questioning whether deep-learning global approximations quietly smooth over the ecological tipping points a causal-ML dissertation would need to respect. These aren't undeveloped ideas — the DEA and spectral-bias notes in particular are technically sharp — but they pull toward a heterodox, theory-first identity that sits at odds with the applied-causal-inference track that dominates the other sixteen essays. See Open Questions below for what to do with this before it costs you a year.

## 03. Promising directions for the dissertation

Reordered around the reputation you actually want: climate adaptation, migration, and cash transfers in conflict-vulnerable settings as the throughline, with the digital-finance and causal-ML work serving that agenda rather than standing as a separate pitch. All four still share one underlying toolkit — the same fused geospatial-plus-panel-data infrastructure — so building it once pays for every direction below.

### I. Climate adaptation, migration & cash transfers under conflict

*The flagship — what your reputation gets built on*

The piece none of the eighteen essays fully commits to, but that your actual career already does: what happens to climate adaptation and social-protection programming when the setting isn't just poor but actively insecure? Cash transfers, crop insurance, and resilience investments are designed and evaluated almost entirely in stable settings; Colombia, Ukraine, and South Sudan taught you that conflict changes who can be reached, what data can be trusted, and whether a program's effects hold once displacement starts. The core question: does investment in climate-adaptive resilience reduce the probability that a shock becomes a displacement event, and does that relationship change — or break down — once you condition on active conflict? Lead with this in every faculty conversation from here on; the other three directions become the evidence for it, not competitors to it.

**Columbia fit** — de Sherbinin's climate-forced-displacement work anchors it directly. It also reaches past your original faculty-alignment note into political science and conflict scholarship — see Outreach for names worth adding.

### II. Digital credit & insurance as adaptation infrastructure in fragile settings

*The applied instrument, narrowed to fit the flagship*

The manipulation-robust credit-scoring and insurance pitch from your actual Columbia SoP, narrowed on purpose: not smallholder farmers in the global south generally, but farmers in places where conflict has already disrupted markets, land records, or physical access — where remote sensing and mobile data aren't a convenience, they're often the only measurement available. That narrowing is a feature, not a loss for a dissertation chapter: it's the version of this project nobody in a standard agricultural-finance track is positioned to do, and it gives direction I a concrete instrument to study rather than an abstract claim.

**Columbia fit** — Björkegren's manipulation-robust prediction work is the direct methodological anchor; Willis's crop-insurance and value-chain-microfinance research is the applied complement; Sachs and Bajpai's e-agriculture and ICT-policy work gives it a policy audience beyond academic economics.

### III. A general toolkit for scaling pilots into national policy

*The connective methodology, and specifically necessary here*

The double-ML / causal-forest / hierarchical-meta-analysis / Bayesian-prior stack that recurs across six essays isn't tied to agriculture specifically — it's a general answer to "how do you responsibly turn a 400-household pilot into a national program." It matters more in conflict-affected settings than in stable ones: RCT panel data from fragile contexts is thin, unevenly measured, and rarely nationally representative — precisely the conditions hierarchical meta-analysis and debiased ML exist to handle. Built once as a reusable methods chapter, it powers directions I and II both.

**Columbia fit** — not directly tied to a named SIPA faculty member, which is worth treating as a real gap. Worth raising with your advisor about a methods committee member outside SIPA — economics or the Data Science Institute — if this becomes more than a supporting chapter.

### IV. Chatbot-elicited survey data in access-constrained settings

*The compact, publishable-first piece*

The "AI-powered mobile survey" detail from the Columbia SoP, treated as its own contribution and sharpened for the flagship: can an LLM-administered survey elicit richer, more truthful investment-decision data than a structured questionnaire, and does that advantage grow specifically where enumerator teams can't safely or reliably travel — the exact condition that defines conflict-affected fieldwork? That's a genuine methods contribution to humanitarian and displacement research, not just a data-collection detail. It's self-contained, methodologically crisp, and doesn't require years of panel data to say something real.

**Columbia fit** — the natural first paper to bring to Björkegren, and the most realistic candidate for an actual first dissertation chapter given the timeline below.

## 04. Faculty outreach

The five faculty named in your original faculty-alignment note are a starting list, not the full map — especially now that conflict and displacement are the headline rather than a secondary thread. Three tiers, sequenced: listen before you pitch.

### Tier 1 — already identified, deepen the relationship

- **Daniel Björkegren** — manipulation-robust prediction, AI & Development. The direct anchor for directions II and IV. *(SIPA / AI and Development Initiative)*
- **Jack Willis** — crop insurance, value-chain microfinance. The applied complement to direction II. *(Economics (Barnard) / SIPA-affiliated)*
- **Alexander de Sherbinin** — climate-forced displacement. The direct anchor for direction I, the flagship. *(CIESIN, Columbia Climate School)*
- **Jeffrey Sachs & Nirupam Bajpai** — e-agriculture, ICT policy for development. The policy-audience bridge beyond academic economics. *(Center for Sustainable Development)*

### Tier 2 — conflict & political-economy adjacent, new given the flagship

- **Page Fortna** — civil war, peacekeeping, conflict duration and recurrence. *(Political Science)*
- **Macartan Humphreys** — conflict, natural resources, and institutions in fragile states, with an experimental-methods bent that pairs well with your causal-inference toolkit. *(Political Science)*
- **Suresh Naidu** — political economy, labor, institutions — a useful theory anchor for the macro/institutional side of conflict-affected development. *(Economics / SIPA)*
- **Eric Verhoogen** — international development economics, informality, firm and market disruption. *(Economics / SIPA)*

Verify current titles, appointments, and availability against SIPA's, Political Science's, and Economics's live directories before emailing anyone in this tier — faculty rosters shift, and this list reflects general knowledge of the department rather than a check done today.

### Tier 3 — institutes and seminar series to scout, not a single name

- **International Research Institute for Climate and Society (IRI)** — climate risk and index insurance for smallholders; institutional lineage running through the R4 Rural Resilience Initiative. Directly relevant to direction II.
- **CIESIN** — de Sherbinin's home base; population, displacement, and vulnerability data infrastructure.
- **Saltzman Institute of War and Peace Studies** — the conflict-scholarship seminar series; the fastest way to find who at Columbia actually studies conflict beyond the four names above.
- **Data Science Institute — AI & Development Initiative** — Björkegren's methods community; likely home for direction III collaborators.
- **Mailman School — Program on Forced Migration and Health** — public-health-side displacement expertise; a good interdisciplinary bridge for direction I that sits outside economics entirely.

**Cadence:** September is for attending, not emailing — sit in on talks, keep a one-line log per event (who, what, where your interests overlapped). First meetings with Tier 1 in October–November, framed as learning about their work, not pitching yours. Tier 2 waits until December–January, once Project 01 or the evidence map exists to show. A second, more direct round in February–March raises summer RA work and second-year advising explicitly. Keep it in a simple spreadsheet — name, unit, event or paper, overlap note, meeting date, follow-up — it's the kind of low-effort tracking that makes six months of scattered conversations look like a deliberate search when you sit down to pick an advisor.

## 05. Month by month

September 2026 through May 2027, on top of coursework — not instead of it. Tags mark which lane each item belongs to: **research**, **outreach**, **portfolio**.

### September 2026

- **[research]** Set up a reference manager and reading log; open three literature lanes — climate adaptation & agriculture, forced displacement/conflict economics, cash transfers & social protection in fragile settings. Target 15–20 anchor papers per lane by month end.
- **[research]** Scope the open-source-conflict-data seminar's term project around the climate–conflict–displacement fusion idea (Project 02 below), so coursework and portfolio work are the same hours.
- **[outreach]** Attend, don't email — SIPA sustainable development seminar, Saltzman Institute's conflict series, one IRI or CIESIN talk. Log what you hear.
- **[portfolio]** Develop and publish personal website with bio, project page, and blogs; focused initially on Academic and Research Hubs
- **[hubs]** Finish most code for academic and research hubs, publish to Github, post projects on website
- **[fellowships]** Identify other fellowship opportunities, conference opportunities, etc.
- **[math thesis]** Begin revisions of math thesis (Project 06): refactor the R code (vectorize, deterministic covariance estimation) and rework the roughness penalty to second-order differences

### October 2026

- **[research]** Close first-pass literature maps; write one "gap statement" per lane — the sentence you'd say if a faculty member asked what's missing.
- **[research]** Start Project 01, the evidence map, cataloguing existing RCTs and quasi-experiments at the climate-adaptation × cash-transfer × conflict intersection.
- **[outreach]** First meetings — Björkegren and de Sherbinin — framed as learning about their work, not pitching yours.
- **[research]** Build out Project 02 (ACLED + IDMC + climate + cash-transfer program data fusion); midpoint check against the seminar's own milestones.
- **[portfolio]** Continue revising and posting about Academic and Research Hubs on website
- **[math thesis]** Continue revisions of math thesis, outreach to math faculty

### November 2026

- **[research]** Draft research-statement v0.1 — a living one-pager reflecting what's actually been learned this semester, distinct from the admissions SoP.
- **[outreach]** Meet Willis and Sachs/Bajpai; scout one Tier 2 talk (Fortna, Humphreys, Naidu, or Verhoogen).
- **[portfolio]** Publish Project 01 (evidence map) as a v1 — spreadsheet or simple dashboard is enough. First concrete artifact.
- **[research]** Finish and submit the conflict-data seminar term paper — this is Project 02's first full draft.
- **[research]** Start Project 04 (data fusion pipeline) as part of processing for Project 02
- **[portfolio]** Publish Project 02 as a GitHub repo plus short write-up.
- **[research]** Present informal 30-min talk to students at SusDev seminar
- **[fellowships]** Use academic and research hubs to apply for AI pedagogy fellowship

### December 2026

- **[research]** Draft the IRB protocol for the chatbot-survey pilot (Project 03) over break, so it's ready to submit day one of spring.
- **[research]** Build out Project 02 (ACLED + IDMC + climate + cash-transfer program data fusion) and determine what it would need to be to be a "full paper"
- **[outreach]** Finals period — skip new meetings, but send Tier 1 faculty you've met a short "here's what I built this semester" note with a link to Project 01. Low-pressure, high-signal.
- **[math thesis]** Implement data-driven λ selection (GCV/REML) and eigenvector-decay weighting; sharpen the thesis around the asymmetric-alternative power gap as the core result

### January 2027

- **[outreach]** First Tier 2 meetings, now with Project 01 and Project 02 to show instead of just intentions.
- **[research]** Complete revised Project 02 paper and distribute to faculty for feedback
- **[research]** Identify conference presentation opportunities for the Project 02 paper.
- **[portfolio]** Publish Project 04 (toolkit) once stable.
- **[math thesis]** Applied validation (Project 06) against Project 02/04 residuals now that the toolkit is stable; finite-sample simulations across n ∈ {50, 100, 500, 1000} in place of a full asymptotic proof

### February 2027

- **[research]** Run the Project 03 pilot once IRB clears; begin analysis.
- **[research]** Revisit the three lit-lane gap statements against a full semester of micro/macro/econometrics — sharpen the theoretical framing now that the toolkit exists to support it.
- **[outreach]** Ask one or two target faculty — likely de Sherbinin and a Tier 2 name — about summer RA or pre-doc-style work.
- **[research]** Continue revisions to Project 02.
- **[math thesis]** Finish thesis rewrite (Project 06); look into presentation opportunities

### March 2027

- **[research]** Finish the Project 03 write-up as a short methods note.
- **[research]** Draft the internal memo narrowing the four directions to the flagship plus one supporting thread — the decision Open Questions asks you to make.
- **[outreach]** Second-round "decision" meetings — bring the narrowed framing, ask directly about advising fit for second year.
- **[research]** Finish revisions to Project 02.
- **[portfolio]** Publish Project 03.

### April 2027

- **[research]** Present larger finalized Project 02 paper to faculty at SusDev seminar.
- **[portfolio]** Publish final Project 02 paper on website
- **[outreach]** Confirm summer plans — an RA line, fieldwork, or continuing one project — with an identified faculty mentor.
- **[portfolio]** Site now carries four finished projects, a lit-synthesis memo per lane, and a one-page research statement.

### May 2027

- **[research]** Wrap coursework; write a short end-of-year retrospective — what changed since September, what the flagship direction looks like concretely now. Useful for you and for whichever faculty member becomes your advisor.
- **[outreach]** Advisor fit should be substantially resolved heading into summer / second year.
- **[portfolio]** Final pass — every project links from the homepage with a one-line "why this matters" framed around the conflict-vulnerable climate/migration/cash-transfer throughline, not as disconnected exercises.

## 06. Self-contained projects for year one

None of these require a new RCT, years of field access, or anything touching sensitive USAID material — the constraint that would otherwise dominate a first-year timeline. Each is scoped to a semester or less, and each is built explicitly around the conflict-vulnerable climate/migration/cash-transfer throughline rather than as a generic methods demo.

### 01 — An evidence map: climate adaptation, cash transfers & conflict

A structured, public catalogue of existing RCTs and quasi-experimental evaluations sitting at the intersection of climate-adaptive agriculture, cash transfers/social protection, and conflict or forced displacement — coded by intervention type, setting, conflict-exposure level, method, and outcome, drawn from 3ie's, J-PAL's, and WFP's evaluation registries plus existing systematic reviews. This is the literature-gap exercise you need to do anyway, turned into a shareable artifact: the intersection itself is thin enough that a well-organized map of it is a genuine, citable contribution, not just a study aid.

| | |
|---|---|
| **Data** | 3ie / J-PAL / WFP registries, published reviews |
| **Output** | Public spreadsheet or dashboard + a "what's missing" memo |
| **Timeline** | Starts October, living document after |

**Risk:** Low — desk research, no IRB

### 02 — Climate shocks, conflict & displacement: a fused public-data study

Fuse ACLED conflict-event data, IDMC displacement figures, a climate-shock indicator (SPEI or CHIRPS-based drought measures), and public cash-transfer program locations (WFP/HDX) into a subnational panel, to test how climate shocks translate into displacement conditional on conflict intensity, and whether social-protection presence moderates that relationship. This is the term project for the open-source-conflict-data seminar, done properly enough to also stand alone — coursework and portfolio work sharing the same hours instead of competing for them.

| | |
|---|---|
| **Data** | ACLED, IDMC, SPEI/CHIRPS, WFP/HDX |
| **Output** | Seminar paper → working paper + reproducible notebook |
| **Timeline** | September 2026 – April 2027; NECR5250 term paper due November, extended into a full paper and presented at the SusDev seminar through spring |

This is direction I, made concrete and small, and direction III's fusion method proven on real data before there's a dissertation-scale dataset to apply it to.

**Risk:** Low — public data, no IRB

### 03 — Pilot: chatbot survey vs. structured survey, head to head

A small (n≈50–150) methods pilot administering both an AI-chatbot survey and a standard structured questionnaire to the same respondents on investment or displacement decisions, testing whether the chatbot elicits richer qualitative detail and holds up under manipulation-robustness checks in the spirit of Björkegren's work. Framing it explicitly around access-constrained settings — where an enumerator team may not be able to travel safely — is what turns this from a generic survey-methods exercise into evidence for direction IV.

| | |
|---|---|
| **Data** | New, small — partner NGO or panel sample |
| **Output** | Methods paper, candidate first dissertation chapter |
| **Timeline** | December 2026 – March 2027; protocol drafted in December, submitted in January, pilot runs once IRB clears |

The most direct way to open a working relationship with Björkegren in year one rather than year three.

**Risk:** Medium — needs IRB approval and a small budget

### 04 — Publish an open-source climate–conflict data-fusion toolkit

Package the ACLED/IDMC/climate/program-data fusion pipeline from Project 02 as a small, documented, reusable library rather than a one-off notebook — the "accessible tool for practitioners" goal that several of your essays name explicitly as a deliverable, done as a public artifact instead of a promise. It becomes the shared infrastructure under Project 02 and, later, direction I.

| | |
|---|---|
| **Data** | Same as Project 02, generalized |
| **Output** | Public GitHub package + short write-up |
| **Timeline** | November 2026 – January 2027; built alongside Project 02's processing pipeline, published once stable |

**Risk:** Low — engineering effort, not new research risk

### 05 — Optional — a short note resolving the heterodox-vs-mainstream question

A scoping essay, written for yourself and an advisor rather than for publication, that positions agent-based modeling, non-parametric/shape-constrained estimation, and causal-ML approaches against each other for the specific problem of scaling pilot interventions in fragile settings. Its job isn't to be a paper — it's to force the decision in Open Questions below onto paper before it gets decided by default.

**Risk:** Low — internal deliverable

### 06 — Math thesis rewrite: an asymmetric-aware omnibus normality test

Revise the existing penalized-GLS omnibus normality test (eigenvector-decomposed empirical process regression with a roughness penalty) around a sharper, more specific result rather than a general-purpose rewrite. Diagnostic work already shows the test underperforms Shapiro-Wilk by 10–20 points on asymmetric alternatives (gamma, chi-square), most likely because the first-difference roughness penalty forces artificial symmetry on the smoothed predictions. Reworking the penalty and the eigenvector weighting to be asymmetry-aware turns that weakness into the thesis's actual contribution — and it's motivated by exactly the heavy-tailed, skewed residual distributions that climate and agricultural-yield data produce, tying the math thesis directly to the applied toolkit behind directions II and III. Full sequencing lives in `math_thesis/rewrite/Gemini Plan for Thesis Revision.md`; validated, where possible, against Project 02's panel-model residuals and Project 04's toolkit output rather than synthetic data alone.

| | |
|---|---|
| **Data** | Simulated distributions (t, gamma, chi-square, GPD/GLD) for the core test; Project 02/04 model residuals for applied validation |
| **Output** | Revised thesis manuscript; a short empirical-validation note reusing Project 02/04 data |
| **Timeline** | September 2026 – February 2027: refactoring and calibration through the fall, applied validation once Project 04's pipeline stabilizes in January |

**Columbia fit** — a sharpened, asymmetry-aware omnibus test used to validate residuals in your own causal-ML pipeline gives direction III's "methods committee member outside SIPA" gap (economics or the Data Science Institute) something concrete to react to, rather than a hypothetical.

**Risk:** Medium — the full asymptotic-consistency proof is treated as optional/stretch for this cycle; a finite-sample simulation study across n ∈ {50, 100, 500, 1000} carries most of the credibility without committing to open-ended theory work on a four-month clock.

## 07. Two things worth resolving early

> **Heterodox identity vs. applied-causal-inference identity.** Sixteen of eighteen essays describe an applied-microeconomics, causal-inference, remote-sensing research program. Three sources — American, the New School, and the `Research Ideas.md` notes — describe a structurally different one: agent-based post-Keynesian modeling, feminist and anti-imperialist critique, non-parametric optimization as a rejection of structural econometrics. Both are real interests, but they call for different advisors, different committees, and arguably different departments. SIPA's Sustainable Development faculty — Björkegren, Willis, Sachs, de Sherbinin — sit solidly in the applied-empirical camp, which suggests the heterodox strand is better treated as a secondary intellectual interest (a second-year field paper, a reading group, a minor field) than as competition for the dissertation spine. Worth naming explicitly to your advisor rather than letting it surface as scope creep in year two.

> **Breadth of applications vs. one flagship thread.** Across eighteen essays the same toolkit gets pointed at credit scoring, crop insurance, cash transfers, migration, and foreign-aid policy design — five different applications riding the same causal-ML-plus-remote-sensing engine. That range was an asset for admissions, where each school wanted to see fit with its own faculty. It's a liability for a dissertation, which needs one flagship application to anchor around. Direction I — climate adaptation, migration, and cash transfers under conflict — is now that anchor; direction II (digital credit and insurance) becomes the concrete instrument studied inside it, and direction III (the general scaling toolkit) is the methods contribution that makes both possible.

1. **Start Project 02** (the climate–conflict–displacement fusion) in September — it's already your seminar's term project, so it costs no extra hours and produces the first real evidence for the flagship direction.
2. **Build Project 01** (the evidence map) in parallel — it's desk research, needs no approvals, and is the literature-gap exercise you need to do regardless, turned into something citable.
3. **Queue Project 03** (the chatbot pilot) for January so the IRB clock runs over winter break instead of eating into semester time.
4. **Have the heterodox conversation with your advisor in the first semester**, not the third — it's cheap to resolve now and expensive to resolve after a year of work has already leaned one way.
5. **Sequence Project 06's applied validation after Project 04 stabilizes** — reuse the toolkit's residuals instead of gathering separate data for the thesis, and treat the full asymptotic-consistency proof as optional/stretch for this cycle rather than a hard requirement.

---

Ground Truth — research planning memo
Sources: 19 files, research/independent-research/notes/processed_outputs
