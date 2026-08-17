#!/usr/bin/env bash
set -e

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
  || echo "WARNING: Docker cannot see the GPU yet. If this is a brand-new install, a fresh SSH session (or VM reboot) may be needed to pick up the docker group membership before the conversion script runs."

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

echo "[System] Installing marker-pdf and pypdf against the frozen torch stack."
python3 -m pip install --upgrade pip -q
python3 -m pip install --no-cache-dir "pillow<11,>=10.1.0" pypdf marker-pdf -c /tmp/torch-constraints.txt -q

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
# Pre-pull surya's vLLM inference server image now, during one-time setup,
# rather than letting it happen lazily on the first conversion run. Setup
# already only runs once per VM instance (per gcp_instructions.md Step 3.1),
# so this doesn't cost anything extra -- it just moves a network-bound pull
# out of the timed, GPU-billed conversion step, and keeps the per-book
# elapsed-time figures convert_textbook.py prints from being skewed by a
# one-time image download on whichever book happens to run first.
#
# Read the image tag from surya's own settings instead of hardcoding it, so
# this stays correct if the pinned surya-ocr version (a transitive
# dependency of marker-pdf) ever changes its default.
# ---------------------------------------------------------------------------
echo "[System] Pre-pulling surya's vLLM inference server image."
VLLM_DOCKER_IMAGE=$(python3 -c "from surya.settings import settings; print(settings.VLLM_DOCKER_IMAGE)")
echo "Image: $VLLM_DOCKER_IMAGE"
sudo docker pull "$VLLM_DOCKER_IMAGE"

echo "[System] Environment provisioning completed successfully."