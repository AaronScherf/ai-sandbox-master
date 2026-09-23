# Textbook Conversion Pipeline: GCP/Docker Environment Debugging

This subproject (`convert_textbook_instructions.md`, `marker_setup.sh`,
`textbook/convert_textbook.py`) predates the status-doc system, so this is
its first entry here — it covers where the pipeline already stood going
into this session, a real run's worth of environment/infra debugging that
surfaced four distinct issues (two needing real fixes, two pure operator
error), and then a real content bug the same run's actual output surfaced:
a book coming out named `UnknownAuthor_..._0000` despite its filename
having the missing info, fixed with a new bibliographic-extraction tier
plus a naming-reconciliation post-processing pass for already-converted
books.

## Where things already stood

The pipeline itself (Marker-based PDF → structured Markdown extraction, run
on a GPU VM via Docker + surya's vLLM backend) was already shipped and
working prior to this session — it went through a full colab-CLI → GCP VM
migration, chapter-aware chunking, image-description, and academic-hub
indexer integration over many prior commits (see `git log --follow --
textbook/convert_textbook.py` and `-- marker_setup.sh` for the full history
under the pipeline's earlier name, `marker-conversion`). This session was a
real end-to-end run of the *existing* pipeline against a fresh VM, not a
feature change — every issue below is environment/infra debugging, found by
actually running the documented steps in order.

## This session's real-run debugging, in order

### 1. Docker container instantiated from the wrong directory

**Symptom:** inside the running container, `/workspace` was completely
empty — `gcloud compute scp marker_setup.sh ...` failed with `stat local
"marker_setup.sh": No such file or directory`, and later, `PDF_FILENAMES`
came back empty (`No .pdf files found directly under /academic-hub/`).

**Root cause:** Step 0.1's `docker run`/`docker start` block was executed
from `ai-sandbox/` (one level above `academic-rag-model/`), not from inside
`academic-rag-model/` as the instructions specify. `-v ${PWD}:/workspace`
then mounted `ai-sandbox/` itself instead of `academic-rag-model/`, and
`-v ${PWD}\..\academic-hub:/academic-hub` resolved to a nonexistent
`ai-sandbox-master\academic-hub` instead of `ai-sandbox\academic-hub`. Since
`gcp-container` already existed, a plain `docker start -ai gcp-container`
would have kept reusing those wrong mounts rather than recomputing them.

**Fix:** no code/doc change — Step 0.1 already correctly says to run "from
PowerShell within the project directory." Removed the container
(`docker stop`/`docker rm`) and rebuilt it from `academic-rag-model/`.
Pure operator error, already covered by the existing instructions.

### 2. IAP tunnel: `4003: failed to connect to backend` / `Failed to connect to port 22`

**Symptom:** both `marker_setup.sh` scp lines failed with a TCP-level IAP
tunnel error, distinct from the 255/"VM stopped" case the instructions
already covered.

**Investigation:** VM confirmed `RUNNING`, `allow-iap-ssh` firewall rule
confirmed present and correctly scoped (network match, no restrictive
target tags), `networkInterfaces[0].network` confirmed `default`. Serial
console output (`gcloud compute instances get-serial-port-output`) showed a
completed boot with no NVIDIA-driver-install reboot loop. `gcloud compute
ssh ... --troubleshoot` (network connectivity, user permissions, VPC
settings, VM status, VM boot status) came back with 0 issues on every
check. Simply waiting ~1-2 minutes and retrying the same command succeeded.

**Root cause:** `RUNNING` status only means the VM has booted, not that
sshd/the guest agent are ready to accept connections — that gap can be a
minute or two on a freshly created or just-started instance, and none of
the IAP/firewall/permission checks catch it because nothing is actually
misconfigured.

**Fix:** documented in `convert_textbook_instructions.md` Step 2.2 — a new
note right after the existing 255-error note, explaining the likely
wait-and-retry fix and giving the `--troubleshoot` command as the fallback
diagnostic.

### 3. `marker_setup.sh`: `E: Unable to correct problems, you have held broken packages.`

**Symptom:** provisioning failed partway through, at the NVIDIA Container
Toolkit install step (`sudo apt-get install -y -qq
nvidia-container-toolkit=1.17.8-1`), on a freshly created VM (not
leftover state from a prior partial run — reproduced identically on a
second from-scratch instance).

**Investigation:** `apt-cache madison nvidia-container-toolkit` showed
`1.17.8-1` was still a valid, available version — ruling out the "pin aged
out of the repo" failure mode the script's own comment already warned
about. Rerunning the install manually without `-qq` surfaced the real
detail: `nvidia-container-toolkit : Depends: nvidia-container-toolkit-base
(= 1.17.8-1) but 1.19.1-1 is to be installed`. `apt-cache policy
nvidia-container-toolkit-base` confirmed `1.19.1-1` was already
**preinstalled** on the VM (`Installed:` line), not merely apt's default
candidate (`Candidate:` was actually the newer `1.20.0-1`).

**Root cause:** Step 1.3's VM-creation command uses `--image-family`, which
always resolves to whatever image Google/`ml-images` most recently
published under that family — not a pin to a specific image. The image
build that resolved on this run (`...-v20260909`, built the day before this
session) ships `nvidia-container-toolkit-base` preinstalled at `1.19.1-1`,
newer than the script's `1.17.8-1` pin. apt refuses to downgrade an
already-installed package to satisfy an unrelated package's exact-version
dependency, so the pinned top-level install fails outright — a second,
previously undocumented way this pin can break (distinct from the "ages out
of the repo" case the script already warned about).

**Fix, first pass:** `marker_setup.sh` — bumped the pin from `1.17.8-1` to
`1.19.1-1` (matching what was actually preinstalled at the time, not the
newest `1.20.0-1`), bumped `SETUP_VERSION` from `"2"` to `"3"`. Verified end
to end: rerunning the corrected script against the same VM completed
provisioning successfully — GPU visible in Docker (`nvidia-smi` inside a
test container), preinstalled torch 2.9.1+cu129/torchvision 0.24.1+cu129
verified with CUDA available, marker-pdf/google-genai installed, surya's
`vllm/vllm-openai:v0.20.1` pre-pulled, setup marker written.

**Fix, final:** a version bump only delays the same failure until the next
image build ships an even newer preinstalled `nvidia-container-toolkit-base`
— so removed the version pin entirely instead. `nvidia-container-toolkit`
is now installed unpinned; apt resolves it and `nvidia-container-toolkit-base`
together as a matched set every time, *upgrading* an already-preinstalled
base to match (which apt allows, unlike the downgrade the old pin used to
demand) rather than conflicting with it. This self-heals against whatever
image build Step 1.3 happens to resolve, instead of needing a manual pin
bump roughly every time Google publishes a new one (expected every few
weeks per `--image-family`'s floating nature, issue noted below).
`SETUP_VERSION` bumped again, `"3"` → `"4"`.

### 4. Operator confusion: running `gcloud compute scp`/env-var-dependent commands from inside the VM's own shell

**Symptom:** `ERROR: (gcloud.compute.scp) Source(s) must be remote when
destination is local. Got sources: [marker_setup.sh], destination: :~/`.

**Root cause:** the command was run from inside an active `gcloud compute
ssh` session (i.e. on the VM itself), where `$VM_INSTANCE_NAME` was unset
(it's only exported in the docker container's shell, from Step 0.2) and the
local `marker_setup.sh` file doesn't exist — the empty variable produced
the confusing bare `:~/` destination.

**Fix:** no code/doc change — procedural clarification only (`exit` back to
the docker container shell, identifiable by its short hex container-ID
prompt vs. the VM's `instance-<name>` prompt, before running any
`gcloud compute scp`/`ssh` command).

### 5. Real-run finding: a converted book named `UnknownAuthor_Econometrics_0000`

**Symptom:** the Hansen econometrics textbook, converted successfully by
Step 3.3, came out in an output folder named
`UnknownAuthor_Econometrics_0000` — despite the source PDF's own filename
being a clear `Hansen_Econometrics_2022.pdf`-style name.

**Root cause:** `convert_textbook.py`'s bibliographic-naming logic had three
tiers (PDF's own embedded metadata → LLM reading of the markdown title page
→ regex over the same markdown) and no fourth tier that ever looked at the
source filename for structured info — the filename was only ever used
wholesale, as the entire folder name, in the rare case *nothing* was found
at all. Here, the markdown-page tiers found *a* title (satisfying
`is_descriptive_bibliographic_info`'s title-OR-author check) but no
author/year, so the code fell straight to the `UnknownAuthor`/`0000`
placeholders instead of ever consulting the filename that actually had that
information.

**Fix:**
- Added `extract_bibliographic_info_from_filename()`: parses a 4-digit year
  plus camelCase/underscore/hyphen-separated words out of the filename
  (`HansenEconometrics2022.pdf` / `Hansen_Econometrics_2022.pdf` → author
  `Hansen`, title `Econometrics`, year `2022`), assuming the
  author-lastname-first-word convention. Wired in as a 4th tier in
  `process_one_pdf` that only fills whichever of title/author/year the
  tiers above left blank — never overrides a real match.
- Refactored the shared naming logic (`sanitize_filename`,
  `is_descriptive_bibliographic_info`, `merge_bibliographic_info`, the new
  filename tier, and a newly-extracted `derive_folder_name()`) out of
  `convert_textbook.py` into a new pure-Python `textbook/bib_info.py` module
  (no torch/marker/pypdf dependency, matching `chapter_index.py`) — so the
  exact same naming rule can be reused without pulling in GPU-pipeline
  dependencies.
- Added `reconcile_book_naming()` to `describe_images.py` (Step 5's existing
  local post-processing pass), run automatically on every book before image
  description: re-derives the ideal name from what's already recorded in
  `_metadata.json` plus a fresh filename guess, and renames the folder and
  its `.md`/`.rag.md`/`_metadata.json` files in place if different — fixing
  already-converted books like this one with no re-conversion or LLM cost.
  Repoints the book's index card (`path`, `rag_md_path`) via a new
  `update_card_paths()` in `indexer/index_card.py`.
- Test coverage: new `tests/test_bib_info.py`, additions to
  `tests/test_describe_images.py` (folder/file rename, index-card repoint,
  dry-run, already-ideal-name no-op, target-already-exists skip) and
  `tests/test_index_card.py`. Full suite (1260 tests) passing.
- `convert_textbook_instructions.md` Step 5 updated to describe the
  automatic naming-reconciliation pass.

**Not yet done:** rerunning Step 5 against the real Hansen book output to
confirm the rename actually fires end-to-end (the fix is unit-tested but
not yet re-verified against the real converted folder from this session).

### 6. Real-run finding: a mid-run VM hang, and a held-packages wall on recovery

**Symptom, part 1:** partway through an 801-page book (page subset 555-687),
the SSH session running Step 3.3's conversion dropped: `Connection ...
closed by remote host`, `Broken pipe`. `gcloud compute instances describe
... --format="value(status)"` immediately after said `RUNNING` (not
preempted/stopped), so the earlier hypothesis of a Spot preemption didn't
hold up as-is. A subsequent bare `gcloud compute ssh ... --command=...`
(just to check for an orphaned process) failed again with the same `4003`
error from Issue #2 above -- but this time `--troubleshoot` came back
completely clean (0 issues on every check, `REACHABLE` both directions).

**Investigation:** `--troubleshoot`'s network check is a synthetic
connectivity trace (Google's Connectivity Test API), not a real SSH
handshake -- "0 issues" only proves nothing is *misconfigured*, not that
sshd can currently accept a connection. Serial console output
(`get-serial-port-output`) showed the real signal: a "GCE Workload
Certificate refresh" job had been firing every ~10 minutes all session
(21:51, 22:01, ..., 22:53), then stopped entirely -- the very last line in
the whole log was `ens4: Could not set DHCPv4 address: Connection timed
out` at 23:30:48, with nothing at all logged for over an hour after that.
Total silence that long, with no more routine housekeeping jobs firing, is
a hang, not a slow VM.

**Fix, part 1:** `gcloud compute instances reset $VM_INSTANCE_NAME
--zone=$GCP_ZONE` -- a hard power-cycle that reboots the guest without
touching the persistent disk, preserving the book's chunk-level checkpoint
progress from before the hang (unlike delete-and-recreate).

**Symptom, part 2:** after the reset, re-syncing `marker_setup.sh` (now at
`SETUP_VERSION="4"`, the "unpinned toolkit" fix from earlier this session)
and rerunning it hit `E: Unable to correct problems, you have held broken
packages.` again -- at the *same* NVIDIA Container Toolkit step Issue #3
had already fixed. `df -h /` ruled out a full disk (39G free). The real apt
error this time was different in kind from Issue #3's:
`nvidia-container-toolkit : Depends: nvidia-container-toolkit-base (=
1.20.0-1) but 1.19.1-1 is to be installed` -- both packages were already
`Installed: 1.19.1-1` (from this VM's original successful provisioning
earlier in the session), yet apt refused to bring them in line with the
newer candidate. Manually naming all four related packages together
(`nvidia-container-toolkit`, `nvidia-container-toolkit-base`,
`libnvidia-container-tools`, `libnvidia-container1`) surfaced the real
cause: `The following held packages will be changed` -- these packages
mark *themselves* `apt-mark hold` once installed (a real, deliberate
self-protection against something later silently bumping the toolkit out
of sync with the matched NVIDIA driver), which a VM's first-ever
provisioning never encounters (nothing is installed/held yet) but any
later re-provisioning of an already-set-up VM does.

**Fix, part 2:** unblocked immediately with `sudo apt-get install -y
--allow-change-held-packages nvidia-container-toolkit
nvidia-container-toolkit-base libnvidia-container-tools
libnvidia-container1`, then made it permanent in `marker_setup.sh`: the
install line now names all four packages explicitly and passes
`--allow-change-held-packages` (naming only the top-level package, even
with the flag, still fails -- apt won't resolve a consistent upgrade for
held dependents unless they're named too). `SETUP_VERSION` bumped `"4"` →
`"5"`. Verified: the manual command succeeded, `marker_setup.sh` then
completed provisioning, and the conversion command was rerun and resumed
(checkpointing intact) rather than restarting from page 1.

**Doc updates:** `convert_textbook_instructions.md` -- Step 2.2 gained a
note distinguishing "`--troubleshoot` clean but SSH still fails" (check
serial console, then hard-reset) from the wait-and-retry case already
documented; Step 3.1 gained a note about the general
`dpkg --configure -a` / `apt-get install -f -y` recovery pattern for a
reset interrupting some other apt operation, distinct from the
now-self-documented toolkit-hold case in the script itself.

**Not yet done:** the conversion is running again as of this entry but
hasn't yet been confirmed to reach the end of this book (or complete the
rest of the batch) -- see "What's next".

### 7. Real-run finding: rerunning an interrupted batch redid already-finished books from scratch

**Symptom:** after Issue #6's recovery, rerunning Step 3.3's exact batch
command showed `Document 1/4` doing full fresh conversion work (real table
OCR calls, no "already completed" skip messages) on a 1081-page book --
different total pages than the 801-page book that had actually been
interrupted, meaning this book had most likely *already fully succeeded*
earlier in the session, before the process moved on to (and was later
interrupted on) a different, later book in the same 4-book batch.

**Root cause:** chunk-level checkpointing only helps *within* one book's
processing. Once a book fully finishes, `process_one_pdf` deletes its
`checkpoint_dir` as part of that success (nothing left to resume from is
correct once real output is safely uploaded) -- but there was no
*whole-book* check to begin with, so rerunning the same batch command
necessarily redoes every book in the list from page 1, including ones that
already succeeded and uploaded before the interruption.

**Fix, first pass (later found incomplete):** added a check keyed on
`indexer/index_card.py`'s index card (`find_card_by_file_id`) -- a card is
only ever written after a book's conversion succeeds, so its existence
seemed like the right "already done" signal. **This doesn't actually work
running on the GCP VM**: the on-VM indexing call inside `process_one_pdf`
needs `GEMINI_API_KEY` and a real local `academic-hub` checkout, and
*neither exists there* -- `.env`/`academic-hub/` are only ever mounted into
the local Docker container (Step 0.1), never copied to the VM. That
indexing call already silently fails there every time (caught, logged as a
`WARNING: source-indexer update failed...`, harmless to the conversion
itself) -- meaning no index card is ever written on the VM, and the
first-pass fix would never have actually triggered in the real Step 3.3
environment. Caught and corrected before the user hit it.

**Fix, corrected:** added `find_existing_output_by_file_id()` in
`convert_textbook.py` -- checks `--output` itself (GCS or local) directly
for an existing `*_metadata.json` whose `source_pdf_file_id` matches this
PDF's content hash. `raw_output` is the one thing that actually is durable
in the documented VM workflow (every book's GCS upload already happens
immediately per-book, confirmed while investigating this), so this needs no
indexer, no `GEMINI_API_KEY`, nothing beyond what Step 3.3 already has.
`process_one_pdf` now tries the (cheap, and correct wherever academic-hub
*is* available) index-card check first, then this GCS/local-output check,
before doing any real work. Test coverage: 7 new tests across
`TestFindExistingOutputByFileId` (GCS-mocked and local-filesystem cases) and
`TestProcessOnePdfSkipsAlreadyConvertedBook`. Full suite (1281 tests)
passing.

**Related, separate finding surfaced by the same investigation:** Step
3.4's documented "export" step actually does two things in one block --
downloading finished output (safe to run any time, including mid-batch,
since each book uploads as soon as it finishes) and emptying the bucket
(`gcloud storage rm -r .../processed_outputs/* .../input_documents/*` --
**not** safe mid-batch, since it deletes the source PDFs any not-yet-
converted book in the same batch still needs to download). Split into 3.4a
(anytime) and 3.4b (end-of-batch only, with an explicit warning) in
`convert_textbook_instructions.md`.

**Also caught while investigating Issue #7 (live run, real filenames):**
`extract_bibliographic_info_from_filename()`'s original heuristic assumed
an `AuthorTitleYear`-shaped filename -- backwards for this pipeline's real
input, which uses a library/ebook-repository convention (`"Title -- Author
-- Place, Year -- Publisher -- isbn..."`, confirmed against two real
filenames from a real run). A real Hayashi econometrics book was misnamed
with `"Econometrics"` (its actual title) recorded as the *author* as a
direct result. Fixed in `textbook/bib_info.py`: the `" -- "`-segment
convention is now tried first (segment 0 = title, segment 1 = author),
falling back to the old camelCase/underscore guess only when no such
segments exist; also fixed to take the *last* 4-digit year in the filename
rather than the first, since an author's birth year (e.g. Hansen's
"1962-") reliably precedes the real publication year in this convention.
4 new tests using the real Hansen/Hayashi filenames directly. This doesn't
retroactively fix already-uploaded folder names -- Step 5's
`reconcile_book_naming()` should correct them once run, no reconversion
needed (not yet verified against these two specific books -- see "What's
next").

### 8. Real-run finding: the same book's slowest chunk disconnected the SSH session twice, VM confirmed healthy the second time

**Symptom:** rerunning the batch (with Issue #7's skip fix not yet deployed
to the VM -- this rerun predates that) hit the *exact same* disconnect,
at the *exact same* chunk (`Processing page subset: 555 to 687 of 801`,
the same book from Issues #2/#6/#7), a second time. `--troubleshoot` and
serial console output both confirmed the VM itself was fully healthy this
time (routine "GCE Workload Certificate refresh" jobs still firing
normally right up to the end of the log, no gap) -- unlike Issue #6, this
wasn't a VM hang.

**Root cause (most likely, not exhaustively proven):** not something
specific/pathological about that page range's content -- it's simply the
largest chunk in this book (132 pages, heavy table content per earlier
table-processing-stats logs), so it's the single longest continuous
stretch with no output, making it the most exposed window for *any*
connection-ending event (an IAP tunnel session limit, a transient network
blip, etc.) to land in, regardless of root cause. The real underlying
issue: Step 3.3 ran the entire multi-hour batch in the foreground of one
SSH/IAP connection, so that connection's health was a single point of
failure for the whole run the entire time it took.

**Fix:** `marker_setup.sh` now installs `tmux` (`SETUP_VERSION` bumped
`"5"` → `"6"`, and added to `quick_verify_existing_setup()`'s dpkg check).
`convert_textbook_instructions.md` Step 3.3 now launches the conversion
inside a detached `tmux` session (piping output to `~/convert_log.txt`)
instead of running it attached to the SSH connection directly -- the
`gcloud compute ssh --command=...` call now returns almost immediately
after starting the job, and the job's lifetime is fully decoupled from
that connection afterward. Progress is checked via short-lived
`tail`/`tmux capture-pane`-style commands or by reattaching
(`tmux attach -t convert`), each of which is low-risk even if it drops,
unlike the old single long-lived foreground session.

**Not yet done:** this is a structural fix, not yet exercised on a real
multi-hour run to confirm a dropped connection genuinely no longer affects
the job.

## Known, not yet fixed / open items

- **`--image-family` (Step 1.3) is inherently a moving target.** It will
  keep resolving to whatever Google most recently publishes, so the same
  unchanged VM-creation command can hand back a different underlying image
  — and a different preinstalled package set — at any time, plausibly every
  few weeks. Issue #3's *specific* failure (the toolkit pin) is now fixed at
  the root by unpinning it, but the general risk remains for anything else
  in `marker_setup.sh` that might someday pin a version against something
  the DLVM image itself ships. Not switching to a fully pinned `--image`
  here, since that trades away driver/CUDA security updates for
  reproducibility, and unpinning the one package that actually broke was
  the more targeted fix — recorded as a known, accepted tradeoff rather
  than something further to solve preemptively.

## What's next

1. ~~Confirm the resumed conversion run reaches the end~~ -- **confirmed
   2026-09-11**: full 4-book batch completed, all `[OK]` in the batch
   summary. Content quality spot-checked and looks good (see Issue #9/#10's
   local inspection).
2. ~~Rerun Step 5 to confirm `reconcile_book_naming()` on real data~~ --
   **done 2026-09-11, see Issue #10**: it initially made Hansen/Hayashi/
   Stock's names *worse* (a real bug it surfaced, fixed same session), then
   correctly fixed all three once that fix landed.
3. If the VM hangs again under sustained load, it may be worth checking
   Cloud Monitoring's CPU/memory graphs for this instance during the hang
   window to see whether it's genuine resource exhaustion (vLLM + marker's
   CPU-side pipeline both running for hours on a 4-vCPU `g2-standard-4`) or
   something else -- not investigated this time since a hard reset resolved
   it well enough to keep moving.
4. ~~Issue #7's whole-book skip fix needs a real rerun to confirm~~ --
   **confirmed live 2026-09-11**: rerunning the 4-book batch correctly
   skipped both Hansen and Hayashi (`Already converted in a prior run...
   skipping re-conversion`) and only actually processed the genuinely-
   unfinished books.
5. ~~Issue #7's filename-parsing fix needs Step 5 run against real books~~
   -- superseded by item 2/Issue #10 above.
6. ~~Issue #8's `tmux` fix needs a real run to confirm~~ -- **partially
   confirmed 2026-09-11**: `marker_setup.sh` re-verified cleanly at
   `SETUP_VERSION=6` (tmux installed), and the batch launched via
   `start_conversion.sh` survived being checked on/reconnected to multiple
   times without dying. Not yet confirmed specifically against an actual
   mid-run SSH/IAP disconnect (none happened after this fix was deployed).
7. ~~Check Document 4 (Cameron)'s table-of-contents page~~ -- **confirmed
   2026-09-11**: rendered as a clean, correctly-aligned markdown table with
   all chapter titles and page numbers intact, despite the 34 `Table OCR
   failed` sub-blocks logged during conversion (same underlying
   TOC-misclassified-as-table phenomenon as `tables_ocr_failed` discussed
   earlier, just at a larger scale for this book's bigger/more complex
   TOC). Confirms Marker's fallback to plain text-layer extraction
   (`tables_pdftext`) produces excellent results for a born-digital PDF
   like this one -- those OCR-failure log lines were cosmetic, not
   reflected in the actual output quality.

### 9. Real-run finding: two orphaned duplicate folders from earlier, differently-named runs

**Symptom:** after downloading the finished 4-book batch, 6 folders showed
up locally (and in the bucket), not 4: `UnknownAuthor_ECONOMETRICS_0000`
and `UnknownAuthor_Contents_2007` alongside the correctly-named-for-now
`Econometrics_ECONOMETRICS_1962` and `Econometrics_Contents_2007`.
Confirmed via each folder's own `_metadata.json` (`source_pdf_file_id`,
`total_pages_processed`): the `UnknownAuthor_*` pair are genuine duplicates
of Hansen and Hayashi respectively (matching file_id, near-identical line
counts) -- output from an earlier run, *before this session's filename-
based naming tier existed at all*, left behind once a later run derived a
different (still-wrong, but different) name for the same two books.

**Root cause:** `delete_existing_gcs_output()` only ever replaces a prior
upload at the *exact* current folder name (documented in its own docstring
from when it was written) -- it has no way to find a prior version sitting
under a *different* name. Every naming-logic change this session (the
filename-fallback tier, then its dash-segment correction) was exactly the
kind of change that can shift a book's derived name between runs.

**Fix:** removed both orphaned folders (locally and from the bucket, once
confirmed as genuine duplicates by file_id). Hardened the underlying gap:
extracted a new `cleanup_stale_renamed_output()` in `convert_textbook.py`,
called right before every upload, which uses `find_existing_output_by_file_id`
(the same file_id-based lookup Issue #7's skip check already uses) to find
and remove any *differently-named* prior version of this exact book before
writing the new one -- closing the gap regardless of what the name changed
from/to. In normal operation this should rarely even fire, since Issue #7's
skip check already prevents reconverting a book with *any* existing output
in the first place; this is the defensive backstop for the case where
someone deletes a book's output specifically to force a reconversion
without also removing the old folder. 4 new tests in
`TestCleanupStaleRenamedOutput`. Full suite (1289 tests) passing.

### 10. Real-run finding: Step 5's naming reconciliation made two books *worse* -- "temp" as author

**Symptom:** running Step 5 for real, `Hansen_...`, `Hayashi_...`, and
`Stock_...`'s folders all got renamed to start with `temp_` (e.g.
`Econometrics_ECONOMETRICS_1962` → `temp_ECONOMETRICS_2022`) -- `reconcile_book_naming()`
had extracted the literal word `"temp"` as each book's author.

**Root cause:** `reconcile_book_naming()` reads `_metadata.json`'s
`source_pdf_path` field as if it were the real source filename -- but for a
book converted from a `gs://` input, `convert_textbook.py` actually records
the *local temp download's* path there (`temp_gcs_input_....pdf`), not the
real source filename. A real, pre-existing bug with no visible effect until
tonight's naming-reconciliation feature started actually reading that field
for filename parsing. `source_pdf_path` couldn't simply be repointed at the
real filename either -- it's also used, in its current (path-shaped) form,
by `derive_course()` and the index card's `rel_md_path`, both of which
expect a multi-segment path, not a bare filename.

**Fix:** `convert_textbook.py` now also records a new, unconditional
`source_pdf_filename` field (`os.path.basename(raw_input)`) alongside the
existing `source_pdf_path` -- purely additive, doesn't touch anything that
depends on `source_pdf_path`'s existing shape. `reconcile_book_naming()`
now prefers `source_pdf_filename`, falling back to `source_pdf_path` only
for books converted before this field existed (same behavior as before
this fix, for those older conversions only). 2 new tests confirming the
priority and the fallback.

**Related, second bug found while recovering from this:** one book's real
filename itself has a stray underscore already baked into it upstream
(`"...Fumio Hayashi_,Princeton _ Princeton University Press..."`), which
combined with `sanitize_filename()`'s own `"_"` separator to produce
`Hayashi__Contents_2007` (double underscore) instead of
`Hayashi_Contents_2007` -- `sanitize_filename()` never collapsed or trimmed
underscores already present in its input (underscore is a word character,
passes through its regexes untouched). Fixed: now collapses repeated
underscores and trims leading/trailing ones. 5 new tests in
`TestSanitizeFilename`.

**Recovery for the 4 already-converted books:** manually patched each
book's `_metadata.json` with its real filename (known from the original
conversion logs) and reran `reconcile_book_naming()` locally (pure logic,
no LLM call needed) via a one-off script -- no reconversion needed. Final
state: `Cameron_Microeconometrics_Methods_and_Applications_2013` (already
correct), `Hansen_ECONOMETRICS_2022`, `Hayashi_Contents_2007`,
`Stock_Question_Help_2019`. Author/year are now correct on all four;
`ECONOMETRICS`/`Contents`/`Question Help` as titles are pre-existing
markdown-heading-extraction quality issues (not fixable by the filename
tier, since those title fields were already non-blank) -- known, not
solved here, consistent with this whole naming system's "best-effort
convenience, not authoritative data" framing throughout. Full suite (1296
tests) passing.

8. ~~None of these 4 books have an index card yet~~ -- attempted via
   `python -m indexer.index_search rebuild`, which surfaced a **third**
   consumer of the same root cause behind Issue #10: `rebuild()`'s
   textbook branch (`indexer/index_search.py`) also trusted
   `source_pdf_path` as a real, readable local file (to `compute_file_id()`
   fresh from it) -- for these 4 books it's the same meaningless VM
   temp-download path, so all 4 got `skipped_no_source_pdf`. Fixed:
   `rebuild()` now falls back to looking for the real PDF by
   `source_pdf_filename` (Issue #10's field) in the directory this book's
   `processed_outputs/` folder lives under -- still present locally, since
   Step 3.2 uploads it to GCS without moving/deleting the local copy. 2 new
   tests. Full suite (1298 tests) passing. ~~Rerun `python -m
   indexer.index_search rebuild`~~ -- **confirmed 2026-09-11**: Cameron's
   `_metadata.json` was separately missing `source_pdf_filename` entirely
   (never renamed, so never went through the manual recovery patch the
   other 3 books got -- patched by hand once identified), then a final
   rerun reported `generated: 1, skipped_no_source_pdf: 0`. All 4 books now
   have index cards.

## 2026-09-22: pipeline-autonomy-policies effort -- three plans shipped (rebuild safety, duplicate auto-resolution, OOM/cost escalation ladder)

Design: `docs/superpowers/specs/2026-09-20-pipeline-autonomy-policies-design.md`,
`2026-09-20-textbook-conversion-skill-design.md`,
`2026-09-20-textbook-conversion-walkaway-execution-design.md`. Plans:
`docs/superpowers/plans/2026-09-20-rebuild-safety-fix.md`,
`2026-09-20-duplicate-auto-resolution.md`,
`2026-09-20-oom-cost-escalation-ladder.md`. All three executed via
`superpowers:subagent-driven-development` in their own isolated worktrees
(fresh implementer + task review per task, one whole-branch review per
plan) and merged into `main` the same day. 1438 tests passing on `main`
after all three merges.

The throughline across all three: this pipeline had been run manually,
session by session, with a human answering every duplicate prompt, cost
sanity check, and OOM recovery step in real time. These plans replace each
of those stop-and-ask points with either full automation or a
cheap-to-undo default plus after-the-fact review, aimed at genuine
walk-away execution of a multi-book batch.

### 1. rebuild-safety-fix

The cross-course duplicate-detection feature (shipped 2026-09-18, see
`docs/superpowers/specs/2026-09-17-cross-course-duplicate-textbook-detection-design.md`)
introduced **clone** index cards for duplicate books -- cards outside
`index_search.py`'s normal one-card-per-file-hash identity assumption. A
plain `index_search.py rebuild` (no `--prune` needed) could silently evict
the *canonical* course's own card from its own shard whenever a
byte-identical clone existed elsewhere, confirmed live. The only mitigation
at the time was a doc-only prohibition: never run `rebuild` over a course
holding a clone.

**Fix, not just a guard:** `duplicate_check.py`'s `copy_duplicate_artifacts`
now writes a `duplicate_of_file_id` marker into the clone's own
`_metadata.json`. `index_search.py`'s `rebuild()` textbook loop checks for
that marker and, when present, skips re-hashing the clone's PDF entirely --
instead deriving the same `compute_id_from_parts([duplicate_of_file_id,
clone_course])` id used at clone-creation time, so `--prune` no longer
evicts it and the canonical card is never touched. Covered by a real
end-to-end test (`TestRebuildWithRealDuplicateClone`), verified to actually
fail without the fix before it landed.

### 2. duplicate-auto-resolution

Even with rebuild made safe, the duplicate-check step itself still blocked
on a human for every Tier 2 (fuzzy title/author/year) match, which defeats
walk-away execution. The design tradeoff, as framed going in: missing a
real duplicate only costs re-running the conversion for that one book if
caught later, but converting a book that turns out to be a duplicate costs
real GPU-VM time -- so the fix should bias toward skipping and asking for
confirmation *after*, not blocking before.

**What shipped:** a `AUTO_SKIP_THRESHOLD = 0.85` combined-score cutoff.
Above it, a Tier 2 match auto-resolves the same way a Tier 1 (exact) match
already did -- artifacts copied, no reconversion -- but the new clone is
flagged `duplicate_pending_confirmation` and recorded to a durable queue at
`.index/duplicates/pending_confirmation.json`. Below 0.85 but above the
existing `SURFACE_THRESHOLD = 0.6`, behavior is unchanged (interactive
prompt, or left unresolved + reported under "Needs confirmation" in
`--non-interactive` mode). The queue is reviewed at any later, convenient
time:

```bash
python -m indexer.duplicate_check --review-pending
python -m indexer.duplicate_check --confirm-pending <file_id>   # it really was a duplicate
python -m indexer.duplicate_check --reject-pending <file_id>    # it wasn't -- removes the clone, book gets reconverted next run
```

A same-pair candidate already sitting in the pending queue is excluded from
`find_fuzzy_candidates` so it can't be matched again while awaiting review.
`record_pending_confirmation` is idempotent on `(incoming_file_id,
new_card_file_id)`, found and fixed during this plan's own final review.

### 3. oom-cost-escalation-ladder

Three changes to the batch-conversion workflow, all in
`convert_textbook_agent_instructions.md`/`convert_textbook.py`:

- **Ascending file-size batch ordering.** If an OOM is going to hit, it's
  going to hit the largest book in the batch -- sorting ascending means a
  resize triggered mid-batch affects as little of the remaining batch as
  possible, rather than being sprung on book 2 of 6 with four books still
  to go on the wrong machine size.
- **Cost sanity check now auto-proceeds**, escalating to a stop-and-ask
  only past >15 books or >2000MB total -- previously every run stopped for
  a manual go/no-go regardless of size.
- **A 3-rung OOM escalation ladder** replacing the old fully-manual
  recovery writeup: Rung 1 auto-resets the VM and relaunches on the same
  machine size; Rung 2 (second confirmed OOM on the same book) auto-resizes
  `g2-standard-4` -> `g2-standard-8` and relaunches; Rung 3 (a third,
  post-resize OOM) stops and asks a human. Every rung is gated on a
  `dmesg`-based positive OOM confirmation first, so a different failure
  mode (a torchaudio crash, an orphaned-container VRAM leak) doesn't get
  misdiagnosed as OOM and burn through the ladder for nothing.
- **Cost reconciliation**: actual VM wall-clock time and an approximate
  cost figure are reported at the end of every run, next to the pre-run
  estimate, closing the loop on whether that estimate was any good.

**Found and fixed during this plan's own final review, before merge:** the
ladder as first written would have silently destroyed the evidence it
depends on. `start_conversion.sh` truncates `~/convert_log.txt` and
`~/ram_sampling_log.txt` on every relaunch, and `gcloud compute instances
reset` clears the VM kernel's `dmesg` ring buffer on reboot -- so "relaunch
Step 3.3" (each rung's own remediation) was wiping the exact failed-attempt
data the escalation ladder needs to know which rung applies, and that
Step 3.4c wants to fold into `docs/status/vm_sizing_log.jsonl` as a real
sizing data point. Fixed with a durable `~/oom_ladder_state/<book>/`
directory on the VM's boot persistent disk (survives `instances reset` and
`stop`/`start`; only Step 4's VM deletion erases it) that snapshots both
logs and maintains a `rung_count` file *before* each relaunch, so the
active rung is read back as an authoritative number instead of inferred
from memory. Step 3.4c now downloads that directory before VM deletion and
gates its `--machine-type` argument off the downloaded `rung_count` instead
of relying on the operator remembering whether a resize happened.

### Process notes worth keeping

Two of the three plans' local `git merge` into `main` hit the same
shared-checkout hazard -- another concurrent session's own uncommitted
work on an unrelated file (never touched by either branch) blocking the
merge. Resolved both times with a path-scoped, uniquely-tagged
`git stash push -u -m "<tag>" -- <path>`, never a bare stash (see
`feedback_concurrent_session_git_hazard` in the assistant's memory).

## 2026-09-22 (same day, after the merges above): closed out the one deferred item -- stale duplicate-check/rebuild prose in both instruction files

Both `convert_textbook_instructions.md` and `convert_textbook_agent_instructions.md`
predated the two plans above and were never updated: one still said fuzzy
matches "always prompt," the other said non-interactive mode leaves all
Tier 2 matches unresolved with no mention of the new >=0.85 auto-skip band
or the `--review-pending` workflow; both still told the reader never to
run `index_search.py rebuild` over a course holding a clone, which was true
before 2026-09-22's fix and false after it. Flagged independently by two
reviewers during the plans' final reviews, explicitly out of scope for any
of the three plans as written (none touched this prose). Fixed directly,
docs only, no code change (commit `5b4f075`).
