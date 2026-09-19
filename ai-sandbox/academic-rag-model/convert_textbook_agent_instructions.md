# Textbook Conversion Pipeline — Agent Instructions

This is the agent-facing version of `convert_textbook_instructions.md`,
written for an autonomous coding agent (not a human at an interactive
terminal) to run. It assumes: local `gcloud` is installed and already
authenticated as the user (`gcloud auth list` shows an active account),
Docker is **not** used (the human doc's Step 0.1 gives an interactive
shell the agent can't drive usefully — run every command below directly
on the host instead), and every command is issued as its own single Bash
call — never combine two commands meant for different shells/hosts into
one call, and never paste a multi-line heredoc (see the Debugging
appendix, "Never combine or heredoc commands").

## When to stop and ask the user

Do not proceed past these points without an explicit answer:
1. **Subdirectory inclusion** (Step 0 below) — every run.
2. **Size/cost sanity check** before creating the VM (Step 1.3) — every run.
3. **Every Tier 2 (fuzzy) duplicate match** (Step 0.4) — never auto-skip one.
4. **VM deletion** at the end of a session (Step 4).
5. **Any Preflight gap** (Step -1) you can't fix yourself — report and stop;
   don't attempt to request quota, enable billing, or grant IAM roles
   beyond what Step -1 itself checks for.
6. **A second genuine system-RAM OOM-kill on the same book/chunk after one
   manual `gcloud compute instances reset` + relaunch already tried** (see
   the Debugging appendix's "chunk is silently degraded" entry) — this is
   a real signal the machine type is undersized for that book's content,
   and resizing (e.g. `g2-standard-4` → `g2-standard-8`, same L4 GPU, more
   system RAM) is a cost-changing decision, not something to do silently.
   Note this is about the *external* reset-and-relaunch, not
   `start_conversion.sh`'s own built-in watchdog retries -- those 5
   automatic attempts happen first, inside the VM, and don't by themselves
   fix an OOM-kill (see the appendix), so their exhaustion alone doesn't
   yet meet this bar. A single tight-but-recovering `free -h` reading, or
   a container/process dying for a reason *other* than a confirmed
   `dmesg`-visible OOM-kill, does not meet this bar either — let the
   watchdog's automatic retries handle those.

## Step -1: Preflight verification (read-only, run once per session)

Confirm the environment is actually ready before touching anything. All
of these are safe, read-only `gcloud`/`gcloud storage` calls.

```bash
# .env must exist one level up from this file, with these set:
grep -oE '^[A-Z_]+' ../.env
# Expect at least: PROJECT_ID, VM_INSTANCE_NAME, GCP_ZONE, BUCKET_NAME, GEMINI_API_KEY

set -a; source ../.env; set +a

# Authenticated as a real account?
gcloud auth list

# Vertex AI enabled + IAM role granted (Step 1.2's one-time setup)?
gcloud services list --enabled --project="$PROJECT_ID" | grep aiplatform
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
gcloud projects get-iam-policy "$PROJECT_ID" \
    --flatten="bindings[].members" --format="value(bindings.role,bindings.members)" \
    | grep "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" | grep aiplatform.user

# GPU quota (Step 1.3 needs PREEMPTIBLE_NVIDIA_L4_GPUS >= 1 in the target region)
gcloud compute regions describe "${GCP_ZONE%-*}" --project="$PROJECT_ID" \
    --format="value(quotas)" | tr ';' '\n' | grep PREEMPTIBLE_NVIDIA_L4_GPUS

# Bucket exists (one-time; skip Step 1.3's bucket-create if so)
gcloud storage ls --project="$PROJECT_ID" | grep "gs://$BUCKET_NAME/"
```

If any check fails (no billing, no quota, missing IAM role, `.env` var
missing), **stop and report the specific gap to the user** — these need a
human with Console/billing access, not more agent retries.

## Step 0: Declare the run and check for duplicates

### Step 0.1: Set `TEXTBOOK_SUBDIR` and list PDFs

```bash
set -a; source ../.env; set +a
export TEXTBOOK_SUBDIR="academic_resources/<course>/textbooks"   # set per run

shopt -s nullglob
PDF_FILENAMES=()
for pdf_path in "../academic-hub/$TEXTBOOK_SUBDIR"/*.pdf; do
    PDF_FILENAMES+=("$(basename "$pdf_path")")
done
export PDF_FILENAMES
printf '  %s\n' "${PDF_FILENAMES[@]}"
```

This only looks at direct children of `TEXTBOOK_SUBDIR`, matching the
existing convention (re-running against the same folder won't re-ingest
`processed_outputs/`).

**Ask the user now** whether any nested subfolder under `TEXTBOOK_SUBDIR`
(e.g. a `Bonus/` folder of supplementary readings) should also be
converted. If yes: **run it as its own separate later batch** — a
different `TEXTBOOK_SUBDIR` value (or a manual list), its own Step 1.3
VM lifecycle, run only after the main batch's VM has been torn down.
Never mix a nested subfolder's PDFs into the same spot-VM session as the
main textbooks: a spot instance can be preempted mid-batch, and keeping
batches small and separately-scoped means a preemption or a bad book in
one batch never jeopardizes the other.

### Step 0.2: Verify SDK

```bash
gcloud version
```

### Step 0.3: Run the duplicate check (new)

This agent's shell has no interactive stdin, so always pass
`--non-interactive` — the default (no flag) mode blocks on an `input()`
y/n prompt per Tier 2 candidate, which will hang forever here.

```bash
python -m indexer.duplicate_check --textbook-subdir "$TEXTBOOK_SUBDIR" --non-interactive \
    --emit-to-convert /tmp/to_convert.txt
```

`--emit-to-convert` writes the final "to convert" filenames (one per
line) to that path alongside the normal stdout report — that file, not a
re-glob of the folder, is what `PDF_FILENAMES` gets rebuilt from below.

This is local, offline, and free (no GPU, no VM, no LLM calls) — see
`docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md`.
It always prints a "To convert" and a "Skipped -- duplicate found,
artifacts copied" section, plus — only when at least one Tier 2 match is
still undecided — a third "Needs confirmation -- rerun with --resolve"
section. A previously-dismissed pair is excluded from consideration
entirely and never printed anywhere.

- **Tier 1 (exact byte match)** is resolved automatically — nothing to ask.
- **Tier 2 (fuzzy match)** candidates in the "Needs confirmation" section
  print the new PDF's own `incoming file_id`, plus each matching
  candidate's course, title, file_id, and similarity score. In
  `--non-interactive` mode these are left unresolved (their PDFs stay in
  the "to convert" list — the safe direction per the spec's
  error-handling rule). Relay every candidate to the user in chat and get
  an explicit yes/no, then re-run with one `--resolve` per decision to
  apply them without blocking. **`--resolve` takes the new PDF's own
  `incoming file_id` from the report -- not the matched candidate's
  `file_id`:**

  ```bash
  python -m indexer.duplicate_check --textbook-subdir "$TEXTBOOK_SUBDIR" --non-interactive \
      --emit-to-convert /tmp/to_convert.txt \
      --resolve <incoming_file_id_a>=yes --resolve <incoming_file_id_c>=no
  ```

  `yes` performs the skip+copy against that book's best-scoring
  candidate; `no` records a permanent dismissal of that (incoming,
  candidate) pair (never surfaced again). Always pass
  `--emit-to-convert` on this re-run too — it is the run that applies
  the decisions, so its emitted file is the one that reflects them.

Then rebuild `PDF_FILENAMES` from the emitted file:

```bash
mapfile -t PDF_FILENAMES < /tmp/to_convert.txt
export PDF_FILENAMES
printf '  %s\n' "${PDF_FILENAMES[@]}"
```

**Read the emitted file; do not re-glob `TEXTBOOK_SUBDIR` here.** A
confirmed duplicate's artifacts are copied into this course, but its
*source PDF deliberately stays in `TEXTBOOK_SUBDIR`* — so a re-glob
returns the identical list as before the check, and the book that was
just resolved would be uploaded and reconverted anyway, defeating the
whole step. The emitted file is the only list that reflects the check's
decisions.

If `PDF_FILENAMES` is now empty (the emitted file is empty), every book
in this folder was already covered by an existing conversion — report
that to the user and stop; there is nothing left to convert and no VM is
needed this run.

One caveat to carry forward, and it's stronger than "review before
pruning": books resolved as duplicates get **clone** index cards, marked
with a `duplicate_of_file_id` field, which sit outside `index_search.py`'s
normal one-card-per-file reconciliation. **Do not run
`index_search.py rebuild` -- with or without `--prune` -- over a course
that has received clones** until this is fixed upstream: a plain
`rebuild` can silently evict the *canonical* course's own card from its
own shard (confirmed live for byte-identical duplicates), which is worse
than anything `--prune` alone would do. See the spec's "Known
limitations" section for the full mechanism before running `rebuild`
anywhere near an affected course.

## Step 1: One-time-per-project setup (idempotent — safe to always run)

### 1.1 Vertex AI (only if Step -1 found it missing)

```bash
gcloud services enable aiplatform.googleapis.com --project="$PROJECT_ID"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/aiplatform.user"
```

### 1.2 Create the bucket (only if Step -1 found it missing)

```bash
gcloud storage buckets create "gs://$BUCKET_NAME" --project="$PROJECT_ID" --location="${GCP_ZONE%-*}"
```

### 1.3 Size/cost sanity check, then create the VM

Before creating the VM, compute and report to the user:

```bash
TOTAL_MB=0
for f in "${PDF_FILENAMES[@]}"; do
    SZ=$(stat -c%s "../academic-hub/$TEXTBOOK_SUBDIR/$f" 2>/dev/null || stat -f%z "../academic-hub/$TEXTBOOK_SUBDIR/$f")
    TOTAL_MB=$((TOTAL_MB + SZ / 1048576))
done
echo "${#PDF_FILENAMES[@]} PDF(s), ~${TOTAL_MB} MB total, to convert:"
printf '  %s\n' "${PDF_FILENAMES[@]}"
```

**Ask the user to confirm before proceeding** — state the PDF count and
total size, that this launches a billed `g2-standard-4` + L4 Spot VM for
a run that (based on prior real runs) takes on the order of hours for a
multi-hundred-page batch, and that a Spot VM can be preempted mid-run
(recoverable, but costs wall-clock). Only create the VM after a yes.

```bash
gcloud compute instances create "$VM_INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --zone="$GCP_ZONE" \
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

If a later `--tunnel-through-iap` step fails with a connection/permission
error (not an auth error), the project's firewall may be missing the IAP
rule:

```bash
gcloud compute firewall-rules create allow-iap-ssh \
    --project="$PROJECT_ID" --network=default --direction=INGRESS \
    --action=ALLOW --rules=tcp:22 --source-ranges=35.235.240.0/20
```

## Step 2: Prepare the VM

### 2.1 Scope check (always run — cheap, no-op if already correct)

```bash
CURRENT_SCOPES=$(gcloud compute instances describe "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --format="value(serviceAccounts[0].scopes)")
if [[ "$CURRENT_SCOPES" == *"cloud-platform"* ]]; then
    echo "VM already has cloud-platform scope."
else
    VM_STATUS=$(gcloud compute instances describe "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --format="value(status)")
    [ "$VM_STATUS" != "TERMINATED" ] && gcloud compute instances stop "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    gcloud compute instances set-service-account "$VM_INSTANCE_NAME" \
        --zone="$GCP_ZONE" --service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --scopes=cloud-platform
    gcloud compute instances start "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
fi
```

### 2.2 Copy scripts to the VM

**On Windows, `~` does not reliably expand in `gcloud compute scp` destinations** — this environment's gcloud uses PuTTY's `pscp` under the hood, which (unlike OpenSSH's `scp`) does not expand `~` server-side; confirmed live: `gcloud compute scp foo.sh VM:~/` fails with `pscp: remote filespec ~/: not a directory`, and the same command with `~/somedir/` fails with `pscp: remote filespec ~/somedir/: not a directory` if `somedir` doesn't already exist (a fresh VM's `~/academic-rag-model/` doesn't exist until you create it). So: capture the real remote home directory once via a plain SSH command, create the target directory, and use the captured absolute path for every scp from here on instead of `~`.

```bash
REMOTE_HOME=$(gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="echo \$HOME")
gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="mkdir -p $REMOTE_HOME/academic-rag-model"
```

```bash
gcloud compute scp marker_setup.sh start_conversion.sh "$VM_INSTANCE_NAME":"$REMOTE_HOME/" --zone="$GCP_ZONE" --tunnel-through-iap --quiet
gcloud compute scp --recurse common indexer textbook "$VM_INSTANCE_NAME":"$REMOTE_HOME/academic-rag-model/" --zone="$GCP_ZONE" --tunnel-through-iap --quiet
```

**Also copy `GEMINI_API_KEY` to the VM** — without it, `convert_textbook.py`'s source-indexer hook (the step that writes searchable `.index/` cards as a side effect of conversion) fails on every single book with `ERROR: GEMINI_API_KEY not set` and silently degrades to "conversion succeeded, indexing skipped" (confirmed live: this happened for all 6 books in one real run before this step existed, requiring a manual `index_search.py rebuild` afterward to catch up). `gemini_utils.py` resolves `.env` at exactly three parents above itself, so on the VM that's `$REMOTE_HOME/.env` (since `common/gemini_utils.py` lives under `$REMOTE_HOME/academic-rag-model/`). Copy only `GEMINI_API_KEY` — never the whole local `.env` — to avoid putting unrelated secrets (`PAID_GEMINI_KEY`, `CORE_API_KEY`, etc.) on an ephemeral cloud VM that doesn't need them:

```bash
grep '^GEMINI_API_KEY=' ../.env > /tmp/vm_env_minimal
gcloud compute scp /tmp/vm_env_minimal "$VM_INSTANCE_NAME":"$REMOTE_HOME/.env" --zone="$GCP_ZONE" --tunnel-through-iap --quiet
rm /tmp/vm_env_minimal
```

`--quiet` suppresses the SSH-key-passphrase prompt (empty passphrase),
since this shell is not interactive. If this is the very first SSH to a
brand-new VM and it fails with a `255` error or a `4003`/port-22
connection error, see the Debugging appendix — it is very likely just
the VM still finishing boot (wait 1-2 minutes, retry as-is first).

## Step 3: Run the conversion

### 3.1 Provision the VM

```bash
gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="bash ~/marker_setup.sh"
```

Safe to always run — it self-skips if already provisioned. If this fails
on an apt step with "you have held broken packages" right after a
`gcloud compute instances reset` (see Debugging), reconcile dpkg first:

```bash
gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="sudo dpkg --configure -a && sudo apt-get install -f -y"
```

then retry the provisioning command.

### 3.2 Upload input PDFs

```bash
for PDF_FILENAME in "${PDF_FILENAMES[@]}"; do
    gcloud storage cp "../academic-hub/$TEXTBOOK_SUBDIR/$PDF_FILENAME" "gs://$BUCKET_NAME/input_documents/$PDF_FILENAME"
done
```

### 3.3 Launch the conversion (detached, survives disconnects)

```bash
GCS_INPUT_URIS=""
for PDF_FILENAME in "${PDF_FILENAMES[@]}"; do
    printf -v QUOTED_URI '%q' "gs://$BUCKET_NAME/input_documents/$PDF_FILENAME"
    GCS_INPUT_URIS+="$QUOTED_URI "
done
gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="bash ~/start_conversion.sh 'gs://$BUCKET_NAME/processed_outputs' $GCS_INPUT_URIS"
```

This returns almost immediately; the job keeps running on the VM in a
detached `tmux` session regardless of what happens to this connection.

**Check progress this way only** (a short-lived connection, low risk if
it drops) — do not attempt an interactive `tmux attach`; this agent's
shell is not interactive and can't usefully hold one open:

```bash
gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="tail -n 60 ~/convert_log.txt"
```

```bash
gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="tmux has-session -t convert"
```
(non-zero exit = the job finished, or a built-in watchdog inside the
session already retried the conversion up to 5 times and gave up — check
the log's "Batch summary" line, or a `FATAL` line, for the real outcome.
A single dead inference server mid-batch is no longer a reason for this
session to have ended -- see the Debugging appendix.)

For a long-running batch, poll every several minutes rather than tightly
looping — see the Debugging appendix for what a hung VM looks like if a
connection drops mid-run and doesn't come back.

### 3.4a Download finished books (safe any time, including mid-batch)

```bash
mkdir -p "../academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/"
gcloud storage cp -r "gs://$BUCKET_NAME/processed_outputs/*" "../academic-hub/$TEXTBOOK_SUBDIR/processed_outputs/"
```

The `gs://...` source must stay quoted (see Debugging — `nullglob`
silently drops an unquoted `*` here).

To see what's finished without downloading:

```bash
gcloud storage ls "gs://$BUCKET_NAME/processed_outputs/"
```

### 3.4b Empty the bucket — only after the whole batch is confirmed complete and downloaded

```bash
gcloud storage rm -r "gs://$BUCKET_NAME/processed_outputs/*" "gs://$BUCKET_NAME/input_documents/*" --continue-on-error
```

Do not run this until every book in the batch is done and 3.4a has been
re-run with nothing new appearing — it deletes the source PDFs any
not-yet-finished book still needs.

## Step 4: Terminate the VM

Ask the user which they want (default recommendation: delete — a
Persistent Disk bills for its full size the entire time it exists,
running or not, and everything it holds is reproducible from Step 3.1 or
already safe in GCS/local per Steps 3.2-3.4):

- **Stop** (only if another run is expected later the same day):
  ```bash
  gcloud compute instances stop "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
  ```
- **Delete** (default) — confirm explicitly with the user first (this is
  irreversible), then run directly — there is no interactive
  confirmation prompt here since this shell isn't interactive, so the
  chat confirmation *is* the safeguard:
  ```bash
  gcloud compute instances delete "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --quiet
  ```

## Step 5: Describe images locally (no GPU/VM needed — run after Step 4)

```bash
pip install google-genai python-dotenv numpy
python -m textbook.describe_images --textbook-subdir "$TEXTBOOK_SUBDIR"
```

Requires `GEMINI_API_KEY` in `.env` (Step -1 already confirmed it's
set). Add `--dry-run` first to preview without spending API calls, or
`--book "SomeBookFolderName"` to process just one book. Each image's
result is cached as it's produced, so an interrupted run resumes cleanly
on re-run.

## Debugging appendix

- **Never combine or heredoc commands.** Issue exactly one command per
  Bash tool call. A command meant for the VM and a command meant for the
  local/container shell must never be sent together — confirmed live, a
  second command pasted alongside an open heredoc silently ran on the
  wrong host.
- **SSH port-22 `4003` / connection refused right after VM creation or
  start:** the VM's `RUNNING` status only means it started booting, not
  that sshd is ready — wait 1-2 minutes and retry the exact same command
  first. If it still fails:
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --troubleshoot
  ```
  A clean troubleshoot result only proves network reachability, not that
  sshd itself will accept a connection right now. If a run was mid-batch
  and disconnected, check whether the VM actually hung:
  ```bash
  gcloud compute instances get-serial-port-output "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" | tail -80
  ```
  An hour or more of total silence (especially ending in a DHCP renewal
  failure) means it's wedged — hard-reset it (preserves the disk and any
  chunk-level checkpoints already written):
  ```bash
  gcloud compute instances reset "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
  ```
  Give it a minute or two, then retry SSH — and see the dpkg note under
  Step 3.1 if provisioning then fails on a broken-packages apt error.
- **Torchaudio/CUDA sanity check:**
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="python3 -c \"import torch; import transformers; print('torch:', torch.__version__, '| transformers:', transformers.__version__, '| CUDA:', torch.cuda.is_available())\""
  ```
- **Scope-related upload failure at Step 3.3:** Step 2.1 should already
  have caught this — rerun Step 2.1 (e.g. if the VM was recreated since
  the last session and Step 2.1 was skipped).
- **A single malformed/slow book never stalls the whole batch:** each
  chunk is bounded by `--chunk-timeout` (default 1800s) and
  `--page-timeout` (default 240s) before falling back automatically, and
  one book failing is logged and skipped, not fatal to the rest.
- **A chunk is silently degraded to bare PyPDF text (missing
  tables/formulas/layout) because the local inference server died mid-run:**
  `start_conversion.sh` now has a built-in auto-restart watchdog
  (`run_conversion_with_retries`, inside the "convert" tmux session
  itself) that handles most of this class automatically -- **no action is
  normally needed.** It also stops the worst version of this failure at
  the source: `convert_textbook.py` now measures what fraction of a
  chunk's pages fell back to raw PyPDF extraction, and if more than half
  did (`chunk_is_degraded`, `textbook/convert_textbook.py`), it prints a
  `FATAL:` line and exits non-zero **instead of** writing that chunk's
  `.done` marker -- a chunk is never silently checkpointed as done once
  the inference server was effectively dead for it. The watchdog sees that
  nonzero exit, cleans up stale inference-server state, and relaunches --
  already-completed chunks skip via their `.done` markers, so a retry only
  redoes the chunk that was actually in flight. It does this up to 5 times
  (15s apart) before giving up and letting the run end.
  - **You only need to look at this appendix entry when:** `grep -c
    'FATAL' ~/convert_log.txt` is nonzero (retries were exhausted -- a
    genuinely broken environment, not a transient death) or a health check
    finds `sudo docker ps` / `pgrep -fa surya.ocr_error.server` empty
    *while the "convert" tmux session is also gone* (the watchdog itself
    died, not just one attempt inside it).
  - `grep -c 'VLM bypassed\|Layout inference failed' ~/convert_log.txt` is
    still worth checking on an otherwise-healthy-looking run: a HANDFUL of
    isolated lines across a whole book is normal (a genuinely malformed
    individual page that recovered on its own, below the 50% threshold
    above); it's only actionable if it's a tight cluster that the FATAL
    check above didn't already catch.
  - **This is a real, repeatedly-confirmed failure class, not
    hypothetical** -- it happened four times converting one real book,
    for four different underlying reasons (a torchaudio ABI crash, GPU
    VRAM exhausted by leftover containers, a system-RAM OOM-kill, and once
    with no root cause found at all beyond a generic `docker events`
    "TaskDelete" entry). The watchdog's blind cleanup-and-relaunch fixes
    the first, second, and fourth of these outright. It does **not** fix
    the third (system-RAM OOM-kill) -- see below. Marker-pdf/surya use two
    separate local inference processes, and either one dying independently
    produces this symptom:
  - `sudo docker ps` -- should show exactly one `surya-vllm-*` container.
    Empty, or more than one, both indicate a problem: empty means it died;
    more than one means an earlier kill left an orphan that's now
    competing for the same GPU memory as a fresh one (confirmed live:
    two orphaned containers together held 22.4GB of the L4's 23GB total,
    leaving no headroom for real work).
  - `pgrep -fa surya.ocr_error.server` -- should show exactly one process.
    This one is NOT a Docker container -- it's a plain
    `python3 -m surya.ocr_error.server` process that gets reparented to
    init (PPID 1) when the "convert" tmux session is killed, and survives
    independently holding its own slice of GPU memory (~500MB observed).
    `sudo docker ps` alone will not show this leak.
  - `dmesg 2>/dev/null | grep -i 'killed process'` -- a hit here means the
    Linux kernel's own OOM-killer killed the inference process because
    system RAM (not GPU VRAM) ran out. `g2-standard-4` has only ~15GB
    system RAM, which can run genuinely tight on a dense, image/table-heavy
    book. **This is the one case the in-VM watchdog cannot fully fix on
    its own:** its cleanup-and-relaunch only stops/restarts processes
    *inside* the already-memory-pressured VM, which doesn't clear whatever
    caused the OS itself to run out of RAM -- confirmed live, relaunching
    without a full `gcloud compute instances reset` reproduced the exact
    same OOM-kill again within minutes. A `gcloud compute instances reset`
    is issued from *outside* the VM (this is why the watchdog, which only
    runs inside it, can't do this step itself). Symptom to watch for: 5
    consecutive `FATAL` lines a few seconds apart in `~/convert_log.txt`
    (the watchdog burning through all its retries uselessly) each preceded
    by a fresh `dmesg` OOM-kill -- that pattern means stop watching the log
    and go straight to the recovery below. If it recurs a second time on
    the same book after one reset, see "When to stop and ask the user"
    point 6 above rather than resetting a third time.
  - Sometimes there is no diagnosable cause at all: `dmesg` and
    `sudo journalctl -u docker --since '30 min ago'` come back clean
    except a bare `"ignoring event" ... type="*events.TaskDelete"` line
    naming the dead container's ID. Don't spend long chasing this one --
    the watchdog's blind cleanup-and-relaunch fixes it the same way
    regardless of whether a cause is found.

  **Manual recovery -- needed only for a `dmesg`-confirmed OOM-kill, or
  when `~/convert_log.txt` shows the watchdog exhausted all 5 retries and
  the "convert" tmux session has ended:**
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="tmux kill-session -t autostop 2>/dev/null; tmux kill-session -t convert 2>/dev/null; echo done"
  ```
  ```bash
  gcloud compute instances reset "$VM_INSTANCE_NAME" --zone="$GCP_ZONE"
  ```
  (Skip the reset if the trigger was retry exhaustion with no `dmesg`
  OOM-kill involved -- that's a different, non-memory root cause, and a
  reset won't fix it; investigate the `FATAL` lines' surrounding log
  context instead.) Wait ~1-2 minutes after a reset, then:
  ```bash
  gcloud compute ssh "$VM_INSTANCE_NAME" --zone="$GCP_ZONE" --tunnel-through-iap --command="sudo docker ps -aq --filter 'name=surya-vllm-' | xargs -r sudo docker rm -f; pgrep -f 'surya\.ocr_error\.server' | xargs -r sudo kill -9; nvidia-smi --query-gpu=memory.used --format=csv,noheader"
  ```
  Confirm that last command reads low (a few hundred MB is fine; multi-GB
  means something is still holding memory) -- this is a belt-and-suspenders
  check; `start_conversion.sh`'s watchdog runs the same cleanup itself on
  every attempt, including the first one after this manual step. Then
  relaunch Step 3.3 with the same book list (already-finished books skip
  via `convert_textbook.py`'s own whole-book check; already-good chunks
  within an in-progress book skip via the per-chunk checkpoint -- and any
  chunk that was mid-flight during the kill was never marked `.done` in
  the first place, since `chunk_is_degraded` exits before that write) and
  re-arm the autostop watcher as usual.
  - `chunk_is_degraded` only catches a chunk where a clear majority
    (>50%) of pages fell back to raw PyPDF text -- a *milder* degradation
    (say, 2 of 6 pages) still gets checkpointed as done. This is
    deliberate (a lone hard page recovering via the normal per-page
    fallback is expected, not a failure), but it means the file-size
    sanity check from before this fix -- comparing
    `~/academic-rag-model/marker_checkpoints/<book>/chunks/*.md` sizes
    against neighboring same-page-count chunks -- is still worth a look if
    a book's final output looks thin in specific spots, even when nothing
    in this appendix's automatic checks fired.
