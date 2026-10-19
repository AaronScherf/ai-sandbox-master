# Course-agnostic concept graph: design

Date: 2026-10-19. Branch: `claude/concept-graph-generalize`. Builds on
[the concept graph design](2026-10-09-concept-graph-design.md) and its
[current status](../../../status/agent/concept_graph/2026-10-15-concept-graph-status.md).

## Goal

Run the concept-graph pipeline on econometrics, and on any later course, without code changes, whatever the
course's folder names and note structure. Microeconomics must keep working with equivalent output.

Success means:

- `collect seed` for econometrics produces a card with evidence as rich as microecon's: the instructor's dated notes
  in the lecture timeline, slide headings, textbook contents under each book's own key, the 2024 offering's slides,
  and capped TA notes.
- A new course needs only per-course configuration (seed scope, vocabulary, subject) and a review of the files the
  classifier is unsure of.

## Why the current pipeline does not generalize

The pipeline decides what a file is from its path:

- `agent/concept_graph/sources.py` hard-codes three microecon textbooks (`rubinstein`, `mwg`, `ok`); every other book
  becomes `other`, so citations cannot tell Hansen from Cameron.
- Prior years are found by the folder spelling `20??_class` and classified by microecon folder words ("post",
  "pre lecture"). Econometrics spells it `class_2024/Class Notes/Slides/`, so none of it is offered. `ta_notes/` is
  not recognised.
- `seed.outline_context` reads fixed folders (`syllabus/`, `professor_notes/`, `lecture_notes/`, `textbooks/`) and
  offers only labelled statements (`Definition`, `Theorem`, ...). Microecon decks carry 11-24 of these each;
  econometrics notes carry 0-4, and structure their content with headings instead.
- Microecon wording is in code: the fill prompt ("microeconomic theory"), the seed prompt's background-mathematics
  hint, `KIND_HELP` examples, and the `scaffold` README and site title.

The hub has no reliable record of what each file is either. Frontmatter `folder_category` is just the folder name
("Post lecture notes", "Post-Lecture Notes", "Slides", "class_2024"), and index cards (with an LLM-assigned
`doc_type`) cover only part of a course (80 of about 150 econometrics files, and none of the professor's slides).

## Approach

Courses share a finite set of material categories whose names and layouts differ. A shared classifier in
`core/course_materials/` decides each file's category from several independent signals, none of which is decisive on
its own except where the evidence is unambiguous (an Excalidraw source). Files it is unsure of go to the owner on an
interactive review page; decisions are stored and win over the rules. The concept graph reads the resulting catalog
instead of paths.

Rejected alternatives: a model-drafted mapping per course (a model round trip for what a glance at the folder tree
usually settles; can be added later behind the same "flagged" interface), and a hand-written mapping only (no
detection, more setup per course). For the classifier itself, weighted rules beat a model tiebreak (cost,
nondeterminism) and embedding prototypes (needs labelled examples, and only covers indexed files).

## 1. Shared classifier: `core/course_materials/`

### Data model

`classify_course(hub_root, course) -> Catalog`; a `Catalog` holds one `Material` per converted file:

| field | values |
|---|---|
| `path` | hub-relative path of the converted file read for content. Where `X.md` and `X.rag.md` both exist, one record with the `.rag.md`. |
| `format` | `slides`, `handwritten`, `typeset`, `excalidraw`, `chapter` |
| `role` | `syllabus`, `instructor`, `student_notes`, `recitation`, `problem_set`, `exam`, `textbook`, `other` |
| `offering` | `None` for the current offering, else the label from `find_containing_offering_label` (e.g. `2024`) |
| `date` | ISO date from the file name or frontmatter, if any |
| `book` | textbooks only: a short key, by default the first word of the book folder lowercased (`hansen`, `cameron`) |
| `order` | sort key within a role: a leading number in the file name, else the date, else the name |
| `confidence` | margin between the winning and runner-up *authority* scores (below) |
| `evidence` | list of `(signal, vote, weight)` behind the decision |
| `decided_by` | `rules` or `review` |

The professor's handwritten notes and their slide decks share `role: instructor` and differ by `format`.

Each role belongs to one **authority** group, a derived property, not stored:

| authority | roles | meaning |
|---|---|---|
| `class` | `syllabus`, `instructor`, `recitation`, `problem_set`, `exam` | material handed out by the class: ground truth |
| `reference` | `textbook` | published reference |
| `student` | `student_notes` | the student's own notes or their LLM expansions: may contain mistakes |
| `unknown` | `other` | |

Telling the groups apart matters; telling roles apart within `class` matters much less (an instructor deck read as a
recitation deck, or the reverse, is still ground truth). Flagging and confidence therefore work on authority.

### Signals

Each signal votes for a `format`, a `role`, or both, with a weight. All are local and free; none calls a model.

| signal | votes | weight |
|---|---|---|
| frontmatter `source_excalidraw` | `excalidraw` + `student_notes` | decisive |
| `chapters/NN_*.rag.md` layout, or index card `doc_type: textbook` | `chapter` + `textbook` | decisive |
| source PDF page shape (pypdf, first pages, rotation applied) | landscape: format `slides`; portrait: evidence only. Never a role vote. | medium (format only) |
| index card `doc_type` where a card exists | `problem_set`, `ta_notes` (`recitation`), `syllabus`, `handwritten_notes` (`handwritten`) | strong |
| content patterns | syllabus wording (grading, office hours, schedule); numbered problems with lettered parts (`problem_set`); "solution", "midterm", "final exam" (`exam`/`problem_set`); "recitation", "section", "TA" (`recitation`) | medium |
| path words | `professor`, `slides`, `lecture`, `ta`, `recitation`, `hw`, `homework`, `problem`, `exam`, `syllabus`, `proof` | weak, one vote per word |
| fallthrough for format | portrait PDF with few headings and short lines: `handwritten`, else `typeset` | weak |

Starting weights: decisive 10, strong 3, medium 2, weak 1.

Page orientation is a convention of these two courses, not a rule: it is a medium vote for the slide *format* and
says nothing about who made the file. A file whose format is `slides` (from any signal) adds its slides score to the
`class` authority, since a slide deck is class material rather than a student's notes or a book, but it does not
pick a role within `class`.

The decision then runs in two steps:

1. **Authority.** Each group's score is the sum of its roles' votes, plus the slides contribution to `class`. A file is
   **flagged** when the top group scores below 3 or leads the runner-up group by less than 2.
2. **Role within the group.** The group's highest-scoring role; for `class` with no role votes (a deck known only to
   be slides) the role is `instructor`. A tie between two `class` roles is resolved this way and never flagged.

So a landscape deck with no other signal scores `class` 2 and is flagged for review; with a `professor` path word, a
recitation wording match or an index card it clears the threshold. Weights are tuned against the microecon and
econometrics trees during implementation and recorded in the module.

Offerings come from the existing subset markers (`.notes_subset.json`, read by
`core/env/academic_hub_paths.find_containing_offering_label`), not from folder names.

### Storage and overrides

- `academic-hub/.index/materials/<course>.json`: the catalog, regenerated by every `classify`.
- `academic-hub/.index/materials/<course>.decisions.json`: owner decisions keyed by path. A decision can set any of
  `role`, `format`, `offering`, `book`, `order`, or `exclude: true`. Decisions win over rules and survive re-runs;
  records they set carry `decided_by: review`.

Both live in the shared hub, so `classify` and `resolve` are writes to a shared index: tests use fixture trees, and
real runs happen from one session at a time. This is the same split as `core/indexer/offering_links.py` (a generated ledger plus a decisions file). Microecon's
first decisions set `book` for its three textbooks (`rubinstein`, `mwg`, `ok`) so existing citation keys keep
meaning the same books.

### Review

Flagged files go onto an interactive Artifact (per the subproject rule that human decisions are made on an Artifact,
not by hand-editing a file), modelled on the offering-links review page: one row per flagged file with its evidence,
a role and format select, and Confirm / Exclude. Decisions live in the page's `db` collection; `resolve` applies them
to `decisions.json` through the module's own function and re-classifies.

### Commands

`python -m core.course_materials.cli --hub-root <hub> --course <course> <command>`:

- `classify`: build or refresh the catalog; print counts per role and format, then each flagged file with its
  evidence, and any decision whose path no longer exists.
- `review`: write the flagged files into the review Artifact's `db` and print its link.
- `resolve`: read decisions back from the Artifact into `decisions.json`, then `classify`.

### API

- `classify_course(hub_root, course) -> Catalog` (writes the catalog file).
- `load_catalog(hub_root, course, *, refresh="if_stale") -> Catalog`: re-classifies when the catalog is missing or
  older than any converted file in the course or the decisions file.
- `Catalog.lookup(path) -> Material | None`: accepts paths under `academic_notes/` or `academic_resources/` (the
  index cards use both), normalised with the existing `academic_hub_paths` helpers; exact match first, then the
  nearest catalogued ancestor directory (so a book's front-matter file maps to that book).
- `Catalog.flagged()`, `Catalog.by_role(role, offering=None)` (sorted by `order`).

## 2. Concept graph on the catalog

### Citation keys

`classify_passage(path, citation)` keeps its signature and becomes a lookup plus this mapping:

| material | source key | ref |
|---|---|---|
| textbook | its `book` | `ch. N, <citation>` (as today) |
| instructor, format `slides` | `slides` | deck title |
| instructor, other formats | `notes` | date, else title |
| student_notes | `lecture` | date |
| recitation | `recitation` | title or date |
| problem_set | `hw` | stem |
| exam | `exam` | stem |
| syllabus | `syllabus` | stem |
| other, or no catalog match | `other` | stem |

A prior offering appends its label: `slides-2024`. For microecon, textbook keys, `lecture`, `slides` and `hw` are
unchanged; the prior-year keys `slides-pre-2024` and `proofs-2024` become `slides-2024` (decided: no
`key_overrides` map for this cosmetic difference). Stored citations are not rewritten; nothing re-validates their
keys, so only new cards use the new keys. Unmatched paths are reported once per run.

### Seed evidence

`outline_context` builds the card from the catalog by role, authoritative material first:

1. **syllabus** (current offering): cleaned excerpt, as today.
2. **instructor** (current offering, by `order`): labelled statements and, new, section headings of every deck and
   note. Dated instructor notes join the lecture timeline.
3. **recitation**: headings only.
4. **prior offerings**: instructor slides by offering label, as the microecon 2024 and 2025 decks are offered today.
5. **textbook**: each book's contents, and the section headings of the chapters `seed.yaml` puts in scope.
   `textbook_chapters` is keyed by `book` (folder names still accepted).
6. **student_notes**: statements and headings by date; their dates still form the lecture timeline.

The seed instructions say how to weigh them: the syllabus, the instructor's and recitation material and the textbooks
are authoritative; the student's lecture notes (source key `lecture`) are transcriptions and may contain mistakes, so
they show teaching order, dates and coverage, and where they disagree with class material the class material wins.
The fill instructions carry the same rule for the passages a fill card offers.

`problem_set` and `exam` material is not offered to seed (as today); retrieval still finds it for later stages.

The statement pattern also accepts plurals and numbering (`Assumptions 7.1`, `Theorem 3.2`). The context keeps its
12,000-character cap; offered passages are capped per role (starting values: instructor 30, student notes 20,
recitation 8, prior offerings 15 per offering, textbook contents 1 per book plus in-scope chapters) so a large
role cannot crowd out the slides.

## 3. Course wording and per-course setup

- **Subject.** `config/site.yaml` gains `subject` (validated by `Site`; default `the course`). The fill prompt says
  "studying {subject}", plus the authority rule above. The seed prompt's hint becomes "If the course relies on background mathematics or other
  prerequisites, give it a first section, however brief." Microecon's `site.yaml` gets
  `subject: graduate microeconomic theory`, so its cards read as before.
- **Kinds.** `vocab.yaml` `kinds` entries may be plain names (as today) or `{name, help}` mappings. File help wins;
  `KIND_HELP` is the fallback and gains generic entries: `estimator`, `assumption`, `test`, `statistic`,
  `distribution`, `result` (an asymptotic or finite-sample property of an estimator or statistic). `Vocab` normalises
  both forms so `graph.vocab.kinds` stays a list of names for every caller.
- **Scaffold.** `scaffold` takes `--title` and `--subject`; the README, `site.yaml` and the `seed.yaml` comment use
  them. The comment lists the course's `book` keys from the catalog when one exists, instead of the hard-coded
  microecon keys.
- **Gate.** `collect seed` calls `load_catalog(refresh="if_stale")`. If any material is still flagged it stops and
  names the files (`--allow-unreviewed` overrides). Other stages only use the catalog through `classify_passage`.

Per-course setup for econometrics: `classify`, review flagged files; `scaffold` an `econometrics-concept-graph`
repo with title and subject; write `seed.yaml` (scope, `must_include`, Hansen chapters) and the `vocab.yaml` kinds;
`collect seed`. Writing `seed.yaml` stays a human step: it is what the files cannot say, as for microecon.

## 4. Errors, testing, verification

### Error handling

- Unreadable PDF or missing source file: the page-shape signal abstains; evidence records `pdf: unavailable`.
- No signal reaches the threshold: `role: other`, flagged.
- A decision whose path no longer exists: reported by `classify`, kept.
- Corrupt catalog or decisions JSON: raise naming the file; no silent fallback to path rules.

### Tests

- `tests/core/course_materials/`: each signal; the vote combiner and flagging thresholds; a fixture course with
  deliberately non-standard names (slides under `misc/`, a problem set named `week3.pdf`, a `class_2023` offering
  with a subset marker, a textbook with `chapters/`); decisions win and survive re-classification; `lookup` across
  both roots and the ancestor fallback; staleness.
- `tests/agent/concept_graph/`: `classify_passage` on a catalog (each mapping row, prior-offering suffix, no match);
  seed offers slide headings and dated instructor notes and respects role caps; the fill prompt carries `subject`;
  `Vocab` accepts both kind forms; the seed gate stops on flagged material; scaffold uses title and subject.

### Real-data verification (no model calls)

1. **Microecon regression.** `classify microecon` flags few files; record the three `book` decisions. Compare the
   seed card from this branch with the one from `main`: expected differences are prior-year key renames and the
   added slide headings only.
2. **Econometrics dry run.** `classify econometrics` and review flagged files; `collect seed` and check the card has
   dated instructor notes in the timeline, slide headings, `hansen`/`cameron`/`hayashi`/`stock` keys, the 2024
   offering's slides, and capped TA notes. Then the normal Antigravity relay (subscription, no API cost).

## Deferred: does the edge vocabulary fit econometrics?

Microecon builds topics by logical dependency, which the edge types express (`implies`, `iff`, `hypothesis_of`,
`yields`). Econometrics introduces one set of mathematical tools early (LLN, CLT, continuous mapping, Slutsky, delta
method, projection) and applies it to many settings, so its graph should be flatter and tool-centred, and may need
types such as `applies`/`uses` and `special_case_of`. Decision: run the existing types first. After the first `fill`
and `link` runs on econometrics, check:

- how many link-card edges are really "uses/applies" relations recorded as another type;
- the fan-out of tool concepts and which edge types carry it;
- the number of orphaned nodes.

If the fit is poor, new edge types (schema, validator, link prompt, viewer legend) get their own spec.

## Out of scope

New edge types (deferred above); viewer changes; moving other pipelines (study guides, tutor, problem generation)
onto the catalog; a model-drafted classification stage.
