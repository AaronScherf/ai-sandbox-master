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

echo "[System] Purging residual VLM server locks."
sudo rm -f /root/.cache/datalab/surya/vllm_server.lock

# A killed/crashed/reset "convert" session leaves its vLLM inference server
# container running -- Docker containers aren't tied to the tmux session
# that started them, so `tmux kill-session -t convert` (or a VM reset)
# never stops it. The lock purge above only clears a lock FILE, not the
# actual container. Confirmed live: after two kill/relaunch cycles in one
# session (excluding then re-including a book, then a hard reset), TWO
# separate `surya-vllm-*` containers were found still running, each holding
# its own full copy of the model's GPU memory (16.2GB + 6.2GB out of the
# L4's 23GB total) -- the combined footprint left no headroom for real
# page processing, and every page from that point on silently failed over
# to the bare PyPDF fallback with a CUDA out-of-memory error, not a fatal
# one. Stop and remove any leftover ones before every launch so this can't
# accumulate across restarts.
STALE_VLLM_CONTAINERS=$(sudo docker ps -aq --filter "name=surya-vllm-")
if [ -n "$STALE_VLLM_CONTAINERS" ]; then
    echo "[System] Removing stale vLLM server container(s) from a prior run: $STALE_VLLM_CONTAINERS"
    sudo docker rm -f $STALE_VLLM_CONTAINERS
fi

# The vLLM Docker container isn't the only leftover risk -- surya also
# spawns its own standalone `python3 -m surya.ocr_error.server` process
# directly on the host (not inside Docker) the first time a chunk needs
# OCR-error detection, and reuses it for the rest of the run rather than
# starting a fresh one per chunk. Confirmed live: killing the "convert"
# tmux session does NOT kill this process -- it gets reparented to init
# (PPID 1) and keeps running orphaned, still holding its own slice of GPU
# memory (514MB observed), on top of whatever the vLLM container(s) hold.
# Same accumulation risk as the vLLM containers, different mechanism.
STALE_OCR_ERROR_PIDS=$(pgrep -f 'surya\.ocr_error\.server' || true)
if [ -n "$STALE_OCR_ERROR_PIDS" ]; then
    echo "[System] Removing stale surya.ocr_error.server process(es) from a prior run: $STALE_OCR_ERROR_PIDS"
    sudo kill -9 $STALE_OCR_ERROR_PIDS
fi

echo "[System] Starting document extraction inside a detached tmux session."
tmux kill-session -t convert 2>/dev/null || true
tmux new-session -d -s convert \
    "cd ~/academic-rag-model && python3 -u -m textbook.convert_textbook $REQUOTED_INPUTS --output $REQUOTED_OUTPUT 2>&1 | tee ~/convert_log.txt"

echo "[System] Started -- this connection can drop safely now."
echo "[System] Check progress: gcloud compute ssh \$VM_INSTANCE_NAME --zone=\$GCP_ZONE --tunnel-through-iap --command=\"tail -n 40 ~/convert_log.txt\""
