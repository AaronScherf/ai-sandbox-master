# Textbook Conversion Pipeline

## Prerequisites

* A GCP project with **billing enabled**, and the account running these commands has Owner/Editor on it (needed for the IAM and service-account changes in Steps 1.2/2.1).
* **GPU quota** approved for the zone you'll use, specifically `PREEMPTIBLE_NVIDIA_L4_GPUS` (Spot VMs draw from the preemptible quota pool, a separate metric from `NVIDIA_L4_GPUS`) if you're using Step 1.3's VM creation command as-is. This is the single most common blocker on a brand-new project -- request it under IAM & Admin > Quotas in the Console *before* Step 1.3, since approval isn't always instant.
* `gcloud` and Docker installed locally, and Docker running.
* A copy of `.env.example` (in the parent directory of this folder) filled in as your own `.env` -- see that file for what each variable means. `.env` is gitignored; never commit your real one.
* A folder named `academic-hub` as a sibling of this `academic-rag-model` folder, containing a subfolder matching whatever you set `TEXTBOOK_SUBDIR` to in Step 0.2 below -- that's where your input PDFs go and where processed output lands locally.

## Step 0: Initialize the Docker Container

Execute the following script from PowerShell within the project directory (containing the `Dockerfile`, `.env`, and `convert_textbook.py`). Ensure the Docker daemon is operational prior to execution.

### Step 0.1: Build and instantiate the environment

* **Initial Execution:** This builds the image and instantiates a named container. The `colab-cli` dependencies have been structurally excised.
* **Subsequent Executions:** Skips the build phase and restores the existing container via `docker start`.
* Loads `PROJECT_ID` from the `.env` file located in the parent directory.
* Mounts the current project directory into `/workspace` to ensure local synchronization of the extraction scripts.
* Persists `gcloud` authentication configurations across container lifecycles via volume mounting.

```powershell
if (docker ps -aq -f "name=^gcp-container$") {
    docker start -ai gcp-container
} else {
    docker build -t gcp-runner .
    docker run -it --name gcp-container `
        --env-file ../.env `
        -v ${PWD}:/workspace `
        -v ${PWD}\..\academic-hub:/academic-hub `
        -v gcloud-config:/root/.config/gcloud `
        -v gcloud-ssh:/root/.ssh `
        gcp-runner
}
```
Note: To stop and remove a previously created Docker container (in case you need to reconfigure it or you've changed env), use:
docker stop gcp-container
docker rm gcp-container

You are now operating within the container's interactive bash shell for all subsequent operations.

### Step 0.2: Declare run-specific variables

`TEXTBOOK_SUBDIR` and `PDF_FILENAMES` identify a particular run of the pipeline (which subject folder, which books in it) rather than durable per-machine config, so they're declared here instead of in `.env`.

```bash
# Path, relative to the academic-hub/ folder mounted into the container
# (Step 0.1), where input PDFs live and where processed output will be
# written back to.
export TEXTBOOK_SUBDIR="academic_resources/math-camp/textbooks-and-papers"
```

`PDF_FILENAMES` is populated automatically from whatever `.pdf` files sit directly inside `TEXTBOOK_SUBDIR` -- change which books get converted by changing what's in that folder, not by editing a list here. This is what makes running this same pipeline against a new course directory (set `TEXTBOOK_SUBDIR` above, drop that course's PDFs in the folder) a one-line change instead of also needing every filename retyped. `convert_textbook.py` loads Marker's vision models exactly once per invocation and reuses them across every file found, so batching a whole course's books together here is substantially cheaper than converting them one invocation at a time.

```bash
shopt -s nullglob
PDF_FILENAMES=()
for pdf_path in "/academic-hub/$TEXTBOOK_SUBDIR"/*.pdf; do
    PDF_FILENAMES+=("$(basename "$pdf_path")")
done
export PDF_FILENAMES

if [ ${#PDF_FILENAMES[@]} -eq 0 ]; then
    echo "[FATAL] No .pdf files found directly under /academic-hub/$TEXTBOOK_SUBDIR -- check TEXTBOOK_SUBDIR." >&2
else
    echo "[System] Found ${#PDF_FILENAMES[@]} PDF(s) in $TEXTBOOK_SUBDIR:"
    printf '  %s\n' "${PDF_FILENAMES[@]}"
fi
```

This only looks directly inside `TEXTBOOK_SUBDIR` (not its `processed_outputs/` subfolder), so re-running against the same folder won't try to re-ingest already-converted output.

### Step 0.3: Verify SDK Installation

Validate the Google Cloud SDK installation.

```bash
gcloud version
```

## Step 1: Authenticate the SDK within the Container

### 1.1 Update the global active developer identity profile

```bash
gcloud auth application-default login --disable-quota-project
gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID
```

### 1.2 One-time: enable Vertex AI for LLM-assisted bibliographic metadata (optional)

`convert_textbook.py` uses a Gemini model, via Vertex AI, to read each book's title page and identify its title/author/publication year when the PDF's own embedded metadata is missing or unreliable (regex pattern-matching is used only as a fallback if this is unavailable). It reuses the VM's existing credentials rather than needing a separate API key, but the underlying GCP project needs two things granted **once, ever**, that a VM-level fix can't provide -- these are project IAM/API settings, not anything `marker_setup.sh` or Step 2.1 touches:

```bash
# Enable the Vertex AI API on the project (idempotent -- harmless to rerun).
gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID

# Grant the VM's service account permission to call it.
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/aiplatform.user"
```

If you skip this (or it's not set up yet), `convert_textbook.py` still works -- it just logs a warning per book and falls back to the regex heuristic, same as before this feature existed. Cost is negligible: each book sends a few KB of title-page text to a fast/cheap Gemini model once.

### 1.3 Create the GCS bucket (one-time) and VM instance (recreate each session)

The bucket only needs to be created once ever per project -- skip that part if `$BUCKET_NAME` already exists.

The VM is a different story if you're following Step 4's recommended workflow of deleting the instance after every session (see the cost rationale there): a Persistent Disk is billed for its full provisioned size for as long as it exists, whether the VM is running, stopped, or deleted-but-disk-kept -- there's no way to pause that charge short of not having the disk at all. For a pipeline run about once a month, recreating the VM from scratch each time (this command) genuinely costs $0 between sessions, versus a stopped instance's disk quietly billing ~$0.10/GB/month the whole time it sits idle. Nothing on the disk is worth paying to avoid this: input/output data always flows through the GCS bucket, never the VM disk (Steps 3.2-3.4), and everything `marker_setup.sh` installs (apt packages, pip packages, the pulled vLLM Docker image) is re-derived automatically from public sources on the next run -- see Step 3.1's idempotency note. So run this VM-creation command at the start of every session that follows a Step 4 deletion, not just the first time ever.

`marker_setup.sh` hard-requires a VM booted from a Deep Learning VM image with a matching torch/CUDA/driver stack already preinstalled (see the comments at the top of that file) -- it will fail fast and loudly on a generic Ubuntu image rather than silently misbehave, but you still need the right image to begin with. The command below matches the exact image family, machine type, and GPU this pipeline has been validated against.

```bash
# Bucket
gcloud storage buckets create "gs://$BUCKET_NAME" --project=$PROJECT_ID --location="${GCP_ZONE%-*}"

# VM: g2-standard-4 + a single NVIDIA L4 is the machine-type/GPU pairing this
# pipeline expects (g2 machine types only support L4 GPUs -- if you need a
# different GPU, e.g. for quota reasons, you'll need a different machine
# type family too; see GCP's accelerator/machine-type compatibility docs).
# --scopes=cloud-platform here means Step 2.1's check should find nothing to
# fix on a VM created this way -- it stays in the instructions as a safety
# net for VMs created some other way (Console, an older command, etc).
gcloud compute instances create $VM_INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=$GCP_ZONE \
    --machine-type=g2-standard-4 \
    --accelerator=type=nvidia-l4,count=1 \
    --image-family=pytorch-2-9-cu129-ubuntu-2204-nvidia-580 \
    --image-project=ml-images \
    --boot-disk-size=100GB \
    --boot-disk-type=pd-balanced \
    --maintenance-policy=TERMINATE \
    --provisioning-model=SPOT \
    --instance-termination-action=STOP \
    --scopes=cloud-platform
```

If `--tunnel-through-iap` fails later (Steps 2.2/3.1/3.3) with a connection or permission error rather than an authentication error, your project's default network may be missing the firewall rule IAP needs:

```bash
gcloud compute firewall-rules create allow-iap-ssh \
    --project=$PROJECT_ID \
    --network=default \
    --direction=INGRESS \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=35.235.240.0/20
```

## Step 2: Prepare the Virtual Machine

### Step 2.1: Ensure the VM's service account has sufficient scope

`convert_textbook.py` runs on the VM itself and uploads output to GCS using the VM's *attached service account*, which is subject to an instance-level OAuth scope in addition to whatever IAM roles that service account holds. A freshly created VM commonly defaults to a scope that can read GCS but not write to it -- conversion then runs to completion and fails only at the very last step (the output upload), which is a frustrating way to lose a run.

This check is a single cheap `describe` call (no VM state change, no billing impact), so it's safe to run at the start of every session regardless of whether the VM is new or one you've used before:

* **Scope already correct** (the common case for a VM you've already fixed once): prints a confirmation and does nothing else.
* **Scope missing** (expected the first time a given VM instance is used): stops the VM if it's running (required -- `set-service-account` only works on a stopped instance), grants `cloud-platform` scope, and starts it back up. This only needs to happen once per VM instance; it persists across ordinary stop/start and only needs redoing if the VM is deleted and recreated (Step 4, Option B).

```bash
CURRENT_SCOPES=$(gcloud compute instances describe $VM_INSTANCE_NAME --zone=$GCP_ZONE --format="value(serviceAccounts[0].scopes)")

if [[ "$CURRENT_SCOPES" == *"cloud-platform"* ]]; then
    echo "[System] VM already has cloud-platform scope -- nothing to do."
else
    echo "[System] VM is missing cloud-platform scope (found: '$CURRENT_SCOPES')."
    echo "[System] This is expected the first time this VM instance is used and needs a one-time fix."

    VM_STATUS=$(gcloud compute instances describe $VM_INSTANCE_NAME --zone=$GCP_ZONE --format="value(status)")
    if [ "$VM_STATUS" != "TERMINATED" ]; then
        echo "[System] Stopping VM to change its service account scope (only possible while stopped)."
        gcloud compute instances stop $VM_INSTANCE_NAME --zone=$GCP_ZONE
    fi

    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
    SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

    echo "[System] Granting cloud-platform scope to $SERVICE_ACCOUNT."
    gcloud compute instances set-service-account $VM_INSTANCE_NAME \
        --zone=$GCP_ZONE \
        --service-account=$SERVICE_ACCOUNT \
        --scopes=cloud-platform

    echo "[System] Restarting VM."
    gcloud compute instances start $VM_INSTANCE_NAME --zone=$GCP_ZONE
fi
```

### Step 2.2: Synchronize scripts to the Virtual Machine

Transfer the provisioning and execution scripts to the home directory of the remote Compute Engine instance.

This will trigger the SSH key metadata to update, which may require additional authentication.

Note: If you get a 255 error, check to ensure the VM is running (and not stopped)

```bash
gcloud compute scp marker_setup.sh $VM_INSTANCE_NAME:~/ --zone=$GCP_ZONE --tunnel-through-iap
gcloud compute scp --recurse common indexer textbook $VM_INSTANCE_NAME:~/academic-rag-model/ --zone=$GCP_ZONE --tunnel-through-iap
```

`common/`, `indexer/`, and `textbook/` are copied recursively so `convert_textbook.py`'s package-qualified
imports (`from common.gemini_utils import ...`, `from indexer.index_card import ...`, `from textbook.page_markers import ...`)
resolve on the VM the same way they do locally. `notes/`, `postprocessing/`, and `rag/` aren't needed here --
nothing under `textbook/` imports them. (This also fixes a real, previously-undocumented gap: `index_card.py`
and `gemini_utils.py` were never actually transferred to the VM by the old per-file `scp` line above, despite
`convert_textbook.py` importing both.)

## Step 3: Execute the Extraction Pipeline

### 3.1 Execute environment provisioning

This provisions the OS and Python dependencies. It's safe -- and recommended -- to run this at the start of every session rather than deciding for yourself whether it's needed: `marker_setup.sh` checks the VM's persistent disk for a completed, still-healthy prior setup and, if found, skips the entire build and exits in a few seconds instead of wasting compute redoing it.

* **Fresh instance:** no prior setup found -- runs the full build.
* **Already provisioned:** prior setup found and re-verified healthy -- skips straight through.
* **Broken/partial state:** prior setup found but re-verification fails, or the build itself fails partway -- the script stops and prints an explicit message telling you to stop, delete, and recreate the VM (Step 4, Option B) rather than silently limping forward on an unknown disk state.

```bash
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="bash -s" << 'EOF'
bash ~/marker_setup.sh
EOF
```

Debug step if torchaudio problems: Run the following to test if torchaudio is still causing problems in the current GCP VM image

gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="bash -s" << 'EOF'
python3 -c "import torch; import transformers; print('torch:', torch.__version__, '| transformers:', transformers.__version__, '| CUDA:', torch.cuda.is_available())"
EOF

### 3.2 Stage the input documents in Google Cloud Storage
Before executing the extraction, each raw PDF must be uploaded to your GCS bucket so the remote Virtual Machine can access it.

```bash
for PDF_FILENAME in "${PDF_FILENAMES[@]}"; do
    gcloud storage cp "/academic-hub/$TEXTBOOK_SUBDIR/$PDF_FILENAME" "gs://$BUCKET_NAME/input_documents/$PDF_FILENAME"
done
```

### 3.3 Convert the PDFs to structured artifacts

Execute the conversion. Because the underlying hardware is persistent, this command can be run iteratively across separate sessions without re-provisioning the environment or recompiling binaries.

All PDFs staged in Step 3.2 are passed to a single `convert_textbook.py` invocation, so the vision models load once and are reused across every book -- avoid splitting this into one `gcloud compute ssh` call per book, since that would reload the models (and re-spawn the vLLM server) each time.

Filenames are shell-quoted with `printf %q` before being joined into one string -- this heredoc is sent as literal text to the remote `bash -s`, which re-parses it from scratch, so any spaces, parentheses, or other shell-special characters in a filename need to survive that round trip intact rather than being word-split apart.

```bash
GCS_INPUT_URIS=""
for PDF_FILENAME in "${PDF_FILENAMES[@]}"; do
    printf -v QUOTED_URI '%q' "gs://$BUCKET_NAME/input_documents/$PDF_FILENAME"
    GCS_INPUT_URIS+="$QUOTED_URI "
done

gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="bash -s" << EOF
echo "[System] Purging residual VLM server locks."
sudo rm -f /root/.cache/datalab/surya/vllm_server.lock

echo "[System] Initiating document extraction."
cd ~/academic-rag-model && python3 -u -m textbook.convert_textbook $GCS_INPUT_URIS --output "gs://$BUCKET_NAME/processed_outputs"
EOF
```

A single book that turns out to be unusually slow or malformed no longer stalls the whole batch indefinitely: each Marker call is bounded by `--chunk-timeout` (default 1800s per chunk) and `--page-timeout` (default 240s per page fallback) before it's treated as hung and falls back automatically, and one book failing outright is logged and skipped rather than aborting the remaining books in the list. Override the defaults if needed, e.g.:

```bash
# python3 -u -m textbook.convert_textbook $GCS_INPUT_URIS --output "gs://$BUCKET_NAME/processed_outputs" --chunk-timeout 2400 --page-timeout 300
```

LLM-assisted bibliographic metadata (Step 1.2) is on by default and needs no flags in the common case -- it auto-detects the GCP project from the VM's credentials. If you haven't done the Step 1.2 one-time setup yet, or want to skip it for a run, add `--no-llm-bib` to go straight to the regex fallback.

If you still get an ERROR related to scopes and authorization by GCP at this step, Step 2.1's check should have already caught and fixed it -- rerun Step 2.1 (e.g. if the VM was recreated since your last session and you skipped straight to Step 3).

### 3.4 Export the structured artifacts to the local host

Google Cloud VMs do not natively mount Google Drive. To retrieve the markdown and image artifacts, execute a recursive secure copy from the VM back to the local Docker workspace. The volume mount established in Step 0.1 will automatically synchronize these files to your local Windows filesystem.

```bash
# Ensure the local target directory structure exists prior to transfer.
# Uses the /academic-hub mount point directly (same convention as Step 3.2)
# rather than a "../academic-hub" relative path 
mkdir -p "/academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/"
```


```bash

# Recursively download the processed artifacts from the GCS bucket
gcloud storage cp -r gs://$BUCKET_NAME/processed_outputs/* "/academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/"

# Empty the bucket
gcloud storage rm -r gs://$BUCKET_NAME/processed_outputs/* gs://$BUCKET_NAME/input_documents/* --continue-on-error
```

## Step 4: Terminate the Compute Instance

To halt billing cycles, the VM must be explicitly stopped or deleted upon completion of the pipeline.

**Default to Option B (delete)** for the usage pattern this pipeline is actually run under -- occasional, roughly-monthly conversion batches. A Persistent Disk bills for its full provisioned size the entire time it exists, regardless of whether the VM attached to it is running or stopped -- "stopped" halts *compute* billing only, not storage. For a disk that then sits idle for weeks between runs, that's real, avoidable monthly cost for no benefit: nothing on the disk is data you'd miss (books/outputs only ever live in the GCS bucket or your local machine, per Steps 3.2-3.4), and everything the disk's provisioning represents (Step 3.1) is mechanically reproduced from public package sources the next time `marker_setup.sh` runs. Deleting gives you a real $0 between sessions; stopping does not.

Only use one block!

Reach for **Option A (stop)** only in the one case where paying to keep the disk actually saves you something real: you expect to run the pipeline again **later the same day** (or otherwise before your next natural stopping point), and want to skip re-running `marker_setup.sh`'s few-minutes of provisioning in between. It's a short-lived convenience, not the default end-of-session step.
```bash
# Option A: Stop the instance. This halts compute billing but preserves the disk
# (and provisioning state) for a same-day rerun. Storage fees continue to
# accrue for as long as the disk exists, even while stopped.
gcloud compute instances stop $VM_INSTANCE_NAME --zone=$GCP_ZONE
```

This deletes your VM instance permanently! It requires typing a confirmation phrase before it will run, specifically so that copy-pasting or running through this entire document in one pass can't silently delete the instance -- if you don't type it, nothing happens.
```bash
# Option B (default/recommended): Delete the instance entirely. This
# permanently destroys the disk and halts all billing mechanisms, compute
# and storage alike. Recreate it via Step 1.3's VM-creation command next
# time -- provisioning (Step 3.1) runs again automatically at that point,
# same as it would on any fresh instance.
read -p "Type DELETE to permanently destroy $VM_INSTANCE_NAME and its disk: " CONFIRM_DELETE
if [ "$CONFIRM_DELETE" = "DELETE" ]; then
    gcloud compute instances delete $VM_INSTANCE_NAME --zone=$GCP_ZONE --quiet
else
    echo "Aborted -- '$VM_INSTANCE_NAME' was NOT deleted."
fi
```

## Step 5: Describe Images Locally

This step runs entirely on your local machine, **outside the Docker container** (exit the container's shell first, or just open a new PowerShell window) -- it needs no GPU, no VM, and no gcloud/IAP tunnel, just local files and network access to the Gemini API. There's no reason to keep billing the VM while this runs, which is why it comes after Step 4 rather than before it.

For each image in a book's converted markdown, `describe_images.py` asks a Gemini model whether the image is meaningful academic content (a diagram, chart, plot, or figure) worth describing for RAG/study use, or decorative/non-informational content worth skipping (stock photos, publisher logos, cover art). Images before the book's first real chapter (cover art, title-page decoration) are filtered out for free, no LLM call needed. The result is a derived `<BookName>.rag.md` file with descriptions inserted directly beneath each kept image's link -- the original `<BookName>.md` is never modified.

### Step 5.1: One-time local setup

```powershell
cd academic-rag-model
pip install google-genai python-dotenv
```

Requires a `GEMINI_API_KEY` in your `.env` (see `.env.example` -- a free key from aistudio.google.com/apikey works, or enable billing on that key for higher rate limits; either way this step's own API cost is negligible, well under $1 even for an image-heavy book).

### Step 5.2: Run it

Batches over every book folder found under `academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/` by default -- reuse the same `$TEXTBOOK_SUBDIR` you set in Step 0.2 for this run.

```powershell
$TEXTBOOK_SUBDIR="academic_resources/math-camp/textbooks-and-papers"

python -m textbook.describe_images --textbook-subdir $TEXTBOOK_SUBDIR
```

* Add `--book "SomeBookFolderName"` to process just one book instead of the whole batch.
* Add `--dry-run` first to see which images would be processed (and which are already cached from a prior run) without spending any API calls.
* Each image's result is cached in `<BookName>_image_descriptions.json` inside that book's output folder as it's produced -- if the run is interrupted (network blip, rate limit, closed terminal), rerunning the same command picks up where it left off instead of re-billing already-processed images.

Note: this step depends on `run_config.json` being present in the book's output folder (written automatically by Step 3.3/3.4 as of this feature). Output converted before this feature shipped won't have it, and won't have the page-prefixed image links this script looks for either -- rerun Step 3 on those books first.
