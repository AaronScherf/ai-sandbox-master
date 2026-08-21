# Textbook Conversion Pipeline

## Prerequisites

* A GCP project with **billing enabled**, and the account running these commands has Owner/Editor on it (needed for the IAM and service-account changes in Steps 1.2/2.1).
* **GPU quota** approved for the zone you'll use, specifically `PREEMPTIBLE_NVIDIA_L4_GPUS` (Spot VMs draw from the preemptible quota pool, a separate metric from `NVIDIA_L4_GPUS`) if you're using Step 1.3's VM creation command as-is. This is the single most common blocker on a brand-new project -- request it under IAM & Admin > Quotas in the Console *before* Step 1.3, since approval isn't always instant.
* `gcloud` and Docker installed locally, and Docker running.
* A copy of `.env.example` (in the parent directory of this folder) filled in as your own `.env` -- see that file for what each variable means. `.env` is gitignored; never commit your real one.
* A folder named `academic-hub` as a sibling of this `marker-conversion` folder, containing a subfolder matching whatever you set `TEXTBOOK_SUBDIR` to in Step 0.2 below -- that's where your input PDFs go and where processed output lands locally.

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

Change this list to update the batch of target textbooks. `convert_textbook.py` loads Marker's vision models exactly once per invocation and reuses them across every file in this list, so batching several books here is substantially cheaper than converting them one invocation at a time -- prefer adding to this list over running the pipeline repeatedly for one book each time.

```bash
export PDF_FILENAMES=(
    "textbook.pdf"
    "rudin-walter-principles-of-mathematical-analysis-1976.pdf"
    "Linear Algebra Done Right (4th edition) Axler.pdf"
)
```

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

### 1.3 One-time: create the GCS bucket and VM instance (skip if you already have both)

Skip this entirely if `$BUCKET_NAME` and `$VM_INSTANCE_NAME` already exist. This only needs to run once ever per project -- not once per session (that's Steps 2-3).

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

```bash
gcloud compute scp marker_setup.sh convert_textbook.py chapter_index.py page_markers.py $VM_INSTANCE_NAME:~/ --zone=$GCP_ZONE --tunnel-through-iap
```

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
python3 -u ~/convert_textbook.py $GCS_INPUT_URIS --output "gs://$BUCKET_NAME/processed_outputs"
EOF
```

A single book that turns out to be unusually slow or malformed no longer stalls the whole batch indefinitely: each Marker call is bounded by `--chunk-timeout` (default 1800s per chunk) and `--page-timeout` (default 240s per page fallback) before it's treated as hung and falls back automatically, and one book failing outright is logged and skipped rather than aborting the remaining books in the list. Override the defaults if needed, e.g.:

```bash
# python3 -u ~/convert_textbook.py $GCS_INPUT_URIS --output "gs://$BUCKET_NAME/processed_outputs" --chunk-timeout 2400 --page-timeout 300
```

LLM-assisted bibliographic metadata (Step 1.2) is on by default and needs no flags in the common case -- it auto-detects the GCP project from the VM's credentials. If you haven't done the Step 1.2 one-time setup yet, or want to skip it for a run, add `--no-llm-bib` to go straight to the regex fallback.

If you still get an ERROR related to scopes and authorization by GCP at this step, Step 2.1's check should have already caught and fixed it -- rerun Step 2.1 (e.g. if the VM was recreated since your last session and you skipped straight to Step 3).

### 3.4 Export the structured artifacts to the local host

Google Cloud VMs do not natively mount Google Drive. To retrieve the markdown and image artifacts, execute a recursive secure copy from the VM back to the local Docker workspace. The volume mount established in Step 0.1 will automatically synchronize these files to your local Windows filesystem.


```bash
# Ensure the local target directory structure exists prior to transfer.
# Uses the /academic-hub mount point directly (same convention as Step 3.2)
# rather than a "../academic-hub" relative path -- a relative path here
# depends on the shell's cwd still being exactly /workspace, which can
# silently drift over a long manual session and land output in the wrong
# place instead of erroring.
mkdir -p "/academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/"

# Recursively download the processed artifacts from the GCS bucket
gcloud storage cp -r gs://$BUCKET_NAME/processed_outputs/* "/academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/"

# Empty the bucket
gcloud storage rm -r gs://$BUCKET_NAME/processed_outputs/* gs://$BUCKET_NAME/input_documents/* --continue-on-error
```

## Step 4: Terminate the Compute Instance

To halt billing cycles, the VM must be explicitly stopped or deleted upon completion of the pipeline. 

Only use one block!

```bash
# Option A: Stop the instance. This halts compute billing but preserves the disk 
# (and provisioning state) for future executions. Minimal storage fees apply.
gcloud compute instances stop $VM_INSTANCE_NAME --zone=$GCP_ZONE
```

This deletes your VM instance permanently! It requires typing a confirmation phrase before it will run, specifically so that copy-pasting or running through this entire document in one pass can't silently delete the instance -- if you don't type it, nothing happens.
```bash
# Option B: Delete the instance entirely. This permanently destroys the disk and 
# halts all billing mechanisms. Provisioning (Step 3.1) must be repeated upon recreation.
read -p "Type DELETE to permanently destroy $VM_INSTANCE_NAME and its disk: " CONFIRM_DELETE
if [ "$CONFIRM_DELETE" = "DELETE" ]; then
    gcloud compute instances delete $VM_INSTANCE_NAME --zone=$GCP_ZONE --quiet
else
    echo "Aborted -- '$VM_INSTANCE_NAME' was NOT deleted."
fi
```