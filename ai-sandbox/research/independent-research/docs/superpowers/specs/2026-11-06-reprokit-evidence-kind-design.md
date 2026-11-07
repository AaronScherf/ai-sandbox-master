# Addendum: the `evidence` project kind (reprokit v0.4.0)

Date: 2026-11-06. Status: draft for owner review. Addendum to
`2026-10-31-reproducible-research-framework-design.md` (section 4, "Evidence/desk repo");
the original text is unchanged. Handoff: `../plans/2026-11-06-reprokit-evidence-kind-handoff.md`.

## 1. Intent

An evidence repo treats a project's **evidence base as data** and its **synthesis as a
function of that data**. The point is not to reproduce a literature summary. It is to let
anyone ask: what changes if sources are added or removed, which claims rest on which
sources, and what did each re-extraction cost? Sources are not only journal articles: they
include datasets, web pages, grey-literature reports, and project packages (procurement
documents, progress reports, monitoring data).

Projects waiting on it: `evidence-map`, `transferability`, later `systems-dynamics`.

## 2. Goals, non-goals, anti-goals

Goals
- Recompute a synthesis from a manifest of typed sources; support add/remove (leave-one-out,
  subset) sensitivity runs.
- Every claim in the synthesis cites manifest entries, and `validate` checks it.
- Rights-safe: no PDFs, full text or transcriptions committed; confidential material never
  leaves its class.
- Cost-transparent: paid AI use goes through `compute.yaml` and the $1 warning rule.
- Study-kind output stays byte-identical.

Non-goals (v0.4.0)
- Fetching and transcribing sources (acquisition adapters), searching OpenAlex, Zotero
  sync. These are a later release; v0.4.0 defines the data formats they will write to.
- The `library` kind. The 3ie taxonomy hooks (spec phase 12, still blocked).

Anti-goals
- A second parallel mechanism for datasets (reuse descriptors).
- Empty scaffolding for small projects (minimal tier, section 8).
- Hidden monorepo coupling: converters are pluggable adapters, never imports from the monorepo.

## 3. Unit of work and "reproduce"

Pipeline: search protocol (recorded) -> screen -> extract -> aggregate -> synthesize.
"Reproduce" means: given the manifest and the cached extraction records, regenerate the
aggregate tables and the rendered synthesis deterministically, and verify each source
still resolves by identifier. It does not mean re-running the search or any paid AI step.
Re-extraction is an explicit, cost-warned command.

LLM extraction is not byte-deterministic, so the **committed extraction record is the
artifact**, keyed by source id, content hash, and extractor/prompt version. Aggregation
and sensitivity runs are deterministic code over those records. Narrative prose is
labelled non-reproducible.

## 4. Citation manifest (`evidence/manifest.yaml`)

New schema `schemas/evidence_manifest.json` (own `schema_version`, starting 0.1.0; the
existing `manifest.json` is the run manifest). YAML now; convertible to JSON later with
the same schema.

Entry fields:
- `id` (local slug, unique), `type` (article, report, dataset, webpage, project_package, other)
- `identifier`: `{scheme: doi | openalex | dataset_doi | url | file_hash, value}`. At least one required.
  Extra identifiers may be listed under `also`.
- `title`, `year`, `retrieved_on`
- `access_class` (open, paywalled, restricted, confidential, unknown)
- `screening_status` (candidate, included, excluded) with `screening_reason`
- `verification_status`: reuse the study-kind vocabulary (proposed, source-verified, ...)
- `content_hash` (of the local copy, when one was acquired), `converter` (name+version)
- `snapshot`: archive URL and date. **Required for `webpage`** to reach source-verified.
- `rights_note`; `extraction` points to the cached record.
- Abstracts are not stored; they are re-fetched by identifier (OpenAlex), per owner decision.

Type rules: `dataset` entries link to a descriptor in `data/descriptors/` (no second
dataset mechanism). `project_package` entries store hash and location pointer only, and are
rejected in a `public` repo unless their `access_class` allows it.

## 5. Extraction cache and sensitivity

`evidence/extractions/<id>.yaml`: structured fields (schema per project, declared in
`evidence/extraction_schema.yaml`), page/section locators, no bulk quotation,
`extractor`, `prompt_version`, `source_content_hash`, `cost`. A record is stale when the
source hash or extractor version changed. `reprokit evidence-run --exclude <ids>` /
`--only <ids>` recomputes aggregates over a subset; adding a source only requires that
source's record. (Command naming is the builder's call.)

Local, gitignored role directories (no files committed): `cache/sources/` (fetched or
hand-placed originals), `cache/text/` (transcriptions). Validator rejects PDFs and
full-text files anywhere else in the repo.

## 6. Claims versus sources

`synthesis.md` uses `[@id]` markers. `validate` checks: every marker resolves to a
manifest entry; every cited entry is `included`; cited entries must be `source-verified`
(otherwise reported as a problem); every `included` entry has an extraction record. Network
resolution is a separate `reprokit verify-sources` command, never in the 30-second test path.

## 7. Zotero

Optional. The manifest is the only source of truth, and reproduction needs no account.
`sources` in the charter may record an optional `zotero_group`; the API key lives in `.env`
read via `reprokit.env`, never logged.

## 8. Charter, template, validation

- **Charter:** stay on 0.2.0. Add an optional `evidence:` block allowed only when
  `kind: evidence` (`manifest`, `inclusion_criteria`, `search_protocol`). 0.1/0.2 files keep
  validating. Move to 0.3.0 only if required fields are needed.
- **Template:** Copier conditionals on `kind` inside the single `template/` (`_exclude`
  study-only paths). A test generates a study repo with and without the change and asserts
  byte-identity.
- **Dispatch:** `validate` runs the shared core, then a per-kind module
  (`evidence_rules.py`, kept near 150 lines or fewer).
- **Tiers:** minimal = `project.yaml`, `evidence/manifest.yaml`, `synthesis.md`, protocol.
  Opt-in (Copier question `screening_pipeline`) = extraction schema/cache, sensitivity
  command, `compute.yaml`, `agents.yaml`. `systems-dynamics` starts minimal.
- **quick-check:** a fixture manifest (3 fake entries, offline resolve stubs, tiny
  extraction records) run through the real validate -> aggregate -> render path.
- **CI:** Linux and Windows, secret scan, run summary as for study repos.

## 9. Migration and first test case

A one-off script parses the 4 existing `literature_review.md` files (title, authors, year,
venue, DOI link) into manifests (`type: article`, `verification_status: proposed`).
Test case: generate `evidence-map` from a local clone into a scratch location, migrate its
review, run `validate` and `quick-check`, confirm CI in a scratch repo. Do not generate into
`projects/` until the owner says Codex's reorganization has landed.

## 10. Left to the builder / open

- Command names and flags; aggregate output formats; exact `rights_note` vocabulary.
- Whether `verify-sources` also checks snapshots (builder's call, default: DOI/OpenAlex only).
- Fetch/transcribe adapters, Zotero sync, OpenAlex search: a later release.
- Release (tag, push) only on owner approval.
