# Research profile (Spec A)

Gives every research document in the literature index a `research_profile` on its index card: report type,
discipline (OpenAlex field and subfields), method class, study design, orientation, evidence role, country and
income group, 3ie intervention/outcome tags with verbatim quotes, and a mechanical `applicability`
(both / intervention_only / outcome_only / not_applicable / not_assessed). Course-material cards never get one.
Design: `docs/superpowers/specs/` (Spec A) and `docs/superpowers/plans/2026-11-13-spec-a-*.md`.

Run from `ai-sandbox/academic-rag-model/`; `--index-root` defaults to `ai-sandbox/research`. The 3ie trees are
git-ignored data read from `<index-root>/resources/3ie/vocab` (override with `--vocab-dir`).

## Run order

```
python -m agent.literature.profile.cli metadata [--source crossref|openalex]   # DOI check; openalex also stores topics
python -m agent.literature.profile.cli classify collect --variant a             # then fill the cards, then:
python -m agent.literature.profile.cli classify submit <run>
python -m agent.literature.profile.cli classify collect --variant b             # second agent, different prompt
python -m agent.literature.profile.cli classify submit <run>
python -m agent.literature.profile.cli tag collect --kind intervention --level 1   # repeat for levels 2, 3
python -m agent.literature.profile.cli tag submit <run>                            # and for --kind outcome
python -m agent.literature.profile.cli summary [--profile agent/literature/profile/profiles/3ie_strict.yaml] [--json]
python -m agent.literature.profile.cli queue
python -m agent.literature.profile.cli refresh-discipline                          # recompute primary/secondary/fit, no run
python -m agent.literature.profile.cli project <folder> <slug>                      # tag a folder's papers with a project
python -m agent.literature.profile.cli folders plan                                # reviews only; nothing moves
python -m agent.literature.profile.cli folders apply --approve <file_id> | --all   # then `folders undo`
python -m agent.literature.profile.cli eval "<path>/all_study_record.csv"
python -m agent.literature.profile.cli label-page --file-id <id> ... --out <dir>     # blind-labelling page, see below
python -m agent.literature.profile.cli eval --labels <labels.json>                  # score saved page labels
```

**Blind labelling.** Publish `<dir>/index.html` as a private Artifact with `terms.json` beside it and the `db`
capability. Labels land in its `labels` collection, one document per `file_id`; save them as one
`{file_id: document}` JSON file for `eval --labels`. The page holds paper excerpts, so keep `<dir>` under the
research folder, never in the repository.

**Document type and publisher.** `report_type` is the document's form and `publisher_type` says who issued it; the
rules both prompts use are `TYPE_RULES` in `classify.py`. To re-read only those two on documents classified earlier:
`classify collect --variant type`, fill the cards, `classify submit <run>`.

**Second reader.** `reader-pack --file-id <id> ... --out <dir>` writes whole transcripts, the rules and the term lists,
with no predictions. Run an independent model on that folder alone, then `reader-check <dir>` verifies every quote and
writes `<dir>/labels.json` for `eval --labels`.

`collect` writes private cards to `<index-root>/.agent_work/<run>/`; the agent fills each `## Result` block;
`submit` validates (quotes must appear on the cited page) and applies. Bounced cards say why; fix and submit again.
`classify|tag api <run> --model M --approve-cost USD` sends the cards to the paid Gemini key instead and refuses
above the free limit without `--approve-cost`. Reruns with the same prompt version do nothing (`--redo` to force).

## Discipline check with two Gemini agents

Variant `a` classifies fully; variant `b` is a differently worded "librarian" prompt that only picks the field and
subfields. Run each as its own run (ideally in separate agent sessions).

**Primary discipline** (drives folders) is the OpenAlex field when its topic share reaches 0.8; otherwise the
best-supported label from pooled evidence (each agent adds its confidence to its label, each OpenAlex field adds its
share, divided by the number of sources; ties go to agent `a`). **Secondary discipline** is the runner-up of the same
pool, kept for every paper that has one (`secondary_discipline`, `secondary_score`; the top three are in
`discipline_scores`). **`discipline_fit`** is `clear` when the primary's pooled score is at least 0.6 and leads the
runner-up by 0.3, else `mixed` -- a record of papers that do not sit cleanly in one discipline, so none are lost to an
arbitrary choice. Disagreement no longer raises a review item; only a missing second agent check does. Genuinely
semantic splits are not reviewed. Human decisions live in `.index/research_profile/decisions.json` and override the
models. `refresh-discipline` recomputes all of this from the stored readings with no agent run.

## Notes

- Only documents with a readable transcript at the card's `path` are classified; others are skipped with the reason.
- `--file-id` (repeatable) limits any stage to specific documents.
- Tagging prompt `tag-v3`: a review or synthesis (systematic review, meta-analysis, evidence synthesis) counts as
  reporting the interventions and outcomes it synthesises, not ones it only lists as background. Report types outside
  `RESEARCH_REPORT_TYPES` (book chapters, books, notes) are `not_assessed` and never tagged.
- **Projects.** `projects` on a card is a list of project slugs (an `independent-research/projects/` folder name, else
  the old folder name). `project <folder> <slug>` adds one to every paper in a folder. `folders plan` leaves a paper
  with a project where it is; a loose paper goes to its discipline folder. This is the two-tier layout: project
  folders where a paper has a project, discipline folders otherwise.
- **Folder layout.** `<base>/<discipline-slug>/`; Social Sciences splits by its top OpenAlex subfield
  (`social-sciences/development/`, `.../education/`, `general` when there is none). Disciplines with fewer than 3
  papers and non-research documents go to `other`. A card's `course` is its top-level folder (what a re-index derives);
  nested folders live in `path`. Moves work from the card's paths, so papers loose in the base folder (whose `course`
  is their file name) move correctly; transcript, PDF, `.meta.json` and the transcriber page caches move together.
- Folder moves are keyed by `file_id`, logged in `.index/research_profile/folder_moves.json`, and reversible.
- Byte-identical duplicates need only one copy per folder; copies in different project folders may stay.

**Comparing readings.** `compare --labels <labels.json> --reader-pack <folder> --out <dir>` sets the owner's
labels, the cards and the second reader side by side on report type and applicability, and writes a page (publish
with the `db` capability) listing only the differences, without saying who answered what. Export its `rulings`
collection to one JSON file per id, then `adjudicate --comparison <dir>/comparison.json --rulings <folder>` writes
`reference.json` for `eval --labels`. The rulings are made with the other answers in view, so the reference is
adjudicated, not blind.
