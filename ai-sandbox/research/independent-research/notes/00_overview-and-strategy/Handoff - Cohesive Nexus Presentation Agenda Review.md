# Handoff for Claude: recover a cohesive nexus evidence agenda

*Prepared 2026-11-10. Review and brainstorm only. Do not edit the strategy, deck, tracker, or project plans in this pass; return a reasoned recommendation for the owner to review. The v3 strategy currently lives on `codex/nexus-presentation-strategy-v3` and has not landed on monorepo `main` as of this handoff.*

## Task

Review the original presentation argument, the critique and source checks, the newer nexus analysis, and the v3 strategy. Propose the most coherent framing for a research agenda about **how external causal and other evidence can be found, assessed, adapted, and used for decisions in prolonged or recurrent crises and the humanitarian–development transition**. Keep the agenda's research architecture and causal-transfer question visible, while making decision relevance an empirical question rather than an assumption.

The owner likes two changes made in the revisions: (1) identifying actual users, choices, time horizons, and evidence-use barriers, and (2) moving away from a live quantitative simulator that assumes linked data, identifiable target effects, and an already validated transport model. The owner thinks v3 has lost some focus, especially at slides 12 and 13. Slide 12 mentions structural breaks but no longer clearly advances the **causal transfer model**: how and why a source effect might fail to travel when a mechanism, delivery system, or population changes. Slide 13 shifts to resilience, anticipatory action, and risk finance as if they were a new research strand, without enough connection to the broader **evidence-for-decision-making** question or the preceding transport arc.

Cash transfers, anticipatory cash, and index insurance can be useful **use cases** for testing this framework because they pose observable timing, delivery, forecast, treatment, and outcome questions. Do not turn the agenda into a proposed study claiming to determine which cash or insurance approach is “best.” Do not assume a local planner is waiting for an RCT lookup during the immediate response window. Operational feasibility and rapid needs analysis matter, but corridor-level logistics optimization is a separate, adjacent agenda. A central empirical question is whether, for a specified revisable transition decision, external evidence adds value once local constraints and institutional discretion are known.

## Reading map

The relative links below resolve from this handoff file in `ai-sandbox/research/independent-research/notes/00_overview-and-strategy/`, inside the task worktree `C:\Users\theaa\ai-sandbox-master\.worktrees\codex-nexus-presentation-strategy-v3`. If v3 has since landed, use the main checkout's copy. The panel's separate repository exists in the **main checkout**, not this monorepo worktree.

### Read closely

1. [Original presentation strategy](Research%20Presentation%20Narrative%20-%20Humanitarian%20Transportability%20Pipeline.md), especially the executive question, 2×2, and slides 10–15. Recover its useful progression while checking overconfident claims.
2. [Original 15-slide Marp deck](presentation_slides.marp.md), to distinguish the narrative memo from the actual slide language and visual pacing.
3. [Long-form critique analysis](Humanitarian%20Evidence%20Agenda%20-%20Critique%20Analysis.md) and [claim/source verification](Humanitarian%20Evidence%20Agenda%20-%20Source%20Verification.md). Use the latter to avoid repeating unsupported platform, literature, or planner-behavior claims.
4. [First revised strategy](Humanitarian%20Evidence%20Agenda%20-%20Updated%20Presentation%20Strategy.md), which preserves three decision horizons but still emphasizes an acute-response opening.
5. [Nexus research focus analysis](Humanitarian%20Development%20Nexus%20-%20Research%20Focus%20Analysis.md), which makes prolonged-crisis adaptation the center and distinguishes the evidence-use interface from operational optimization.
6. [V3 presentation strategy](Humanitarian%20Evidence%20Agenda%20-%20Presentation%20Strategy%20v3.md), including its newly added JMMI decision and AINAA follow-up. Compare its slides 10–15 with the original and v2 slide sequence.
7. [Projects tracker](../../PROJECTS.md) for actual maturity and links: the compound-shocks panel is a reproducible context panel, `reprokit` is released, the evidence map is in brainstorming, transferability is planned, and the Bangladesh insurance replication has a geolocation gate. Verify current entries rather than treating the 2×2 as an integrated working system.

### Consult for specific claims or possible examples

- [Original critique transcript](<C:/Users/theaa/ai-sandbox-master/ai-sandbox/research/independent-research/notes/00_overview-and-strategy/humanitarian_evidence_research_transcript.md>), supplied by the owner and untracked in the main checkout (absent from this worktree). It contains useful questions and some incorrect or unverified specifics; the source audit above is the guide to those distinctions.
- [3R revision](Ground%20Truth%20-%20PhD%20Research%20Plan%20-%203R%20Revision.md) and [trial transportability follow-up](../03_rct-transportability/Follow-up%20-%20Data%20Availability%20and%20Transportability%20Critique.md) for the resilience/response/recovery framing and data/identification limits.
- Panel repo's [JMMI feasibility review](<C:/Users/theaa/ai-sandbox-master/ai-sandbox/research/independent-research/projects/compound-shocks-panel/docs/feasibility/jmmi-api-2026-11-09.md>): a concrete example of a geographically joinable source that still has coverage, construct, unit, and reuse gates. JMMI is not a production panel input.
- [Elrha's *From knowing to doing*](https://www.elrha.org/resource/from-knowing-to-doing-evidence-use-in-the-humanitarian-sector) for the evidence-use and researcher–practitioner interface, and [Elrha's AINAA project page](https://www.elrha.org/projects/artificial-intelligence-needs-assessment-assistant-ainaa) as a rapid needs-analysis comparator. The AINAA page lists intended outputs but no published delivery updates; do not treat it as proof of a validated tool.

## Questions to resolve in the brainstorm

1. What is the **one-sentence agenda** and overarching research question? Does the core object of study become an evidence-adaptation process, a conditional causal-transfer model, an evidence-use process, or a tightly specified combination? Name what is genuinely new and what remains an open hypothesis.
2. What is the logical chain from the 2×2 assets through evidence appraisal and local context to conditional transfer and actual decision use? Which parts can be standalone outputs? Where must the chain stop because treatment, outcome, location, or implementation data are missing?
3. How should slides 10–15 progress? In particular, design a slide 12 that makes **structural breaks a test of causal transportability**, including treatment version, mechanism, institutional delivery, market or payment links, displacement, and possible interference. State what a DAG or other model can diagnose and what it cannot identify. Should slide 13 return to a **method selection and validation** question, as in the original, while moving resilience and risk finance to examples or open questions? If you recommend another arrangement, explain the bridge from slides 11 to 14.
4. How can the deck demonstrate relevance to a real, revisable nexus decision without implying that researchers can rank cash, in-kind aid, insurance, or combined packages from currently available data? What would a modest evidence product look like, and what observation would show it helped or failed to help?
5. Which empirical use case best illustrates the framework without becoming the whole agenda? Compare cash/social protection, anticipatory action, insurance, and perhaps a different prolonged-crisis transition case against data feasibility, decision access, and clarity of the transfer question. Mark claims requiring new partners, data access, or validation.
6. Which original-slide claims should be retained, softened, or removed? Pay particular attention to asymptotically complete corpora, outlier-trial validity, empirically calibrated priors, universal reliable impact ranges, novel-locality effects, neural causal tools, and the simulation-response exercise. Use the source verification note and tracker to separate demonstrated assets from plans.

## Requested output

Please return a **long-form review and brainstorm**, not a rewritten strategy or deck. Include:

- A concise diagnosis of the current focus problem and the strongest through-line worth keeping.
- Two or three plausible agenda framings, with tradeoffs and a recommended one.
- A proposed 15-slide argument map, giving extra detail for slides 10–15 and explicit transitions among them. Mark what returns from the original, what v3 contributes, and what should move to speaker notes or future work.
- A short table of major claims or methods with the evidence/data gate that would make each defensible, and a list of unresolved owner choices.
- A smallest credible next research step that tests the agenda's motivating claim without prematurely promising a transport estimator, live simulator, or “best intervention” result.

Distinguish **verified project behavior**, **plausible interpretation**, and **new proposal**. Cite the relevant local document and primary external source for factual claims. Ask the owner to choose a framing before editing the deck or selecting an empirical study. Keep project approvals and the JMMI production-integration gate unchanged.
