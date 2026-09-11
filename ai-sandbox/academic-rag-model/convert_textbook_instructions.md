# Textbook Conversion Pipeline

## Prerequisites

* A GCP project with **billing enabled**, and the account running these commands has Owner/Editor on it (needed for the IAM and service-account changes in Steps 1.2/2.1).
* **GPU quota** approved for the zone you'll use, specifically `PREEMPTIBLE_NVIDIA_L4_GPUS` (Spot VMs draw from the preemptible quota pool, a separate metric from `NVIDIA_L4_GPUS`) if you're using Step 1.3's VM creation command as-is. This is the single most common blocker on a brand-new project -- request it under IAM & Admin > Quotas in the Console *before* Step 1.3, since approval isn't always instant.
* `gcloud` and Docker installed locally
* A copy of `.env.example` (in the parent directory of this folder) filled in as your own `.env` -- see that file for what each variable means. `.env` is gitignored; never commit your real one.
* A folder named `academic-hub` as a sibling of this `academic-rag-model` folder, containing a subfolder matching whatever you set `TEXTBOOK_SUBDIR` to in Step 0.2 below -- that's where your input PDFs go and where processed output lands locally.

## Step 0: Initialize the Docker Container

Execute the following script from PowerShell within the project directory (containing the `Dockerfile`, `.env`, and `convert_textbook.py`). Ensure the Docker daemon is operational prior to execution.

### Step 0.1: Build and instantiate the environment

* Ensure Docker is running.
* Ensure you are in the directory location containing the marker_setup.sh script and directories like common, indexer, and textbook.
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
export TEXTBOOK_SUBDIR="academic_resources/econometrics/textbooks"
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

Note: If instead you get `ERROR: [0] Error during local connection to [stdin]: Error while connecting [4003: 'failed to connect to backend']. (Failed to connect to port 22)`, this is a TCP-level failure reaching the VM, not an auth/permissions problem -- and it doesn't necessarily mean anything is misconfigured. The most common cause is simply that the VM is still finishing boot: `RUNNING` status (which Step 2.1's check already confirms) only means the VM has started, not that sshd and the guest agent are ready to accept connections yet -- that can take another 1-2 minutes on a freshly created instance (Step 1.3) or one that was just started. Wait a minute or two and retry the `scp` command as-is first.

If it still fails after waiting, run the built-in diagnostic rather than re-guessing -- it checks network reachability, firewall/VPC rules, IAM permissions, and VM boot status in one pass and reports which one is actually the problem:

```bash
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --troubleshoot
```

Note: `--troubleshoot`'s "connectivity" check only proves packets *can* reach port 22 (a synthetic network-layer trace, not a real SSH handshake) -- it can come back completely clean (0 issues on every check) while the actual `ssh`/`scp` command still fails with the same `4003` error, if sshd itself isn't actually able to accept a new connection right now (as opposed to the VM merely still booting). If a real conversion run (Step 3.3) was in progress and disconnected mid-run (`Connection ... closed by remote host`, `Broken pipe`) and `--troubleshoot` comes back clean but SSH still won't connect, check the serial console for signs the VM has actually hung rather than just being slow:

```bash
gcloud compute instances get-serial-port-output $VM_INSTANCE_NAME --zone=$GCP_ZONE 2>/dev/null | tail -80
```

A healthy VM keeps producing routine systemd/cron log lines (cert refreshes, apt housekeeping, etc.) every several minutes indefinitely -- a long stretch (an hour or more) of total silence at the end, especially ending in something like a DHCP renewal failure, is a real sign the VM is wedged, not just slow. In that case, don't keep waiting and retrying: hard-reset it instead (this reboots the guest without touching the persistent disk, so `convert_textbook.py`'s chunk-level checkpoints from before the disconnect are preserved):

```bash
gcloud compute instances reset $VM_INSTANCE_NAME --zone=$GCP_ZONE
```

Give it a minute or two to boot, then retry SSH. See Step 3.1's note below for a re-provisioning issue this can trigger.

```bash
gcloud compute scp marker_setup.sh start_conversion.sh $VM_INSTANCE_NAME:~/ --zone=$GCP_ZONE --tunnel-through-iap
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
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="bash ~/marker_setup.sh"
```

(A single line, deliberately -- no heredoc. A heredoc block copy-pasted into an interactive terminal is fragile: a stray extra line pasted while it's still open gets silently absorbed into the heredoc body and sent to the *wrong* place -- confirmed live, when a second, unrelated command ended up inside one and ran on the VM instead of the docker container it was meant for. Single-line commands throughout this doc avoid that class of mistake entirely.)

Note: on a VM that's already been through a successful setup once (so `SETUP_VERSION` bumping to a newer script re-triggers a full re-provision, not a fresh install) -- especially right after a hard reset (`gcloud compute instances reset`, e.g. following a hung-VM recovery above) -- provisioning can fail on an apt step with `you have held broken packages` even though nothing about the packages themselves changed. This is different from a fresh-instance apt failure: a reset is a hard power-cycle, and if an Ubuntu background job (unattended-upgrades, `apt-daily`, etc.) was mid-transaction on any package at that exact moment, dpkg's own state for it can be left inconsistent. If this happens, SSH in and let dpkg reconcile itself before touching the failing package again:

```bash
sudo dpkg --configure -a
sudo apt-get install -f -y
```

then retry the setup script. `marker_setup.sh` itself already handles the specific, expected case of `nvidia-container-toolkit` and its dependents being self-held after install (see that script's own comments) -- this dpkg-reconciliation step is for the more general "a reset interrupted some other apt operation" case, which no script can fully anticipate in advance.

Debug step if torchaudio problems: Run the following to test if torchaudio is still causing problems in the current GCP VM image

```bash
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="python3 -c \"import torch; import transformers; print('torch:', torch.__version__, '| transformers:', transformers.__version__, '| CUDA:', torch.cuda.is_available())\""
```

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

If this run was interrupted partway through a multi-book batch (VM hang, disconnect, session timeout), you can just rerun this exact same command with the full original PDF list -- there's no need to figure out and manually restrict it to only the books that didn't finish. Before starting real work on each book, it checks whether a matching output (by the source PDF's own content hash, so a renamed or re-derived-title output still counts) already exists under `--output` -- see Step 3.4a below for checking what's there directly -- and if so, skips straight to reporting that existing path instead of reconverting it. Only genuinely-unfinished books in the list actually get (re)processed.

Filenames are shell-quoted with `printf %q` before being joined into one string, so any spaces, parentheses, or other shell-special characters in a filename survive being passed as arguments intact rather than being word-split apart.

**Runs inside a detached `tmux` session on the VM, launched via `start_conversion.sh` (already on the VM from Step 2.2), not attached to this SSH connection.** A multi-hour batch spent hours foreground-attached to a single SSH/IAP connection is exposed to that connection dropping for *any* reason the whole time it runs -- confirmed live, twice, on the same book's largest/slowest chunk (132 pages of heavy table content, simply the single longest stretch with no output, and so the most exposed window for an IAP session limit, a network blip, or anything else to land). The command below is a **single line, deliberately** -- no heredoc, no multi-line paste (the same reasoning as Step 3.1's note above; the tmux quoting this needs internally lives in `start_conversion.sh` itself, not in what you type here). It returns almost immediately after launching the job, and the job itself keeps running on the VM regardless of what happens to this connection afterward.

```bash
GCS_INPUT_URIS=""
for PDF_FILENAME in "${PDF_FILENAMES[@]}"; do
    printf -v QUOTED_URI '%q' "gs://$BUCKET_NAME/input_documents/$PDF_FILENAME"
    GCS_INPUT_URIS+="$QUOTED_URI "
done

gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="bash ~/start_conversion.sh 'gs://$BUCKET_NAME/processed_outputs' $GCS_INPUT_URIS"
```

**Preferred way to check on progress** (single line, its own short-lived connection, low-risk even if it drops -- use this, not interactive `tmux attach`, for routine checks):

```bash
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="tail -n 60 ~/convert_log.txt"
```

`tmux has-session -t convert` (run the same way, via `--command=`) exits non-zero once the job finishes or crashes -- combine with checking the tail of `~/convert_log.txt` for the "Batch summary" to see the actual outcome.

Only reach for interactive `tmux attach` if you actually want to watch it live. **This is two separate, sequential actions, not one block to paste at once** -- pasting both together sends the second line to whatever shell happens to be reading input at that moment (confirmed live: it silently ran in the local docker container instead of the VM, harmlessly, since the container doesn't have `tmux` installed -- but on the VM it would have piped stray input into whatever session was open there instead). Run the first line, **wait for the VM's shell prompt to actually appear**, then type the second line yourself:

```bash
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap
```
```bash
tmux attach -t convert
```

(Ctrl+B then D detaches again without stopping the job -- do not just close the terminal or Ctrl+C, which would kill it.)

A single book that turns out to be unusually slow or malformed no longer stalls the whole batch indefinitely: each Marker call is bounded by `--chunk-timeout` (default 1800s per chunk) and `--page-timeout` (default 240s per page fallback) before it's treated as hung and falls back automatically, and one book failing outright is logged and skipped rather than aborting the remaining books in the list. To override these defaults for a run, edit the `python3 -u -m textbook.convert_textbook ...` line directly in `start_conversion.sh` (on the VM, or locally before the next `scp`) to add e.g. `--chunk-timeout 2400 --page-timeout 300`.

LLM-assisted bibliographic metadata (Step 1.2) is on by default and needs no flags in the common case -- it auto-detects the GCP project from the VM's credentials. If you haven't done the Step 1.2 one-time setup yet, or want to skip it for a run, add `--no-llm-bib` to go straight to the regex fallback.

If you still get an ERROR related to scopes and authorization by GCP at this step, Step 2.1's check should have already caught and fixed it -- rerun Step 2.1 (e.g. if the VM was recreated since your last session and you skipped straight to Step 3).

### 3.4 Export the structured artifacts to the local host

Google Cloud VMs do not natively mount Google Drive. To retrieve the markdown and image artifacts, execute a recursive secure copy from the VM back to the local Docker workspace. The volume mount established in Step 0.1 will automatically synchronize these files to your local Windows filesystem.

This step is split into two parts on purpose -- **only the first is safe to run before the whole batch has finished.**

#### 3.4a: Download whatever's finished so far (safe any time, including mid-batch)

Each book's markdown/images are uploaded to the bucket as soon as *that book* finishes (see 3.3's script) -- not batched until the whole run completes. So this download command is safe to run at any point, including while other books in the same batch are still converting, to pull down already-finished books without waiting: it only ever copies whatever currently exists under `processed_outputs/`, and does nothing destructive.

```bash
# Ensure the local target directory structure exists prior to transfer.
# Uses the /academic-hub mount point directly (same convention as Step 3.2)
# rather than a "../academic-hub" relative path 
mkdir -p "/academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/"

# Recursively download whatever's currently in the bucket -- run again any
# time, including while other books are still converting, to pick up newly
# finished ones. Also useful right after recovering from an interrupted run
# (VM hang, disconnect, etc.) to check what already made it out before
# rerunning the batch command -- see Step 3.3's own note on this.
#
# The gs:// source is quoted deliberately: Step 0.2 enables `nullglob` for
# this same shell session (to detect zero PDFs found cleanly), which makes
# an unquoted "*" that matches no *local* file vanish silently instead of
# being passed through -- confirmed live: this exact line, unquoted, lost
# its entire source argument that way and failed with a confusing
# "Must have URL arguments" error. Quoting prevents bash from ever
# attempting to glob-expand it locally in the first place, regardless of
# `nullglob`'s state.
gcloud storage cp -r "gs://$BUCKET_NAME/processed_outputs/*" "/academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/"
```

To check what's actually finished before downloading (e.g. after recovering from an interruption, to see which books already succeeded), list folders instead of downloading:

```bash
gcloud storage ls gs://$BUCKET_NAME/processed_outputs/
```

#### 3.4b: Empty the bucket (only once the *entire batch* is confirmed complete and downloaded)

**Do not run this until every book in the batch has finished and you've confirmed 3.4a pulled everything down.** This deletes `input_documents/*` too -- the source PDFs any not-yet-converted book in the same batch still needs. Running it mid-batch (or before rerunning Step 3.3 to pick up an interrupted book) will break that book's next attempt with a "not found" GCS download error, since its source PDF is now gone.

```bash
gcloud storage rm -r "gs://$BUCKET_NAME/processed_outputs/*" "gs://$BUCKET_NAME/input_documents/*" --continue-on-error
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

Before that, each book also gets a free, local, no-LLM naming-reconciliation pass: it re-derives the book's `Author_Title_Year` folder name from what's already recorded in `_metadata.json`, plus a fresh filename-based guess -- fixing books that came out named e.g. `UnknownAuthor_SomeTitle_0000` if their source PDF's own filename actually had the missing author/year in it (a fallback tier `convert_textbook.py` didn't have yet when they were converted). If the re-derived name differs, the folder and its `.md`/`.rag.md`/`_metadata.json` files are renamed in place and the book's index card is repointed automatically -- no re-conversion, no extra API cost. `--dry-run` (below) previews this rename too, without touching disk.

### Step 5.1: One-time local setup

```powershell
cd academic-rag-model
pip install google-genai python-dotenv numpy
```

(`numpy` is a transitive dependency via `indexer/index_card.py`, which `describe_images.py` imports -- easy to miss since neither `describe_images.py` nor its own docstring mention it directly. Confirmed missing live in a docker-container run of this step.)

Requires a `GEMINI_API_KEY` in your `.env` (see `.env.example` -- a free key from aistudio.google.com/apikey works, or enable billing on that key for higher rate limits; either way this step's own API cost is negligible, well under $1 even for an image-heavy book).

### Step 5.2: Run it

Batches over every book folder found under `academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/` by default -- reuse the same `$TEXTBOOK_SUBDIR` you set in Step 0.2 for this run.

```powershell
$TEXTBOOK_SUBDIR="academic_resources/math-camp/textbooks"

python -m textbook.describe_images --textbook-subdir $TEXTBOOK_SUBDIR
```

* Add `--book "SomeBookFolderName"` to process just one book instead of the whole batch.
* Add `--dry-run` first to see which images would be processed (and which are already cached from a prior run) without spending any API calls.
* Each image's result is cached in `<BookName>_image_descriptions.json` inside that book's output folder as it's produced -- if the run is interrupted (network blip, rate limit, closed terminal), rerunning the same command picks up where it left off instead of re-billing already-processed images.

Note: this step depends on `run_config.json` being present in the book's output folder (written automatically by Step 3.3/3.4 as of this feature). Output converted before this feature shipped won't have it, and won't have the page-prefixed image links this script looks for either -- rerun Step 3 on those books first.
