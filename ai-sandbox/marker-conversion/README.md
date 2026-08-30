# Textbook Conversion Pipeline (Marker)

Converts large, figure- and math-heavy textbook PDFs into structured Markdown (with figures extracted as referenced images) using the [Marker](https://github.com/VikParuchuri/marker) layout/OCR model, run on a spot GPU VM in Google Cloud.

## How it works

1. A local Docker container (`Dockerfile`) provides `gcloud` + SSH tooling and mounts this folder, plus a sibling `academic-hub/` folder, for input/output.
2. `marker_setup.sh` provisions a GPU VM (Deep Learning VM image, NVIDIA L4) with Marker's Python/CUDA stack. It's idempotent -- it detects and skips past a healthy prior setup, so it's run at the start of every session rather than only once.
3. Target PDFs are uploaded to a GCS bucket, then converted remotely in a single batched call to `convert_textbook.py`, which loads Marker's vision models once and reuses them across every book. Chunk boundaries align to real chapter breaks by default (sourced from the PDF's embedded outline or its own printed table of contents), and every output page carries a `<!-- page N -->` tag (physical PDF page index) and, where derivable, a `<!-- folio N -->` tag (the book's own printed page number) -- see `textbook/chapter_index.py`/`textbook/page_markers.py`. It also optionally uses Gemini (via Vertex AI) to read each book's title page and resolve its title/author/year for the output filenames, falling back to regex heuristics if that's unavailable.
4. Converted Markdown + images are copied back down to `academic-hub/<TEXTBOOK_SUBDIR>/processed_outputs/` on the local machine, and the GCS bucket is emptied.
5. The VM is stopped (cheap, reusable) or deleted (fully torn down) to control billing.

See [`gcp_instructions.md`](gcp_instructions.md) for the full step-by-step guide -- one-time GCP project setup, authentication, VM creation, running a batch, and troubleshooting.

## Key files

- `textbook/convert_textbook.py` -- orchestrates the Marker conversion and optional LLM-assisted bibliographic metadata lookup; runs on the VM.
- `marker_setup.sh` -- provisions the VM's Python/CUDA/Marker environment; safe to re-run every session.
- `Dockerfile` -- local container image with `gcloud` and SSH for driving the pipeline from Windows/PowerShell.
- `gcp_instructions.md` -- full step-by-step usage instructions.

## Repository layout

Scripts are grouped by subproject, each a Python package (`__init__.py`), with two shared modules that
almost everything else depends on. Run any script as a module from this directory, e.g.
`python -m notes.transcribe_notes --notes-subdir ...` or `python -m indexer.index_search query "..."` --
not as a bare file path, since the package-qualified imports below need this directory on `sys.path`
(`python -m` does that automatically; `pytest`/`python -m unittest` work too via the root `conftest.py`).

- `common/` -- `gemini_utils.py`: Gemini client setup, retry/backoff, `.env` loading. Used by every subproject.
- `indexer/` -- `index_card.py` (per-file card generation), `index_search.py` (rebuild/search CLI),
  `chunk_index.py` (passage-level chunking/embedding), `retag.py` (corpus-wide tag mining). The
  source-indexer subproject; also depended on by every conversion pipeline below for its indexing hooks.
- `textbook/` -- `convert_textbook.py`, `chapter_index.py`, `page_markers.py` (all VM/GPU-touching --
  see `gcp_instructions.md`), plus `describe_images.py` (local-only figure description). The only files
  that need to be deployed to the GCP VM (along with `common/` and `indexer/`, which they import).
- `notes/` -- `transcribe_notes.py`: local, Gemini-vision-based transcription for problem sets, TA notes,
  exams, and handwritten scans. See `notes_instructions.md`.
- `essays/` -- `convert_essays.py`: local, mammoth-based conversion of `.docx` essays (e.g. PhD
  application statements of purpose) straight to Markdown -- no OCR/vision needed, the `.docx` already
  carries its own structure. See `essays_instructions.md`.
- `postprocessing/` -- `postprocess_notes.py` and its supporting modules: a downstream correction pass
  over `notes/transcribe_notes.py`'s output. Depends on `notes/`.
- `rag/` -- `rag_agent.py`: the multi-turn tutoring agent grounded in passage retrieval. Depends on `indexer/`.
- `tests/` -- flat (not mirrored by subproject); imports are package-qualified to match the layout above.
- `old_attempts/` -- superseded, unmaintained prototypes; not part of the active pipeline.

## Requirements

- A GCP project with billing enabled and GPU quota approved (`PREEMPTIBLE_NVIDIA_L4_GPUS`), plus `gcloud` and Docker installed and running locally.
- `../.env`, filled in from `../.env.example`.
- A sibling `academic-hub/<TEXTBOOK_SUBDIR>/` folder (matching `.env`'s `TEXTBOOK_SUBDIR`) containing the input PDFs.
