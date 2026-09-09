
Goals:
- Synchronized academic and research hubs to support learning and connect with research ideas, leveraging common scripts to reproduce useful AI functions on a local corpus of mixed knowledge artifacts
- Learning Hub:
	- Convert textbooks, notes, lecture materials, problem sets, past exams, etc. into standardized markdown format to improve machine readability for derivative content
	- Develop index for all content (both uploaded and user generated) so a centralized tutor RAG agent can easily query relevant content, both for user generated queries and automated tasks like problem set generation
	- Use index to make notes, textbooks, and other resources quickly searchable by both user and RAG agent
	- Develop customized learning plans based on the syllabus and course content, drawing on resources from related courses to reinforce gaps (like math prerequisites)
		- Combine learning plans for multiple courses into overall semester schedule by identifying synergies in topics
		- Customize study plans to known milestones like exams, build in holidays and breaks
		- Recursively improve study plans by tracking progress throughout the semester, note specific strategies that are working or not working for student
	- Produce summaries / analyses of combined textbook chapters, notes, lecture slides, and other resources by topic, in response to a specific user input or a scheduled rubric of content generation following a syllabus
		- Include visualizations for concepts when possible, using interactive plots or figures
		- Make summaries responsive to learning plan, not just topic based; if the learning plan calls for the user to learn specific content in the coming week, schedule the creation of topic summaries to supplement lectures and notes, analyze notes and lecture slides once available, create a weekly "What did we learn?" summary to reflect on that week's topics, connect with problem sets and user-attempted solutions
			- Convert the reflective summaries to mp3 files so user can listen while on a jog
	- Produce accompanying practice problems based on content to help reinforce learning
		- Collect problems from instructor created problem sets, previous exams, textbook examples, online resources, as well as hub-generated problems into a large index of example problems
		- "Grade" and provide feedback on user submitted solutions to problem sets, incorporate feedback as artifacts in weekly learning summary
	- Encourage user to reflect on learning through weekly reflection journals, answering narrative questions about content, suggesting specific problems to focus on
	- Track learning progress through reflection journals (input from user), "grading" of problem sets (both internally generated and provided by instructors), and results of official exams
		- Specifically target gaps in knowledge and adjust learning plans to focus on content related to exams
	- Convert summaries / lessons / textbook chapters / notes into audio files so user can reinforce learning while on the go
	- Ensure all artifacts are accessible via obsidian with proper tags to support backlinks and mindmaps
- Teaching Hub:
	- Build on academic hub by suggesting improvements to the rubric, course schedule, lecture materials, problem sets, and exams
	- Generate authoritative problem sets to be used for future teaching
		- Collect and transcribe student submissions, evaluate aggregate performance
- Research Hub:
	- Convert academic journal articles from PDF to md format
	- Discover new journal articles by topic, author, and web of knowledge sampling
	- Index articles using OpenAlex and custom tags and yaml frontmatter
	- Literature reviews / gap analysis of existing research corpus to identify promising areas of research
	- Convert research notes from google docs to md files
	- Organize research ideas into tangible project proposals, brainstorm data sources and methods, develop timelines / research plans to fit major milestones
- Academic Website:
	- Manage personal academic website via HugoBlox and Github Pages
	- Connect to social media like Bluesky, Medium, Github
	- Host project descriptions for academic / teaching / research hubs as well as independent research projects
	- Host blog describing process of creating hubs, conducting research, reviewing books and articles, reflecting on pedagogy, etc.


## Progress So Far:

**Project-wide status/synthesis:** [[2026-08-30-academic-hub-status]] (cross-subproject map, pipeline diagram, real-corpus state, cross-cutting patterns, consolidated TODOs, and — folded in 2026-09-07 — the cross-cutting known-bugs tracker formerly its own doc)

* Learning Hub:
	* (DONE) Textbook transcription to md files
		* Spec: [[2026-08-19-textbook-chunking-and-page-tracking-design]]
		* Plan: [[2026-08-20-chapter-aware-chunking]], [[2026-08-20-vm-validation-checklist]]
		* Status: [[2026-08-22-chapter-aware-chunking-status]] — shipped, VM-validated across 3+ books. A handful of low-stakes deferred items (stale docstring, minor off-by-ones) remain, explicitly non-blocking.
		* (DONE) Convert figures to written descriptions
			* Status: [[2026-08-23-image-description-status]] — all 5 real textbooks processed (793 candidate figures, 764 described, 29 correctly skipped as decorative); no open blockers
	* (DONE) Handwritten notes conversion to md [[2026-08-24-notes-transcription-status]]
		* (Brainstormed, paused — no examples yet) Capture-pipeline redesign for handwritten_notes specifically: retire the OneNote screenshot→web-Gemini→paste round-trip (confirmed as the source of repeated colored-LaTeX blocks in the current output, not a transcription bug) in favor of Excalidraw notes in the Obsidian vault, transcribed then expanded to prose before hitting the corpus. See [[2026-08-24-notes-transcription-status]]'s "2026-09-07" section. Paused pending real Excalidraw examples (plugin not yet installed).
		* (Paused, in progress) Post processing to clean up notes, expand where necessary: 
			* Spec: [[2026-08-26-notes-postprocessing-design]]
			* Plan: [[2026-08-26-notes-postprocessing]]
			* Status: [[2026-08-27-notes-postprocessing-status]] — deliberately paused; open causal z-score precision problem on math-heavy prose (threshold raise cut noise ~62%, didn't eliminate it). Most promising unpursued fix (retrieval-conditioned scoring against passage embeddings) is now possible since the indexer below shipped, but not yet attempted.
	* (DONE) Indexer to categorize and quickly query across knowledge corpus 
		* Spec: [[2026-08-27-source-indexer-design]]
		* Plan: [[2026-08-28-source-indexer-core]], [[2026-08-28-source-indexer-retag]], [[2026-08-29-passage-embeddings]]
		* Status: [[2026-08-29-source-indexer-status]] — shipped, merged, real corpus healthy (30 cards, 0 orphaned/untagged, 14 tags). No open blockers.
	* (DONE) Problem Set Generator
		* Spec: [[2026-09-03-problem-generation-design]]
		* Plan: [[2026-09-03-problem-generation-plan]]
		* Status: [[2026-09-05-problem-generation-status]] — shipped, default Gemini (gemini-3.1-flash-lite) with local Ollama opt-in. Open: first-match parsing is vulnerable to a chatty model, no relevance threshold on style-pool retrieval.
	* (DONE) Problem Set Extractor / Corpus 
		* Spec: [[2026-09-06-problem-corpus-extraction-design]]
		* Plan: [[2026-09-06-problem-corpus-extraction]]
		* Status: [[2026-09-06-problem-corpus-extraction-status]] — shipped. Open: numbered-list boundary detector over/under-splits some problem-set prose.
		* (TBD) Future ideas depending on this (from Problem Set Generator's own status doc): few-shot examples from the corpus, direct-serve matching, solution backfilling, corpus growth, tiered local-corpus-then-Gemini pipeline
	* (DONE) Visualization generator 
		* Spec: [[2026-09-02-visualization-agent-design]]
		* Plan: [[2026-09-02-visualization-agent]]
		* Status: [[2026-09-02-visualization-agent-status]] — shipped (template tier + Ollama/Gemini fallback, wired into the RAG agent as an opt-in). Default fallback backend flipped to Gemini 2026-09-06 after Ollama reliability issues. Open: only 4 templates, no parameter extraction from retrieved content, no automatic visualize-or-not decision.
		* (DONE) Follow-on: Ollama retry hardening — Spec: [[2026-09-03-viz-ollama-retry-hardening-design]], Plan: [[2026-09-03-viz-ollama-retry-hardening]]
		* (DONE) Follow-on: local example store (feeds past successful generations back as few-shot examples) — Spec: [[2026-09-03-viz-example-store-design]], Plan: [[2026-09-03-viz-example-store]]
		* (DONE) Follow-on: combined answer+citations+viz report — Spec: [[2026-09-05-combined-report-design]], Plan: [[2026-09-05-combined-report]]
	* (DONE) YouTube Lecture downloader / converter to md
		* Spec: [[2026-09-06-video-lecture-notes-design]]
		* Plan: [[2026-09-06-video-lecture-notes]]
		* Status: [[2026-09-06-video-lecture-notes-status]] — shipped as `video_notes/`, validated across 2 real passes against the Math Camp playlist; found+fixed a shared Ollama context-truncation bug also affecting problem_gen/viz. Open: full 105-video playlist run still unvalidated, citation-gap in generated notes remains.
	* (DONE) RAG Tutoring Agent for user-facing queries
		* Spec: [[2026-08-30-rag-agent-design]]
		* Plan: [[2026-08-30-rag-agent]]
		* Status: [[2026-08-30-rag-agent-status]] — shipped on branch `rag-agent`, validated against real multi-turn queries. Deliberately private-only (real fair-use risk for a public tool serving copyrighted textbook content; a verbatim-passage incident this project already had made the risk concrete) — public deployment deferred pending real legal input, not an engineering choice.
	* (In Progress) md to mp3 converter to create audio files
		* Spec: [[2026-09-06-audio-generator-design]]
		* Plan: [[2026-09-06-audio-generator]]
		* Status: (no dedicated status doc yet) — `audio_generator/` shipped (discovery, idempotent state, Piper/Kokoro-ONNX synthesis, pipeline/CLI) plus an LLM-based LaTeX-to-narration revision wired in 2026-09-07. Blocked: the real CPU-timing validation (spec §9) was OOM-killed on the primary dev machine (qwen2-math:7b needs 4.4GB, <500MB was free with other apps open) — deferred to a machine with more free RAM, still unresolved.
	* (TBD) Persistent conversation/activity history for the RAG agent — named prerequisite for scheduled tasks, multi-day study continuity, and "summarize what I've covered this week"
	* (TBD) Extended/structured report generation (multi-section, multi-passage synthesis, distinct from single-question tutoring)
	* (TBD) Study-plan agent that calls the RAG agent as a building block — needs course-level structural awareness, sequencing/pacing logic, and a syllabus/timeline input
	* (TBD) Between-course retrieval validation, and corpus growth beyond math-camp — the course-filter/cross-course ranking and retag's tag vocabulary are both implemented but never exercised at more than one course's scale
* Research Hub:
	* (DONE) Journal article discovery from open source and paywall sites
		* Spec: [[2026-08-31-journal-discovery-design]]
		* Plan: [[2026-09-01-journal-discovery-plan]]
		* Status: [[2026-09-01-journal-discovery-status]] — shipped as `journal_discovery/`, merged to `main`. EZProxy validated live: Cloudflare bot-detection blocks scripted gated-paper fetches independent of credentials, not a cookie-freshness problem — expect a high needs_manual rate for major-publisher papers as the normal steady state. Four efficiency fixes shipped 2026-09-02 (dedup-before-scoring, EZProxy-only pacing, Semantic Scholar as a 2nd OA tier, exact-title dedup).
	* (DONE) Snowball sampling from works cited from existing corpus and forward citations
		* Spec: [[2026-09-02-journal-discovery-snowball-design]]
		* Plan: [[2026-09-02-journal-discovery-snowball-plan]]
		* Status: [[2026-09-01-journal-discovery-status]]
	* (DONE) Journal article conversion from PDF to md with tables preserved
		* Status: [[2026-09-01-journal-article-transcription-status]] — shipped as `journal_articles/convert_journal_articles.py`, reuses the notes pipeline's tiered routing wholesale. Real-corpus validated (3 papers converted, federated search across essays+journal corpora confirmed). Known gap: page_looks_defective() is tuned for LaTeX math notes, not paper prose — flags 32-43% of real paper pages, pushing them to the more expensive whole-document Gemini tier more often than necessary (still cheap in absolute terms, ~$0.02/paper).
		* (TBD) How to accurately preserve figures?
	* (Spec'd + planned, not built) Journal article metadata & folder audit
		* Spec: [[2026-09-02-metadata-folder-audit-design]]
		* Plan: [[2026-09-02-metadata-folder-audit-plan]]
		* Status: not implemented — `audit_metadata.py` was never written. Would auto-correct folder placement + tag-frontmatter sync (both mechanically well-defined) and flag title/author/DOI mismatches for human review, chained onto `reconcile_needs_manual.py`'s run. Motivated by a real gap noted in the journal-discovery status doc: mis-attributed OpenAlex concepts (e.g. a "Resilience (materials science)" homonym collision for a social-resilience paper).
	* (DONE, for local .docx — Google Drive pull still TBD) Research notes conversion from google docs to md files
		* Status: [[2026-09-01-research-notes-conversion-status]] — shipped as `essays/convert_essays.py` (mammoth-based .docx-to-md, no OCR/GPU needed), reconciled into the same source indexer as academic-hub. Real 19-file corpus validated, federated cross-corpus search confirmed. Today it's still a hand-populated local folder, not pulled from Google Drive directly — that's the actual open gap behind the original goal's "from google docs" framing.
	* (In Progress — brainstormed, not yet spec'd/planned) Literature review / gap analysis based on research corpus
		* Spec: (brainstorm only) [[2026-09-06-research-rag-design]] — a dedicated Research RAG agent (`research_rag/research_agent.py`) distinct from the tutoring agent: high-recall retrieval (top 20+, diversified by year/theme/method) feeding "summary"/"lit_review"/"gap_analysis" task types, output as structured technical markdown rather than conversational Q&A
		* Plan:
		* Status: not started — next steps per the brainstorm are a skeleton implementation, prompt templates per task type, then validation against the existing indexed journal-article corpus
	* (TBD) Data sources manager / discovery
		* Spec:
		* Plan:
		* Status:
	* (TBD) Methodology examples script library (Share common utilities across research projects for data extraction, processing, analysis, etc.)
		* Spec:
		* Plan:
		* Status:
	* (TBD) Research project critique engine
	* (TBD) Research project brainstorming engine
	* (TBD)
* Teaching Hub:
	* (TBD)
* Academic Website:
	* (DONE) Create website based on HugoBlox template
	* (DONE) Customize website to personal bio, upload CV, thesis projects, etc.
	* (DONE) Link personal social media sites, Google Scholar, etc.
	* (DONE) Start project descriptions for academic hub, thesis projects, etc.
	* (DONE) Start blog posts describing process
	* (In Progress) Create and maintain project plan and blogging schedule to ensure consistent promotion on project progress
		* [[website_blog_plan]]
	* (TBD) Post about website on LinkedIn
	* (TBD) Document progress to date in further blog series
* Independent Research:
	* (In Progress): Revise and improve on math thesis
		* [[MATH_Final_Thesis.pdf]]
		* [[Gemini Plan for Thesis Revision]]
	* (In Progress): Develop research plan for PhD based on career goals and complementary consulting work
		* 
	* (TBD): Revise and improve on Berkeley thesis [link]