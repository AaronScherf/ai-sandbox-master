# Website page readability revisions — revised editorial guide

Prepared on 2026-10-15 following a review of all 38 substantive pages:
28 project pages and 10 blog posts. Nine unpublished HugoBlox template
examples remain excluded. This is a new companion to
[the original tracker](website_page_readability_revisions.md); that file is
preserved as the earlier proposal.

The original ranking used website commit `88124e4`. This revision uses the
local website content at `e10f9b3`, including subsequent changes to Journal
Discovery and Concept Graph. The review examined page source text and selected
package documentation and implementation details. It did not independently
reproduce project results, conduct reader testing, or inspect rendered mobile
layouts. Recheck current source material when each page is revised.

The objective is clear, engaging writing that sounds like Aaron explaining
his own work to an interested person without a programming background. The
document gives instructions for a later editing pass; creating it does not
mark any website page revised or authorize publication.

## 1. Audience and purpose

Assume the reader understands studying, research, or job applications but
does not know programming, AI terminology, or this project's internal names.
Adapt the audience to the page: students for study tools, researchers for
literature tools, applicants for Resume Manager, and an interested general
reader for the theses and development workflow.

The opening should make three things easy to understand:

1. What practical problem prompted the project?
2. What can someone do with it now?
3. What concrete example or result makes that useful?

Explain the benefit before the file format or technique. For example, begin
with making handwritten notes searchable; introduce Markdown afterward if
the format matters. Do not require readers to understand a "corpus," an
"index," or "RAG" before they understand why the project exists. Plain
alternatives include "collection of course materials," "search catalog,"
and "answers based on passages from my course materials."

Do not force every project into the Academic Hub ecosystem. Explain genuine
connections when they help the reader; a thesis or resume tool can stand on
its own. Distinguish a connection that works today from an intended future
integration.

## 2. Structure by page type

Replace the original fixed percentages with a flexible order of emphasis.
Spend most of a project page on its use, an example, its main steps, and the
evidence for its current results. Technical decisions belong where they help
explain a benefit, tradeoff, or limitation. Bug history and future plans are
optional; neither needs a quota.

| Page type | Primary job | Useful structure |
| --- | --- | --- |
| Project page | Explain current capabilities, evidence, and limits | Problem and concrete example; main steps; one or two revealing decisions; scoped results and limitations; a useful next link or documented next step if needed |
| Overview page | Orient readers and help them choose where to go | One connected scenario; tools grouped by the reader's task; clear descriptions of what is available and what remains limited |
| Blog post | Tell a dated story about an experience or development | Motivation or observation; a few meaningful events; what changed or was learned; a link to current project details |

Do not turn all pages into the same five-section template. A short converter
may need only a few paragraphs; a substantial research project may need a
methods section. A finished thesis need not conclude with speculative plans.

For historical posts, retain the original perspective. Add a dated update or
a short historical cue when present-tense descriptions would mislead a new
reader. Link to the current project page instead of silently rewriting the
past to match today's implementation.

### Examples should carry the explanation

Prefer one actual example that the page follows from input to useful output:
a handwritten equation becoming searchable, a question finding a relevant
textbook passage, or a resume bullet tailored without changing its facts.
Use short excerpts rather than whole documents. Clearly label invented
demonstrations as illustrative; never present them as actual runs, personal
experiences, or evidence of a capability that has not been established.

A generic "In plain language" paragraph followed by the original technical
opening is insufficient. Integrate the accessible explanation into the whole
page and remove redundant introductions.

### Select development history for its explanatory value

Ask which difficulty best explains why the project works this way. Usually
one example is enough. Resume Manager's change from AI extraction to a
conventional parser is a strong story because it explains a useful and
surprising decision. A complete inventory of YAML errors is unnecessary.

Move detailed failure chronology, commands, thresholds, model names, and
implementation mechanics into linked READMEs or status records unless the
reader needs them to understand the result. Keep useful tradeoffs, including
cost, speed, hardware, accuracy, and human review, in plain language. Do not
present routine implementation as unusual innovation.

## 3. Voice and reading experience

Use first person for Aaron's documented choices, observations, preferences,
and experiences. Preserve what he actually found interesting. Do not invent
an anecdote, frustration, opinion, or learning benefit to make the writing
sound personal. If a personal observation is missing, draft the supported
explanation and identify the missing detail for the author.

Avoid promotional claims and generic concluding lessons. Prefer a concrete
observation over phrases such as "the power of hybrid system design" or
"a unified knowledge ecosystem." Describe what improved rather than
announcing that the project is robust, seamless, innovative, or transformative.

Watch for repeated rhetorical habits across the site: "real," "genuine,"
"silently," "confirmed," bugs repeatedly "surfacing," and paragraphs ending
with "Part of Academic Hub." These words are not banned, but repetition can
make distinct projects sound mechanically generated. Vary the organization
because the stories differ, not merely by replacing words with synonyms.

Use familiar verbs, specific subjects, and short paragraphs, usually two to
four sentences. Vary sentence length enough for natural rhythm. Split long
chains of qualifications, parentheses, and side explanations. Explain an
essential term near its first use; omit unnecessary terminology rather than
building a glossary into every page.

Suggested lengths are starting points, not quotas:

- Substantial project: roughly 400–800 words; exceed this only when the
  additional material helps the intended reader.
- Simple project: roughly 150–350 words, or shorter when sufficient.
- Overview: enough to orient and navigate, without repeating component pages.
- Blog: let the story determine length; preserve effective short updates.

The original "two or three pages" limit is too ambiguous for a mobile site.
Use informative subheadings on longer pages and inspect the rendered result.
Do not pad a short page to meet a range. Do not make every sentence equally
short in pursuit of readability.

Include the title, summary or listing excerpt, captions, and link labels in
the editorial pass. A technical project name can have a plain-language
subtitle or opening explanation. Preserve existing URLs unless a separate
change has been authorized.

Before finishing, read the prose aloud and ask: "Would I say this, and does
it express what I actually found interesting?" The goal is authentic author
judgment and voice, not artificial informality, deliberate mistakes, or
optimization for an AI-text detector.

## 4. Evidence, currency, and claims

Read the current package README and relevant recent status records before
reusing technical claims. Use implementation details to resolve a specific
discrepancy where needed; flag unresolved questions instead of guessing.
Website copy alone is not authoritative evidence of current behavior.

Keep these evidence levels distinct:

| Evidence available | What the page may establish |
| --- | --- |
| Implemented behavior | The capability exists in the code within its documented scope |
| Passing automated or fixture tests | The tested cases passed; this does not establish successful live use |
| A successful run on actual material | The stated result occurred for that input and configuration |
| Repeated use over time | Sustained reliability or practical value within the observed scope |

Give important results their scope and, where relevant, date, sample size,
conditions, and source. Explain what a number means to the reader. An old
count is a dated checkpoint, not a current total. Cost and timing measurements
need the workload and stage they describe; local execution avoids some API
charges but still uses computing resources.

Output volume is not proof of accuracy or learning. Extracting 196 questions
does not establish 196 correct extractions or improved study outcomes.
Citations, source-image comparison, successful code execution, and agreement
between model calls each check something narrower than overall correctness.
Use precise descriptions of what was checked; do not promise that automated
verification eliminates bad edits or wrong answers.

Describe meaningful limitations beside the relevant capability, rather than
collecting every qualification at the end. Avoid repeating broad disclaimers
when a specific limitation explains the issue better. Planned work must be
documented and clearly identified as planned; do not invent a roadmap to fill
a conclusion. If no suitable result or next step is supported, omit it.

### Verified discrepancies to resolve during rewriting

These findings were checked during the review. Verify them again against the
version used for the editing pass.

| Page | Finding and required correction | Supporting local source |
| --- | --- | --- |
| Visualization Sub-Agent | The page describes local, unpaid generation, but the default generation backend is Gemini and Ollama is optional. Update the account of cost and where processing runs. Successful chart execution does not establish mathematical suitability. | [Visualization README](../../agent/viz/README.md) and [backend selection](../../agent/viz/llm_fallback.py) |
| Problem Corpus Extraction | The page's closing implies that the stored bank already feeds problem generation. The package explicitly stops at producing the bank; integration is later work. | [Problem Corpus README](../../agent/problem_corpus/README.md) |
| Commute Podcasts blog | The claim that editing one section regenerates only its episode conflicts with whole-source hashing: changing a note regenerates all its episodes. "9 clean, 15-minute" episodes also conflicts with the post's own 62-minute exception. | [Audio README](../../audio_generator/README.md), [pipeline](../../audio_generator/pipeline.py), and [hashing](../../audio_generator/state.py) |

Other entry-specific checks below are questions to resolve or distinctions
to preserve, not claims that every underlying discrepancy has already been
investigated. For example, verify native Word input before advertising it;
do not infer ingestion support from a migration script handling `.docx` files.

## 5. Links and visuals

Link related projects to their public website pages. Link source code,
READMEs, and status records to public GitHub URLs when available. The original
instruction to use GitHub URLs for every project link would unnecessarily
send general readers away from the explanatory website pages. Published copy
must not contain local filesystem links. Relative documentation links in
this internal guide are for editorial reference, not text to paste into the site.

Explain a dependency only when it helps the reader understand the workflow.
Avoid ending every page with the same list of component links. Give links
descriptive labels, and check that destinations are public and appropriate
for the reader. Do not expose private course materials or personal documents
through examples or screenshots.

During the prose pass, use `[[Insert Image: Description]]` only when a visual
would explain something more clearly. Specify what the visual shows and what
the reader should learn. For example:

`[[Insert Image: Side-by-side crop of an approved handwritten equation and its searchable transcription; highlight the preserved square-root symbol so the reader can compare source and output.]]`

Prefer real output screenshots and simple explanatory diagrams over decorative
generated images. Describe visuals in this pass; generate or capture them in
a later authorized pass. Replace or remove every placeholder before publication.
Final visuals need captions, alt text, readable mobile labels, and sufficient
context for a reader who cannot see the image. Use no visual where a sentence
would explain the point more clearly.

## 6. Editing and completion procedure

Work in the order below unless a changed page or source finding warrants a
documented adjustment. Treat page-specific narrative suggestions as flexible;
factual accuracy and the shared audience goals take precedence.

The website is a separate repository at
`ai-sandbox/personal-website/AaronScherf.github.io`. This tracker belongs to
the outer monorepo. An outer worktree does not isolate website edits. Follow
the [workspace worktree procedure](../../../../docs/WORKTREE_WORKFLOW.md)
and read the website checkout's own agent and editorial guidance before
editing pages. Revising this guide does not start the website rewrite batch.

For each page:

1. Read its current source and relevant supporting material. Record the
   source version and unresolved factual questions in the editing handoff.
2. Apply the indicated edit scope. Draft the useful explanation and example
   first, then select only the technical detail that earns its place.
3. Check claims, evidence levels, dates, costs, examples, related-page links,
   and consistency with neighboring pages. Preserve historical context.
4. Review the complete page, including title, summary, captions, and metadata.
   Preserve required frontmatter and existing publication status.
5. Preview at a narrow/mobile width as well as desktop. Check paragraphs,
   tables, equations, links, images, and listing excerpts. Run the site's
   documented build check for the revision batch and report any unavailable
   validation accurately.
6. Review voice with the author, especially newly drafted first-person
   passages. A reader should be able to explain the purpose, intended user,
   and main limitation from the opening and a skim.
7. Check off the entry only after the revision and required reviews are
   complete. Record the completion date, website commit, source evidence,
   and validation outcome beneath the entry. If visuals, author review, or
   factual checks remain pending, leave it unchecked and name the remaining
   work. Completion of editing is distinct from publication approval.

All entries below are initially unchecked. Suggested completion notation:

`Completed: YYYY-MM-DD; website commit: ...; evidence: ...; preview/build: ...; author review: ...`

## 7. Ranked revision queue

Priority reflects difficulty for a general reader and the extent of rewriting
needed, not project quality or a measured comprehension score. Broad tiers
are more defensible than small differences between adjacent ranks. The two
longest pages contain roughly 1,700–1,800 words each, with paragraphs approaching
or exceeding 300 words. They need restructuring, not just shorter openings.
Journal Discovery has grown since the original ranking; the updated Concept
Graph page is substantially clearer and needs less intervention.

Each entry retains its original rank for traceability. Scope labels mean:

- **Substantial rewrite:** reorganize the explanation and substantially reduce
  technical chronology; adding an example alone is insufficient.
- **Targeted revision:** retain useful material but fix a particular framing,
  example, organization, or claim. Some overview restructuring fits here.
- **Light edit:** make a small improvement or correction; do not lengthen an
  effective short page to satisfy the general structure.

### 01. Notes Transcription Pipeline

- [ ] [Notes Transcription Pipeline](https://aaronscherf.github.io/projects/academic-hub/notes_transcription/)
- **Scope:** Substantial rewrite. **Original rank:** 01.
- Follow one source from handwriting or slides to searchable text and a
  useful study task. Explain why conversion matters before introducing
  Markdown, indexing, or AI retrieval. Show supported inputs and outputs;
  verify direct Word-file support separately from Word-exported PDFs.
- Explain the choice between ordinary extraction and AI transcription in a
  few steps. Keep one revealing correction example and a scoped result.
  Move most downstream verification detail to Notes Post-Processing, and
  replace the long routing and bug chronology with a brief account of current
  behavior and limits. Describe recent changes through their practical effect.

### 02. Marker PDF Conversion

- [ ] [Marker PDF Conversion](https://aaronscherf.github.io/projects/academic-hub/marker_conversion/)
- **Scope:** Substantial rewrite. **Original rank:** 02.
- Explain why ordinary PDF search is insufficient for the intended study
  workflow. Show preserved equations, figures, or page references and what
  they let a reader find or check. Describe temporary cloud hardware and the
  cost tradeoff before setup details.
- Remove duplicated testing summaries and most provisioning, deduplication,
  and recovery chronology. Retain the limited scope of actual validation.
  Keep the statement about personal educational use and authorized source
  PDFs brief; do not imply that personal use alone establishes permission.

### 03. Journal Discovery Pipeline

- [ ] [Journal Discovery Pipeline](https://aaronscherf.github.io/projects/ai-research-assistant/journal_discovery/)
- **Scope:** Substantial rewrite. **Original rank:** 07.
- Follow one research topic through finding candidates, selecting relevant
  papers, obtaining available full text, and adding it to a searchable library.
  Distinguish papers found from papers downloaded and papers actually read.
- Explain automated access and the ordinary user-led browser handoff briefly.
  Replace the service inventory and debugging narrative with links. Reconcile
  older automatic-correction prose with newer human-reviewed classification
  proposals by identifying which operation does what. Keep current results
  scoped, and explain the unresolved loss of information from charts where
  relevant without implying every paper is transcribed losslessly.

### 04. Visualization Sub-Agent

- [ ] [Visualization Sub-Agent](https://aaronscherf.github.io/projects/academic-hub/visualization/)
- **Scope:** Substantial rewrite. **Original rank:** 04.
- Center the explanation on one plot and what changing or inspecting it helps
  a student understand. Explain templates and generated charts afterward.
- Correct the default-backend account using the evidence above. Distinguish
  code running successfully from the chart representing the right concept
  correctly. Compress timeout, retry, example-store, and subprocess history;
  describe safeguards precisely without presenting execution isolation as a
  comprehensive security sandbox. Keep the actual combined-report validation
  status current rather than carrying forward an obsolete test limitation.

### 05. Source Indexer

- [ ] [Source Indexer](https://aaronscherf.github.io/projects/academic-hub/source_indexer/)
- **Scope:** Substantial rewrite. **Original rank:** 05.
- Follow a specific question to a relevant document and then to a passage.
  Explain document cards as catalog records and show how another study tool
  uses the result. Introduce tagging and passage retrieval through this example.
- Keep one lesson about grouping related material and remove most tag-debugging
  detail. Present old corpus counts as dated checkpoints. Explain related-note
  matching and repair limits briefly rather than presenting all maintenance
  mechanisms before the reader understands search.

### 06. Resume Manager

- [ ] [Resume Manager](https://aaronscherf.github.io/projects/resume_manager/)
- **Scope:** Substantial rewrite. **Original rank:** 03.
- Show a factual before-and-after bullet for a particular kind of job,
  explaining what changed and what stayed fixed. Establish the master resume,
  job description, review, and final document before discussing file schemas.
- Make the switch from AI extraction to a conventional parser the central
  engineering lesson, with its measured benefit and scope. Remove the long
  parser-error inventory. Explain what automated checks protect and what the
  author must still review; fixed names and dates do not establish that every
  rewritten bullet preserves all meaning or facts.

### 07. Video Lecture Notes

- [ ] [Video Lecture Notes](https://aaronscherf.github.io/projects/academic-hub/video_notes/)
- **Scope:** Substantial rewrite. **Original rank:** 06.
- Show a short finished note beside the lecture it summarizes. Explain the
  steps from video audio to transcript to combined notes in ordinary language.
- State that reliable per-concept timestamp citations remain incomplete.
  Reduce the context-window investigation to the problem of omitted lecture
  content and how it was addressed. Preserve the limited trial size and
  distinguish a tested subset from full-playlist validation. Do not describe
  desired citation behavior as an observed success.

### 08. Problem Generation Sub-Agent

- [ ] [Problem Generation Sub-Agent](https://aaronscherf.github.io/projects/academic-hub/problem_generation/)
- **Scope:** Substantial rewrite. **Original rank:** 09.
- Show one practice question, its requested technique, and what the checking
  step examines. Explain how course examples influence style and difficulty.
- Make clear that another model call can repeat the first call's mistakes,
  and retrieved examples can steer a question off topic. Summarize the backend
  choice through measured tradeoffs rather than every failed attempt. Keep
  current retrieval examples distinct from the separately extracted problem
  bank, whose integration is not established.

### 09. Tutor Diagnosis & Hint Generator

- [ ] [Tutor Diagnosis & Hint Generator](https://aaronscherf.github.io/projects/academic-hub/tutor_diagnosis/)
- **Scope:** Substantial rewrite. **Original rank:** 08.
- Replace the command tour with a short student attempt, a hint, a revision,
  and the remaining uncertainty. Explain why course-specific feedback matters.
- Remove sweeping assertions about how all general AI assistants behave.
  Describe rubric scores as model feedback rather than instructor grades.
  Explain a second solution as a comparison to inspect, not an authoritative
  verdict. Distinguish this tool from the separate Socratic Tutor and make
  course-grounded versus general hints understandable.

### 10. RAG Analysis

- [ ] [RAG Analysis](https://aaronscherf.github.io/projects/academic-hub/rag_analysis/)
- **Scope:** Substantial rewrite. **Original rank:** 10.
- Show a question, a brief answer, and a readable source reference. Explain
  what the reference lets the student check without treating its presence as
  proof that the answer is correct. Introduce retrieval through this example.
- Move stateless-function design and query reformulation later, retaining only
  what helps explain a practical benefit. Clearly distinguish running-session
  conversation, saved records, and what is available after restarting. Keep
  ungrounded answers and narrow retrieval coverage visible as specific limits.

### 11. Obsidian Git Sync

- [ ] [Obsidian Git Sync](https://aaronscherf.github.io/projects/academic-hub/obsidian_git_sync/)
- **Scope:** Substantial rewrite. **Original rank:** 11.
- Open with taking notes on a tablet and finding them on a laptop. Use a small
  comparison of what syncs and what stays elsewhere, explaining the benefit
  for storage and responsiveness. Define the apps only as needed.
- Separate the current sync setup from retired approaches. Keep one incident
  if it explains a present choice, and move most duplicate-note matching detail
  to Source Indexer. Verify relocation work before presenting it as either
  complete or still planned. Retain the manual plugin-code update limitation.

### 12. Research Notes Conversion

- [ ] [Research Notes Conversion](https://aaronscherf.github.io/projects/ai-research-assistant/research_notes_conversion/)
- **Scope:** Substantial rewrite. **Original rank:** 12.
- Explain why a researcher would search old essays and research ideas
  alongside papers. Show a short conversion example and a paragraph reference
  that helps locate the source.
- Reduce punctuation escaping, frontmatter, and classification fixes to one
  useful lesson about reusing the existing search tools. Explain the present
  input and manual workflow clearly. Keep Google Drive ingestion and a broader
  literature-review workflow identified as planned unless new evidence
  establishes them. Use only appropriate excerpts from personal material.

### 13. Turning Dense Math Notes into Commute Podcasts

- [ ] [Turning Dense Math Notes into Commute Podcasts](https://aaronscherf.github.io/blog/audio_generator_podcasts/)
- **Scope:** Substantial rewrite. **Original rank:** 18.
- Rebuild the post around the listening experience and one development
  surprise, such as discovering that a technically valid recording was too
  long to navigate comfortably. Use an actual listening observation if one
  is available; do not assume generated audio was useful in practice.
- Correct episode lengths and regeneration behavior as recorded above.
  Separate formula-translation time from speech-synthesis and total production
  time. Remove generic lessons about hybrid design and most stage-by-stage
  engineering detail. A short formula-to-speech example can demonstrate the
  benefit more effectively than a long benchmark table.

### 14. Notes Post-Processing

- [ ] [Notes Post-Processing](https://aaronscherf.github.io/projects/academic-hub/postprocess_notes/)
- **Scope:** Targeted revision. **Original rank:** 14.
- Lead with a square-root symbol becoming a plausible-looking `p`. Explain
  the process as flagging suspicious text and comparing it with the original.
  Show the source and corrected line if an appropriate example is available.
- Cut the model-theory inventory. Keep false positives and their cost
  understandable. Correct wording implying that automated image comparison
  eliminates the possibility of a bad edit; it provides another check, with
  its own limits. Connect this page to transcription without duplicating its
  full history.

### 15. Problem Corpus Extraction

- [ ] [Problem Corpus Extraction](https://aaronscherf.github.io/projects/academic-hub/problem_corpus/)
- **Scope:** Targeted revision. **Original rank:** 15.
- Show a readable question card with its source and a clear distinction
  between a student's attempt and an answer key. Explain the value of turning
  scattered exercises into a reusable collection before describing storage.
- Scope the 196-question result to its recorded run and separate extraction
  completion from accuracy. Correct the implication that the bank already
  feeds generation. Explain present output and intended integration separately,
  and shorten the API-rate-limit narrative.

### 16. Audio Generator

- [ ] [Audio Generator](https://aaronscherf.github.io/projects/academic-hub/audio_generator/)
- **Scope:** Targeted revision. **Original rank:** 16.
- Describe what the listener receives and show how one formula becomes
  speakable language. Explain the local/cloud choice through cost and waiting
  time rather than an inventory of model routing and worker counts.
- Distinguish note episodes from textbook handling; retain the long-section
  limitation and accurate regeneration behavior. Recheck the statement that
  the intended summary pipeline does not exist against the current summary
  and study-guide tools, without assuming their integration is complete.
  Separate producing audio from evidence that it improves study.

### 17. Multi-Agent Development Workflow

- [ ] [Multi-Agent Development Workflow](https://aaronscherf.github.io/projects/multi_agent_project/)
- **Scope:** Targeted revision. **Original rank:** 13.
- Follow one actual task handoff and the human decisions involved. Explain
  isolated working copies before introducing Git worktrees, then describe why
  isolation and a designated integrator help avoid conflicting edits.
- Update Gemini's role against the current routing convention. Present agent
  assignments and memory assumptions as this workspace's configuration and
  choices, not universal product capabilities. Preserve the limits: conventions
  depend on participants following them and do not eliminate merge conflicts.

### 18. Journal Article Transcription

- [ ] [Journal Article Transcription](https://aaronscherf.github.io/projects/ai-research-assistant/journal_article_transcription/)
- **Scope:** Targeted revision. **Original rank:** 17.
- Start with finding an article's argument or result after conversion. Explain
  what survives conversion and what needs checking, including information
  carried by figures rather than tables or ordinary text.
- Keep reuse of the notes converter as one useful engineering choice. Move
  renderer names and routing thresholds out of the main narrative. Preserve
  the distinction between a pricing comparison and a measured accuracy
  comparison, and avoid describing article conversion as generally lossless.

### 19. Academic Hub overview

- [ ] [Academic Hub overview](https://aaronscherf.github.io/projects/academic-hub-overview/)
- **Scope:** Targeted revision. **Original rank:** 27.
- Start with one connected study scenario. Group all components by the
  reader's task: prepare materials, find information, study and practice, or
  maintain the collection. Include newer projects in those groups rather than
  collecting them in an undifferentiated closing paragraph.
- Replace technical link descriptions with benefits. Keep descriptions short
  and distinguish tools available today from those with limited validation or
  pending integration. The overview should help a reader choose a next page,
  not repeat the implementation vocabulary of every component.

### 20. Novel Omnibus Normality Test

- [ ] [Novel Omnibus Normality Test](https://aaronscherf.github.io/projects/math_thesis/)
- **Scope:** Targeted revision. **Original rank:** 21.
- Explain the question as whether data depart from a bell-shaped distribution
  and why someone might want to check. State the mixed comparison results
  before explaining the statistical construction. Define power as the ability
  to detect departures in the tested circumstances.
- Verify broad claims about Shapiro–Wilk against the thesis. Preserve sample
  size, simulation conditions, and proof-of-concept status. A new method is
  not necessarily a generally superior one. Link derivations and implementation
  details rather than making them prerequisites for understanding the page.

### 21. Wheat Yield Prediction

- [ ] [Wheat Yield Prediction](https://aaronscherf.github.io/projects/wheat_yield_prediction/)
- **Scope:** Targeted revision. **Original rank:** 26.
- Lead with the question of which wheat varieties perform well where field
  trial information is limited. Explain the evaluation setting and what the
  models were compared against before listing algorithms and data sources.
- Translate R² carefully; it does not mean "82% accurate." Keep results tied
  to the evaluated sample and distinguish predictive performance from observed
  benefits to farmers or deployment in new regions. Preserve the restricted
  pedigree-data limitation when discussing reproducibility.

### 22. Socratic Tutor

- [ ] [Socratic Tutor](https://aaronscherf.github.io/projects/academic-hub/socratic_tutor/)
- **Scope:** Targeted revision. **Original rank:** 24.
- Use an actual or clearly illustrative short exchange to explain how the
  system controls tutoring behavior. Introduce session tracking through its
  value to the learner before CLI commands, event logs, or state machines.
- Put the observed difficulty teaching unfamiliar material near the benefit
  statement. An idealized exchange must not imply that this limitation has
  been solved. Distinguish tested session rules from good teaching observed
  in use, and keep the scope of the two live sessions clear.

### 23. Corpus Health

- [ ] [Corpus Health](https://aaronscherf.github.io/projects/academic-hub/corpus_health/)
- **Scope:** Targeted revision. **Original rank:** 19.
- Follow a missing or stale search passage through discovery, owner review,
  permitted repair, and a final check. Explain how recurring findings retain
  their decisions without leading with ledger or locking terminology.
- Keep the narrow repair scope visible and separate reviewing from repairing.
  Distinguish a scheduler trial from established unattended reliability; a
  large finding count is not a validated error count. Recheck the trial's
  status before repeating its original dates as current work.

### 24. Project Steering

- [ ] [Project Steering](https://aaronscherf.github.io/projects/academic-hub/project_steering/)
- **Scope:** Targeted revision. **Original rank:** 20.
- Follow one item from a crowded to-do list into a reviewed priority. Explain
  what the owner decides and what the software proposes. Make clear that
  reviewing or ranking a task does not start its implementation.
- Treat 69 parsed tasks as scan-coverage evidence, not evidence that priorities
  or assignments are correct. Explain changed-task handling and scheduling
  status briefly. Preserve the page's short length rather than expanding
  into scoring mechanics and versioned-report details.

### 25. Study Guide Pipeline

- [ ] [Study Guide Pipeline](https://aaronscherf.github.io/projects/academic-hub/study_guide_pipeline/)
- **Scope:** Targeted revision. **Original rank:** 23.
- Compare a short draft passage with a more useful reviewed revision. Explain
  what the student supplies, which sources are selected, and where a person
  reviews the work. Translate source planning and provenance into ordinary
  descriptions of materials chosen and passages used.
- Retain the observation that early guides lacked depth or coverage. Do not
  imply that citations or a successful generation run establish exam readiness.
  Explain the relationship to Summary Enhancement without duplicating that
  page or turning this one into a command sequence.

### 26. Summary Enhancement

- [ ] [Summary Enhancement](https://aaronscherf.github.io/projects/academic-hub/summary_enhancement/)
- **Scope:** Targeted revision. **Original rank:** 22.
- Show what expansion adds: a missing explanation, connection, or worked
  example. Distinguish expanding an existing summary from the broader Study
  Guide Pipeline that plans, drafts, and revises a guide.
- Explain why the additional material helps without treating length itself
  as improvement. Keep the limits of citation-label checks and the need to
  inspect worked examples. Use the current interface as the source of truth
  when older status examples differ, and preserve this page's concise scope.

### 27. AI Research Assistant overview

- [ ] [AI Research Assistant overview](https://aaronscherf.github.io/projects/ai-research-assistant-overview/)
- **Scope:** Targeted revision. **Original rank:** 29.
- Use one literature-review question and three plain steps: find candidate
  papers, make available contents searchable, and search them alongside
  research notes. Explain the connection to Academic Hub in terms of reused
  search capabilities rather than embedding or federation terminology.
- Describe the current tools precisely. Avoid implying that a complete
  autonomous literature-review or analysis system has shipped, or that all
  selected papers can be obtained automatically. Keep this an orientation page.

### 28. Introducing Academic Hub

- [ ] [Introducing Academic Hub](https://aaronscherf.github.io/blog/academic_hub/)
- **Scope:** Targeted revision. **Original rank:** 28.
- Add a dated historical cue and a link to the current overview. Simplify
  the dense architecture paragraph around the original practical goal of
  connecting scattered coursework.
- Preserve what was true when the post was written, including design-stage
  descriptions. Do not silently convert the announcement into a present-day
  inventory. Detailed repository, container, sync, and credential mechanics
  can move behind a source link where they do not advance the story.

### 29. Concept Graph

- [ ] [Concept Graph](https://aaronscherf.github.io/projects/academic-hub/concept_graph/)
- **Scope:** Targeted revision. **Original rank:** 25.
- Preserve the improved current structure and live-graph link. Add one
  concept connection, its condition, and what following it helps a student
  understand. A focused screenshot could explain more than the feature list.
- Shorten the interface inventory and drafting mechanics. Keep proposed versus
  reviewed content visible, including unreviewed section summaries and the
  submission path's validation status. Concept and connection counts describe
  scale, not evidence of learning benefit. Do not undo the newer page's useful
  distinction between tests, an actual graph, and unverified workflows.

### 30. Guided Solutions

- [ ] [Guided Solutions](https://aaronscherf.github.io/projects/academic-hub/guided_solutions/)
- **Scope:** Targeted revision. **Original rank:** 30.
- Show a compact excerpt distinguishing a student's reasoning, an agent's
  derivation, and later tutor feedback. Explain why keeping these contributions
  separate helps comparison and review without presenting agent work as the
  student's own reasoning.
- Retain its status as a documented workflow and its evidence from a particular
  run. Do not recast it as an automated product or expand into a schema
  explanation. Keep private source documents private.

### 31. Managing this site with HugoBlox and Claude

- [ ] [Managing this site with HugoBlox and Claude](https://aaronscherf.github.io/blog/site_management/)
- **Scope:** Light edit. **Original rank:** 31.
- Describe editing text, reviewing changes, and publishing automatically.
  Introduce Hugo, GitHub, and Markdown only as needed; YAML, CMS, CI, and branch
  names need not all appear. Preserve the specific first-person examples and
  historical context rather than adding a web-development tutorial.

### 32. Converting Academic Resources to Markdown

- [ ] [Converting Academic Resources to Markdown](https://aaronscherf.github.io/blog/academic_resource_progress/)
- **Scope:** Light edit. **Original rank:** 32.
- Explain what page references and figure descriptions let the author find
  or revisit. One concrete benefit is enough. Reconcile the square-root error
  described as open with later repair records through a dated update or clear
  historical framing. Keep conversion counts scoped and retain the concise post.

### 33. Making Textbook Conversion Easier to Run in Batches

- [ ] [Making Textbook Conversion Easier to Run in Batches](https://aaronscherf.github.io/blog/textbook_conversion_automation/)
- **Scope:** Light edit. **Original rank:** 33.
- Add either a duplicate-book example or an interrupted conversion; both are
  unnecessary unless they improve the story. Clarify review of uncertain
  matches and preserve the distinction between implemented recovery and
  observed reliability. Do not expand into the complete recovery algorithm.

### 34. Indexing and Querying Academic Hub

- [ ] [Indexing and Querying Academic Hub](https://aaronscherf.github.io/blog/indexer_and_rag_progress/)
- **Scope:** Light edit. **Original rank:** 34.
- Add a short source-reference example and explain what the reader can check
  through it. Retain the accessible structure and early-milestone framing.
  This needs a small illustration of the benefit, not a fresh technical account.

### 35. An AI Tutor That Gives Hints and Checks Your Reasoning

- [ ] [An AI Tutor That Gives Hints and Checks Your Reasoning](https://aaronscherf.github.io/blog/pedagogical_rag_hints/)
- **Scope:** Light edit. **Original rank:** 36.
- Consider replacing the abstract preferences example with a more accessible
  one rather than adding another. Show what the learner can do next. Preserve
  the personal motivation and the specific checking limits; remove repeated
  qualifications if they make the same point without adding information.

### 36. Why I Use Obsidian and Excalidraw for Academic Notes

- [ ] [Why I Use Obsidian and Excalidraw for Academic Notes](https://aaronscherf.github.io/blog/obsidian_excalidraw_notes/)
- **Scope:** Light edit. **Original rank:** 37.
- Add one linked-note example or focused screenshot showing handwriting
  beside related material. Briefly explain the two apps. Preserve the candid
  export and maintenance tradeoffs and personal preferences, without expanding
  the product comparison or promising automatic organization.

### 37. Finding Academic Papers for a Research Library

- [ ] [Finding Academic Papers for a Research Library](https://aaronscherf.github.io/blog/academic_journal_discovery/)
- **Scope:** Light edit. **Original rank:** 35.
- OpenAlex is already explained as an academic works catalog, so the original
  suggestion is largely satisfied. An actual research-topic example could add
  value if available. Otherwise preserve this concise account, the distinction
  between discovery and access, and the scope of the early trial.

### 38. Tidying Up Academic Hub's Plumbing

- [ ] [Tidying Up Academic Hub's Plumbing](https://aaronscherf.github.io/blog/academic_hub_infrastructure_cleanup/)
- **Scope:** Light edit. **Original rank:** 38.
- Little rewriting is necessary. Add a brief observable before-and-after sync
  detail only if documented. Keep the short explanation of maintenance value
  and the stated scope of the reorganization. Do not lengthen the post simply
  to satisfy a project-page template.
