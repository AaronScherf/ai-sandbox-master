#!/usr/bin/env bash
set -e

# ---------------------------------------------------------------------------
# Idempotency: this script is meant to be run at the start of every session,
# not just once after instance creation. SETUP_MARKER is written only after
# every provisioning step below has succeeded; on a later run, if the marker
# exists AND the environment it describes still actually works, we skip
# straight to done instead of re-running apt/pip/docker installs that are
# already satisfied on this persistent disk.
#
# If the marker is missing, this is treated as a fresh instance and the full
# build runs. If the marker exists but re-verification fails (e.g. a
# manually altered environment, or something short of a full stop/start that
# left Docker in a bad state), we deliberately do NOT try to silently repair
# or re-provision on top of unknown state -- we fail loudly and point at a
# clean rebuild instead, for the same reason the torch section below refuses
# to reinstall on top of a preinstalled stack: a repair attempt that goes
# wrong is far harder to diagnose than a clean rebuild.
# ---------------------------------------------------------------------------

SETUP_MARKER="$HOME/.marker_setup_complete"

# Bump this whenever the set of things this script provisions changes (new
# package, new pre-pulled image, etc). A marker written by an older version
# is treated as stale rather than trusted blindly -- otherwise a VM
# provisioned before, say, google-genai was added here would keep skipping
# setup forever and silently never get it, degrading (not breaking) whatever
# feature needed it.
SETUP_VERSION="2"

on_error() {
    local exit_code=$?
    local failed_line=$1
    echo ""
    echo "=================================================================="
    echo "[FATAL] Provisioning failed (exit code $exit_code, line $failed_line)."
    echo "This VM's disk may now be in a partially-provisioned state."
    echo ""
    echo "Do not just rerun this script and hope -- a partial apt/pip/docker"
    echo "install can fail in confusing, hard-to-diagnose ways on a second"
    echo "attempt. Recommended fix: stop this VM, delete it and its disk"
    echo "(gcp_instructions.md Step 4, Option B), recreate a fresh instance,"
    echo "then rerun this setup script from a clean disk."
    echo "=================================================================="
    exit "$exit_code"
}
trap 'on_error $LINENO' ERR

quick_verify_existing_setup() {
    # Re-checks the pieces that actually matter at runtime rather than
    # trusting the marker file blindly. Each check is cheap (no network
    # pulls, since everything it touches was already pulled/installed by a
    # prior full run) so this whole function should finish in a few seconds.
    dpkg -s poppler-utils tesseract-ocr docker.io nvidia-container-toolkit >/dev/null 2>&1 || return 1
    sudo docker info >/dev/null 2>&1 || return 1
    python3 -c "import torch, torchvision, marker, google.genai" >/dev/null 2>&1 || return 1
    python3 -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" >/dev/null 2>&1 || return 1
    # nvidia/cuda:12.9.0-base-ubuntu22.04 was already pulled as a side effect
    # of the GPU-visibility smoke test in the full build below, so this is a
    # cached-image run, not a fresh pull.
    sudo docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi >/dev/null 2>&1 || return 1
    VLLM_DOCKER_IMAGE=$(python3 -c "from surya.settings import settings; print(settings.VLLM_DOCKER_IMAGE)" 2>/dev/null) || return 1
    sudo docker image inspect "$VLLM_DOCKER_IMAGE" >/dev/null 2>&1 || return 1
    return 0
}

if [ -f "$SETUP_MARKER" ]; then
    # The marker file is a plain key=value shell snippet -- source it
    # directly rather than parsing, to pick up setup_version and the rest.
    setup_version=""
    # shellcheck disable=SC1090
    source "$SETUP_MARKER"

    if [ "$setup_version" != "$SETUP_VERSION" ]; then
        echo "[System] Found a provisioning marker from an older setup version"
        echo "(recorded: '${setup_version:-none}', current: '$SETUP_VERSION')."
        echo "[System] Re-running provisioning to pick up what changed -- this is"
        echo "expected after a script update, not a failure."
        # Deliberately falls through to the full build below rather than
        # exiting -- this is a benign, expected case, unlike the
        # re-verification failure case right below it.
    else
        echo "[System] Found prior provisioning marker: $SETUP_MARKER"
        echo "[System] Re-verifying the provisioned environment before deciding whether to skip setup..."
        if quick_verify_existing_setup; then
            echo "[System] Environment already provisioned and verified -- skipping setup."
            echo "[System] Marker contents:"
            cat "$SETUP_MARKER"
            exit 0
        fi
        echo ""
        echo "=================================================================="
        echo "[FATAL] A provisioning marker exists at $SETUP_MARKER (setup_version"
        echo "matches this script), but the environment failed re-verification"
        echo "(see the failed check above). The disk is in an inconsistent state --"
        echo "possibly a manually modified environment, or a VM that lost"
        echo "Docker/CUDA state in a way a normal stop/start shouldn't cause."
        echo ""
        echo "Do not let this script 'fix' it by re-running provisioning on top"
        echo "of an unknown state. Recommended fix: stop this VM, delete it and"
        echo "its disk (gcp_instructions.md Step 4, Option B), recreate a fresh"
        echo "instance, then rerun this setup script from a clean disk."
        echo "=================================================================="
        exit 1
    fi
else
    echo "[System] No prior provisioning marker found -- running full setup."
fi

echo "[System] Updating OS packages and rendering utilities."
sudo apt-get update -qq
sudo apt-get install -y -qq poppler-utils tesseract-ocr curl gnupg

# ---------------------------------------------------------------------------
# Docker + NVIDIA Container Toolkit: required by surya-ocr's VLM inference
# server, NOT unused cruft. On a GPU machine, surya auto-spawns its vLLM
# backend inside a Docker container (Docker + NVIDIA Container Toolkit is
# surya's documented GPU requirement; only the CPU/Apple-Silicon path avoids
# Docker, via llama.cpp). Without this, marker silently falls back to plain
# PyPDF text extraction for every page -- no OCR, no layout, no images.
# ---------------------------------------------------------------------------

echo "[System] Installing Docker daemon."
sudo apt-get install -y -qq docker.io

echo "[System] Provisioning NVIDIA Container Toolkit."
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor --batch --yes -o /tmp/nvidia.gpg
sudo mv /tmp/nvidia.gpg /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list > /dev/null

sudo apt-get update -qq
sudo apt-get install -y -qq nvidia-container-toolkit=1.17.8-1

echo "[System] Configuring Docker Runtime."
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
sudo usermod -aG docker $USER

echo "[System] Verifying Docker can see the GPU (this is what surya's VLM server needs at runtime)."
sudo docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu22.04 nvidia-smi \
  || { echo "[FATAL] Docker cannot see the GPU. If this is a brand-new install, a fresh SSH session (or VM reboot) may be needed to pick up the docker group membership -- reconnect and rerun this script once before treating it as a real failure."; exit 1; }

# ---------------------------------------------------------------------------
# PyTorch: this VM boots from a Deep Learning VM image that already ships a
# matched torch + torchvision + torchaudio + CUDA 12.9 + driver 580 stack.
# DO NOT pip-install torch/torchvision/torchaudio again here — a second
# install from a different CUDA wheel index (e.g. cu121) partially overwrites
# the preinstalled files and leaves a broken hybrid install (missing
# libtorch_global_deps.so, mismatched torchaudio ABI symbols, etc).
# Instead, verify the preinstalled stack, then freeze its exact versions in
# a pip constraints file so nothing installed afterwards can touch it.
# ---------------------------------------------------------------------------

echo "[System] Verifying the preinstalled PyTorch/CUDA stack (torch + torchvision only -- this pipeline never needs torchaudio)."
python3 -c "
import torch, torchvision
print(f'torch {torch.__version__} | torchvision {torchvision.__version__} | CUDA available: {torch.cuda.is_available()}')
" || { echo "Critical: preinstalled torch stack is not importable. Aborting before a broken reinstall can mask this."; exit 1; }

# Some Deep Learning VM image builds ship a torchaudio that does not ABI-match
# their own bundled torch (a packaging issue in the image itself, not
# something this script causes). We never use torchaudio -- transformers only
# imports it because surya-ocr pulls in transformers, and one of its modules
# does an unconditional `import torchaudio` that isn't cleanly optional.
# transformers DOES gracefully handle torchaudio being absent (ImportError is
# caught), but not torchaudio being present-and-broken (raises an unguarded
# OSError instead). So: uninstall it outright rather than leave a broken
# install sitting there for something downstream to trip over.
echo "[System] Removing torchaudio (unneeded, and broken in some image builds)."
python3 -m pip uninstall -y torchaudio -q || true

echo "[System] Freezing preinstalled torch/torchvision versions as pip constraints."
python3 -c "
import torch, torchvision
print(f'torch=={torch.__version__}')
print(f'torchvision=={torchvision.__version__}')
" > /tmp/torch-constraints.txt
cat /tmp/torch-constraints.txt

echo "[System] Installing marker-pdf, pypdf, and google-genai against the frozen torch stack."
# google-genai is used only for LLM-assisted bibliographic metadata extraction
# (convert_textbook.py's --llm-bib, on by default) via Vertex AI -- it doesn't
# touch torch/CUDA at all, but is installed under the same constraints file
# for a single consistent resolve.
python3 -m pip install --upgrade pip -q
python3 -m pip install --no-cache-dir "pillow<11,>=10.1.0" pypdf marker-pdf google-genai -c /tmp/torch-constraints.txt -q

echo "[System] Re-verifying torch still resolves correctly after marker-pdf's install."
python3 -c "import torch; print('torch OK:', torch.__version__, '| CUDA:', torch.cuda.is_available())"

echo "[System] Confirming torchaudio wasn't silently reintroduced as a dependency."
python3 -c "
try:
    import torchaudio
    print('WARNING: torchaudio got reinstalled by marker-pdf/transformers. Version:', torchaudio.__version__)
except ImportError:
    print('OK: torchaudio absent, as expected.')
"

# ---------------------------------------------------------------------------
# Pre-pull surya's vLLM inference server image now, during setup, rather
# than letting it happen lazily on the first conversion run -- this keeps
# the per-book elapsed-time figures convert_textbook.py prints from being
# skewed by a one-time image download on whichever book happens to run
# first. Combined with the idempotency guard above, this now only ever
# happens once per VM disk, not once per session.
#
# Read the image tag from surya's own settings instead of hardcoding it, so
# this stays correct if the pinned surya-ocr version (a transitive
# dependency of marker-pdf) ever changes its default.
# ---------------------------------------------------------------------------
echo "[System] Pre-pulling surya's vLLM inference server image."
VLLM_DOCKER_IMAGE=$(python3 -c "from surya.settings import settings; print(settings.VLLM_DOCKER_IMAGE)")
echo "Image: $VLLM_DOCKER_IMAGE"
sudo docker pull "$VLLM_DOCKER_IMAGE"

echo "[System] Recording successful provisioning marker: $SETUP_MARKER"
{
    echo "setup_version=$SETUP_VERSION"
    echo "provisioned_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "torch_version=$(python3 -c 'import torch; print(torch.__version__)')"
    echo "marker_pdf_version=$(python3 -c 'import importlib.metadata as m; print(m.version("marker-pdf"))')"
    echo "vllm_docker_image=$VLLM_DOCKER_IMAGE"
} > "$SETUP_MARKER"

echo "[System] Environment provisioning completed successfully."
