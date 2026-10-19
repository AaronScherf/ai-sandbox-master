# Concept graph: course-agnostic pipeline, status 2026-10-19

Branch `claude/concept-graph-generalize`. Spec `docs/superpowers/specs/agent/2026-10-19-course-agnostic-concept-graph-design.md`,
plan `docs/superpowers/plans/2026-10-19-course-agnostic-concept-graph.md` (Tasks 1-10 done; Task 10 Step 5 stops at the
Gemini relay, which is the owner's step).

## What shipped

- **`core/course_materials/`**: classifies every converted file of a course by role (instructor, recitation, student
  notes, problem set, exam, syllabus, textbook) and format from weighted signals, flags the uncertain ones on
  authority (class material vs. student notes vs. reference), stores the catalog and the owner's decisions in
  `academic-hub/.index/materials/<course>{,.decisions}.json`. CLI: `classify`, `flagged`, `decide` (`--exclude` too).
  Review of flagged files is an interactive Artifact (one was used for econometrics).
- **Concept graph on the catalog**: citation keys come from the catalog (book keys such as `hansen`, `mwg`); the seed
  card offers material by role, class material first; `collect seed` stops while anything is flagged
  (`--allow-unreviewed` overrides); `site.yaml` `subject`; `vocab.yaml` kinds may carry `{name, help}`; `scaffold`
  takes `--title`/`--subject` and lists the course's book keys.
- **`tools/seed_card_coverage.py`**: counts, per kind of material and file, what reaches the seed card against what
  exists, and which graph concepts appear only in left-out material. No model calls. Closed TODO-0074 with it.

### Changes made from the real data (each with a test that failed first)

| Change | Why |
|---|---|
| Index card `ta_notes` vouches for class material, not for a TA | the indexer files microecon's professor decks under it |
| Earlier-offering cap 15 -> 30, any format | 2024 pre/post decks cut off risk and uncertainty; orientation must not decide |
| An untranscribed Excalidraw drawing is a dated student note | 7 econometrics lecture dates were dropped |
| Scaffold writes no topics | microecon's topics leaked into a new course |
| Seed relay steps hold for a first seed | they called every seed "additive" and asked for axioms |
| **Weights:** category folder (`ta_notes`, `professor_notes`, `problem_sets`, `syllabus` directly under the course) is a MEDIUM role vote; index card `textbook` is decisive only with a `chapters/` layout, else WEAK and role only | econometrics `ta_notes/A3` was a textbook on the label alone; `00-review-questions` and `A0-little-o-big-o` were problem sets |
| Recitation offers statements (25) and headings (15) per file; cap 8 -> 25 | econometrics TA notes hold 135 labelled statements, the instructor's handwritten notes 15; at cap 15 the appendices A1-A4 were cut |
| A passage 90% contained in one already offered (10-gram floor) is dropped, on the seed card and in retrieval | the syllabus twice in both courses; microecon's 2024/2025 decks repeat this year's |
| Excluded files are kept in the catalog (`excluded`) and dropped from retrieval | an excluded duplicate still reached fill cards through the index |

## Microecon regression

- Classify: 2 flagged at first, decided (plus the three book keys `rubinstein`/`mwg`/`ok`); 199 materials now, 0
  flagged. The category-folder and textbook-label changes moved none of the 199 decisions.
- Seed card against `main`: no slide deck, lecture date or textbook passage lost; syllabus key `other` -> `syllabus`;
  48 -> 71 passages (slide headings, 2024/2025 decks). The duplicate guard then removed 24 true copies (second
  syllabus, repeated decks): 49 passages, 44K characters. Concept names found in offered material: 43 before and after.
- Coverage (TODO-0074): the 12000-character cut only touches the header (1,599 characters); class material nearly all
  reaches the card; what is left out is textbook material by design. Limits unchanged.

## Econometrics

- Classify: 23 flagged before review (2024 handwritten notes, dated professor notes, loose problem-set files), 0 after;
  all 23 owner answers matched the proposed role. `syllabus/processed_outputs/ec6411A.md` excluded (duplicate of
  `ECON6411_syllabus.md`). 182 materials after the 2026-10-19 transcription batch, 0 flagged.
- Graph repo: `C:\Users\theaa\econometrics-concept-graph`, private on GitHub
  (`AaronScherf/econometrics-concept-graph`); `config/seed.yaml` (scope in syllabus order, 55 required concepts,
  `min_nodes_per_section: 10`) and `config/vocab.yaml` (14 described kinds) drafted with the owner.
- Seed card (dry run, no model): instructor notes in the timeline, slide headings (Gauss Markov Theorem, Omitted
  variables bias), `cameron`/`hansen`/`hayashi`/`stock` keys, 2024 offering slide sets, all 19 TA notes (135/135
  statements); 68 passages, 50K characters.
- **Quirk:** the Stock-Watson conversion lacks chapter 5, so SW chapters 15-17 are files 14-16; `textbook_chapters`
  uses file numbers, and the scope says so. Hayashi's files are numbered from its front matter (`03_1_...` is ch. 1);
  it is not in scope.
- Still untranscribed: `Econometrics Recitation 2026-09-15 08.06.01.excalidraw` (counts as a dated student note).

## Open

- **Next:** the owner hands the seed run to Gemini (classify, collect, coverage, fill the card), then `submit`,
  `validate`, review the skeleton, and continue with `fill`/`link` as for microecon.
- **Deferred edge-vocabulary check** (spec, "Deferred"): after the first econometrics `fill` and `link` runs, count
  link-card edges that are really "uses/applies" relations recorded as another type, the fan-out of tool concepts
  (LLN, CLT, Slutsky, delta method, projection) and which types carry it, and orphaned nodes. A poor fit gets its own
  spec for new edge types.
- Microecon graph repo `site.yaml` has no `subject:` (its cards say "this course"); owner's call, separate repo.
- Make the econometrics repo public (and enable Pages) when the graph is ready to publish, as for microecon.
- `academic-hub/.index/materials/` is committed on this branch; a later `classify` rewrites the catalog, so commit it
  again after the seed run.
