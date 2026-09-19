#!/usr/bin/env bash
# start_conversion.sh
# Launches convert_textbook.py inside a detached tmux session on this VM, so
# the job survives a dropped SSH/IAP connection instead of dying with it --
# see Step 3.3 in convert_textbook_instructions.md. Runs on the VM itself
# (scp'd there alongside marker_setup.sh), invoked with a single simple
# `gcloud compute ssh ... --command="bash ~/start_conversion.sh ..."` line
# from the docker container -- deliberately no heredoc, no multi-line paste
# required, after a real mid-paste mixup (a second, unrelated command line
# ended up inside a heredoc body and got executed on the VM instead of the
# docker container it was meant for).
#
# Usage: bash ~/start_conversion.sh <output-gcs-path> <input-gcs-uri> [<input-gcs-uri> ...]
set -e

OUTPUT_PATH="$1"
shift

if [ -z "$OUTPUT_PATH" ] || [ "$#" -eq 0 ]; then
    echo "Usage: bash ~/start_conversion.sh <output-gcs-path> <input-gcs-uri> [<input-gcs-uri> ...]" >&2
    exit 1
fi

# Re-quote everything for safe embedding in the tmux pane's own command
# string below (a second layer of shell parsing) -- inputs already survived
# one round of %q-quoting to get here as clean positional args, but
# embedding them via a plain $*/"$@" into another string would un-escape
# them again (e.g. a filename with a space would get word-split apart by
# the pane's shell).
REQUOTED_INPUTS=$(printf '%q ' "$@")
REQUOTED_OUTPUT=$(printf '%q' "$OUTPUT_PATH")

# Cleans up leftover inference-server state from a prior crashed/killed run.
# A killed/crashed/reset "convert" session leaves its vLLM inference server
# container running -- Docker containers aren't tied to the tmux session
# that started them, so `tmux kill-session -t convert` (or a VM reset)
# never stops it. The lock purge below only clears a lock FILE, not the
# actual container. Confirmed live: after two kill/relaunch cycles in one
# session (excluding then re-including a book, then a hard reset), TWO
# separate `surya-vllm-*` containers were found still running, each holding
# its own full copy of the model's GPU memory (16.2GB + 6.2GB out of the
# L4's 23GB total) -- the combined footprint left no headroom for real
# page processing, and every page from that point on silently failed over
# to the bare PyPDF fallback with a CUDA out-of-memory error, not a fatal
# one.
#
# The vLLM Docker container isn't the only leftover risk -- surya also
# spawns its own standalone `python3 -m surya.ocr_error.server` process
# directly on the host (not inside Docker) the first time a chunk needs
# OCR-error detection, and reuses it for the rest of the run rather than
# starting a fresh one per chunk. Confirmed live: killing the "convert"
# tmux session does NOT kill this process -- it gets reparented to init
# (PPID 1) and keeps running orphaned, still holding its own slice of GPU
# memory (514MB observed), on top of whatever the vLLM container(s) hold.
# Same accumulation risk as the vLLM containers, different mechanism.
#
# Exported (not just defined) so the retry loop below can call it from
# inside the fresh bash process tmux spawns for the "convert" session.
cleanup_stale_inference_state() {
    sudo rm -f /root/.cache/datalab/surya/vllm_server.lock

    local stale_containers
    stale_containers=$(sudo docker ps -aq --filter "name=surya-vllm-")
    if [ -n "$stale_containers" ]; then
        echo "[System] Removing stale vLLM server container(s): $stale_containers"
        sudo docker rm -f $stale_containers
    fi

    local stale_ocr_pids
    stale_ocr_pids=$(pgrep -f 'surya\.ocr_error\.server' || true)
    if [ -n "$stale_ocr_pids" ]; then
        echo "[System] Removing stale surya.ocr_error.server process(es): $stale_ocr_pids"
        sudo kill -9 $stale_ocr_pids
    fi
}
export -f cleanup_stale_inference_state

# Auto-restart watchdog: convert_textbook.py now exits non-zero both when
# it detects its own local inference server went dead mid-chunk (the
# degraded-chunk check) and when Docker/the OS kills that server out from
# under it externally (a system-RAM OOM-kill, an orphaned-container VRAM
# exhaustion, or the occasional unexplained container "TaskDelete"). Every
# one of those four confirmed incidents in one real batch this session
# needed a human or an external agent to notice the dead process and
# manually clean up + relaunch. This loop does that automatically instead,
# up to MAX_RETRIES times, before giving up and letting the run end (so
# the "autostop" watcher, if armed, still shuts the VM down rather than
# leaving it running idle forever on a genuinely broken environment).
# Already-completed chunks are skipped on each retry via their .done
# markers, so a retry only redoes the chunk that was in flight.
MAX_RETRIES=5
RETRY_DELAY_S=15
export MAX_RETRIES RETRY_DELAY_S REQUOTED_INPUTS REQUOTED_OUTPUT

run_conversion_with_retries() {
    local attempt=1
    local exit_code=1
    while [ "$attempt" -le "$MAX_RETRIES" ]; do
        echo "[System] Conversion attempt $attempt of $MAX_RETRIES."
        cleanup_stale_inference_state
        cd ~/academic-rag-model
        python3 -u -m textbook.convert_textbook $REQUOTED_INPUTS --output $REQUOTED_OUTPUT
        exit_code=$?

        if [ "$exit_code" -eq 0 ]; then
            echo "[System] Conversion finished successfully on attempt $attempt."
            return 0
        fi

        echo "[System] Conversion exited with code $exit_code on attempt $attempt."
        if [ "$attempt" -eq "$MAX_RETRIES" ]; then
            echo "[System] FATAL: giving up after $MAX_RETRIES attempts. This needs manual"
            echo "[System] investigation -- see the debugging appendix in"
            echo "[System] convert_textbook_agent_instructions.md."
            return "$exit_code"
        fi

        echo "[System] Retrying in ${RETRY_DELAY_S}s (already-completed chunks will be skipped)."
        sleep "$RETRY_DELAY_S"
        attempt=$((attempt + 1))
    done
    return "$exit_code"
}
export -f run_conversion_with_retries

echo "[System] Starting document extraction inside a detached tmux session."
tmux kill-session -t convert 2>/dev/null || true
# Truncate rather than let the first attempt append to a stale log from an
# unrelated earlier launch -- retries WITHIN this run still append (-a
# inside the loop), so one launch's full retry history stays in one file.
: > ~/convert_log.txt
tmux new-session -d -s convert "run_conversion_with_retries 2>&1 | tee -a ~/convert_log.txt"

echo "[System] Started -- this connection can drop safely now."
echo "[System] Check progress: gcloud compute ssh \$VM_INSTANCE_NAME --zone=\$GCP_ZONE --tunnel-through-iap --command=\"tail -n 40 ~/convert_log.txt\""
