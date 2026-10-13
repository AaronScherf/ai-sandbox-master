# Website page readability revisions

Ranked on 2026-10-13 from **most** to **least** in need of a rewrite for a
nontechnical reader. This is an editorial priority list, not a finding that a
page or its underlying project is technically incorrect. It covers the 28
substantive project pages and 10 blog posts reviewed at website commit
`88124e4`; nine unpublished HugoBlox template examples are excluded.

Check an item off after revising the linked page for clarity and reviewing its
claims against current source material. Each note identifies the main editing
opportunity; it is not a required wording change.

- [ ] **01. [Notes Transcription Pipeline](https://aaronscherf.github.io/projects/academic-hub/notes_transcription/)** — Lead with what a student receives, then break up the long OCR-routing and bug-history paragraphs into a short process and evidence summary.
- [ ] **02. [Marker PDF Conversion](https://aaronscherf.github.io/projects/academic-hub/marker_conversion/)** — Put the textbook-conversion outcome and cost tradeoff ahead of the dense GPU setup, deduplication, and failure-recovery chronology.
- [ ] **03. [Resume Manager](https://aaronscherf.github.io/projects/resume_manager/)** — Show a simple master-to-tailored-resume example before the lengthy YAML extraction and parser bug narrative.
- [ ] **04. [Visualization Sub-Agent](https://aaronscherf.github.io/projects/academic-hub/visualization/)** — Explain when a student gets a useful plot and how it is checked before detailing templates, local code generation, and subprocess safeguards.
- [ ] **05. [Source Indexer](https://aaronscherf.github.io/projects/academic-hub/source_indexer/)** — Use one concrete search example to explain document cards and passage retrieval before the tag-mining and indexing internals.
- [ ] **06. [Video Lecture Notes](https://aaronscherf.github.io/projects/academic-hub/video_notes/)** — Start with the finished lecture notes and their citation limits; compress the long context-window debugging account.
- [ ] **07. [Journal Discovery Pipeline](https://aaronscherf.github.io/projects/ai-research-assistant/journal_discovery/)** — Present the researcher’s path from topic to candidate paper to accessible full text before API scoring and metadata-reconciliation details.
- [ ] **08. [Tutor Diagnosis & Hint Generator](https://aaronscherf.github.io/projects/academic-hub/tutor_diagnosis/)** — Replace the command-by-command feel with a short student question, hint, draft check, and limitation example.
- [ ] **09. [Problem Generation Sub-Agent](https://aaronscherf.github.io/projects/academic-hub/problem_generation/)** — Illustrate one generated practice question and explain what the second check can and cannot establish before describing the verification loop.
- [ ] **10. [RAG Analysis](https://aaronscherf.github.io/projects/academic-hub/rag_analysis/)** — Show a cited answer first, then shorten the explanation of stateless calls, query reformulation, and retrieval mechanics.
- [ ] **11. [Obsidian Git Sync](https://aaronscherf.github.io/projects/academic-hub/obsidian_git_sync/)** — Make the tablet-to-laptop workflow and the files excluded from sync immediately clear before the implementation history.
- [ ] **12. [Research Notes Conversion](https://aaronscherf.github.io/projects/ai-research-assistant/research_notes_conversion/)** — Add a before-and-after document example and condense the parser, frontmatter, and classification fixes.
- [ ] **13. [Multi-Agent Development Workflow](https://aaronscherf.github.io/projects/multi_agent_project/)** — Explain the coordination problem through one task handoff before introducing agent roles, worktrees, and merge rules.
- [ ] **14. [Notes Post-Processing](https://aaronscherf.github.io/projects/academic-hub/postprocess_notes/)** — Use an example of a plausible but corrupted line of text to explain why the anomaly checks and source-image review matter.
- [ ] **15. [Problem Corpus Extraction](https://aaronscherf.github.io/projects/academic-hub/problem_corpus/)** — Show one extracted question record so provenance and unverified student attempts are understandable without schema terminology.
- [ ] **16. [Audio Generator](https://aaronscherf.github.io/projects/academic-hub/audio_generator/)** — Describe the listening experience and one course-note conversion before model-routing and timing details.
- [ ] **17. [Journal Article Transcription](https://aaronscherf.github.io/projects/ai-research-assistant/journal_article_transcription/)** — Explain the searchable article output and where human checking is needed before renderer and page-count routing details.
- [ ] **18. [Turning Dense Math Notes into Commute Podcasts](https://aaronscherf.github.io/blog/audio_generator_podcasts/)** — Keep the useful first-person story but trim the technical stage-by-stage account and foreground what the audio sounds like in practice.
- [ ] **19. [Corpus Health](https://aaronscherf.github.io/projects/academic-hub/corpus_health/)** — Walk through one finding, owner decision, and permitted repair before describing ledgers, locks, and adapters.
- [ ] **20. [Project Steering](https://aaronscherf.github.io/projects/academic-hub/project_steering/)** — Follow one to-do item from scan to owner review so task IDs, scoring proposals, and route approval feel concrete.
- [ ] **21. [Novel Omnibus Normality Test](https://aaronscherf.github.io/projects/math_thesis/)** — Explain the practical question and comparison result before the statistical construction and specialized terms.
- [ ] **22. [Summary Enhancement](https://aaronscherf.github.io/projects/academic-hub/summary_enhancement/)** — Contrast a short source-grounded summary with an expanded study guide before describing source maps and formatting passes.
- [ ] **23. [Study Guide Pipeline](https://aaronscherf.github.io/projects/academic-hub/study_guide_pipeline/)** — Show what a draft guide and reviewed revision look like before the source-plan and command sequence.
- [ ] **24. [Socratic Tutor](https://aaronscherf.github.io/projects/academic-hub/socratic_tutor/)** — Use a brief learner–tutor exchange to explain the teaching goal before CLI state and event-log terminology.
- [ ] **25. [Concept Graph](https://aaronscherf.github.io/projects/academic-hub/concept_graph/)** — Give an example of two linked course concepts and the human review step before discussing typed relationships and drafting stages.
- [ ] **26. [Wheat Yield Prediction](https://aaronscherf.github.io/projects/wheat_yield_prediction/)** — Explain the model comparison and what its accuracy numbers mean for a reader unfamiliar with breeding research.
- [ ] **27. [Academic Hub overview](https://aaronscherf.github.io/projects/academic-hub-overview/)** — Group the many subproject links by the reader’s task—prepare sources, search, study, or maintain—so the list is easier to navigate.
- [ ] **28. [Introducing Academic Hub](https://aaronscherf.github.io/blog/academic_hub/)** — Add a brief historical cue so its original design-stage description is not mistaken for the project’s current state.
- [ ] **29. [AI Research Assistant overview](https://aaronscherf.github.io/projects/ai-research-assistant-overview/)** — Give a concrete research question or paper-search scenario before terms such as embedding and federated retrieval.
- [ ] **30. [Guided Solutions](https://aaronscherf.github.io/projects/academic-hub/guided_solutions/)** — Add a small example showing how agent work, the student’s reasoning, and later tutor feedback stay distinct.
- [ ] **31. [Managing this site with HugoBlox and Claude](https://aaronscherf.github.io/blog/site_management/)** — Clarify the few Hugo and GitHub terms for readers who have never edited a website repository.
- [ ] **32. [Converting Academic Resources to Markdown](https://aaronscherf.github.io/blog/academic_resource_progress/)** — Connect the conversion metrics to a concrete improvement in searching or studying course material.
- [ ] **33. [Making Textbook Conversion Easier to Run in Batches](https://aaronscherf.github.io/blog/textbook_conversion_automation/)** — Add one concrete duplicate-book or interrupted-run example to make the operational improvement easier to picture.
- [ ] **34. [Indexing and Querying Academic Hub](https://aaronscherf.github.io/blog/indexer_and_rag_progress/)** — Briefly show what a source reference looks like in an answer; the rest is already fairly approachable.
- [ ] **35. [Finding Academic Papers for a Research Library](https://aaronscherf.github.io/blog/academic_journal_discovery/)** — Explain OpenAlex in one plain phrase or example; the search and access story is otherwise clear.
- [ ] **36. [An AI Tutor That Gives Hints and Checks Your Reasoning](https://aaronscherf.github.io/blog/pedagogical_rag_hints/)** — A second short example of a useful hint could make an already clear explanation more tangible.
- [ ] **37. [Why I Use Obsidian and Excalidraw for Academic Notes](https://aaronscherf.github.io/blog/obsidian_excalidraw_notes/)** — A specific linked-note example would help readers visualize the workflow, though the prose is already accessible.
- [ ] **38. [Tidying Up Academic Hub’s Plumbing](https://aaronscherf.github.io/blog/academic_hub_infrastructure_cleanup/)** — The concise post needs little rewriting; a concrete before-and-after sync example would be the main optional improvement.
