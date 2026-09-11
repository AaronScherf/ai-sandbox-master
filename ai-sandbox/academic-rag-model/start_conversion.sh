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

echo "[System] Starting document extraction inside a detached tmux session."
tmux kill-session -t convert 2>/dev/null || true
tmux new-session -d -s convert \
    "cd ~/academic-rag-model && python3 -u -m textbook.convert_textbook $REQUOTED_INPUTS --output $REQUOTED_OUTPUT 2>&1 | tee ~/convert_log.txt"

echo "[System] Started -- this connection can drop safely now."
echo "[System] Check progress: gcloud compute ssh \$VM_INSTANCE_NAME --zone=\$GCP_ZONE --tunnel-through-iap --command=\"tail -n 40 ~/convert_log.txt\""
