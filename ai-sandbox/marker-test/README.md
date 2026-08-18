# Textbook Conversion Pipeline (Marker)

Converts large, figure- and math-heavy textbook PDFs into structured Markdown (with figures extracted as referenced images) using the [Marker](https://github.com/VikParuchuri/marker) layout/OCR model, run on a spot GPU VM in Google Cloud.

## How it works

1. A local Docker container (`Dockerfile`) provides `gcloud` + SSH tooling and mounts this folder, plus a sibling `academic-hub/` folder, for input/output.
2. `marker_setup.sh` provisions a GPU VM (Deep Learning VM image, NVIDIA L4) with Marker's Python/CUDA stack. It's idempotent -- it detects and skips past a healthy prior setup, so it's run at the start of every session rather than only once.
3. Target PDFs are uploaded to a GCS bucket, then converted remotely in a single batched call to `convert_textbook.py`, which loads Marker's vision models once and reuses them across every book. It also optionally uses Gemini (via Vertex AI) to read each book's title page and resolve its title/author/year for the output filenames, falling back to regex heuristics if that's unavailable.
4. Converted Markdown + images are copied back down to `academic-hub/<TEXTBOOK_SUBDIR>/processed_outputs/` on the local machine, and the GCS bucket is emptied.
5. The VM is stopped (cheap, reusable) or deleted (fully torn down) to control billing.

See [`gcp_instructions.md`](gcp_instructions.md) for the full step-by-step guide -- one-time GCP project setup, authentication, VM creation, running a batch, and troubleshooting.

## Key files

- `convert_textbook.py` -- orchestrates the Marker conversion and optional LLM-assisted bibliographic metadata lookup; runs on the VM.
- `marker_setup.sh` -- provisions the VM's Python/CUDA/Marker environment; safe to re-run every session.
- `Dockerfile` -- local container image with `gcloud` and SSH for driving the pipeline from Windows/PowerShell.
- `gcp_instructions.md` -- full step-by-step usage instructions.

## Requirements

- A GCP project with billing enabled and GPU quota approved (`PREEMPTIBLE_NVIDIA_L4_GPUS`), plus `gcloud` and Docker installed and running locally.
- `../.env`, filled in from `../.env.example`.
- A sibling `academic-hub/<TEXTBOOK_SUBDIR>/` folder (matching `.env`'s `TEXTBOOK_SUBDIR`) containing the input PDFs.
