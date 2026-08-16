#!/usr/bin/env bash
set -e

echo "[System] Updating OS packages and rendering utilities."
sudo apt-get update -qq
sudo apt-get install -y -qq poppler-utils tesseract-ocr curl gnupg

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

echo "[System] Verifying the preinstalled PyTorch/CUDA stack."
python3 -c "
import torch, torchvision
print(f'torch {torch.__version__} | torchvision {torchvision.__version__} | CUDA available: {torch.cuda.is_available()}')
" || { echo "Critical: preinstalled torch stack is not importable. Aborting before a broken reinstall can mask this."; exit 1; }

echo "[System] Freezing preinstalled torch/torchvision/torchaudio versions as pip constraints."
python3 -c "
import torch, torchvision, torchaudio
print(f'torch=={torch.__version__}')
print(f'torchvision=={torchvision.__version__}')
print(f'torchaudio=={torchaudio.__version__}')
" > /tmp/torch-constraints.txt
cat /tmp/torch-constraints.txt

echo "[System] Installing marker-pdf and pypdf against the frozen torch stack."
python3 -m pip install --upgrade pip -q
python3 -m pip install --no-cache-dir "pillow<11,>=10.1.0" pypdf marker-pdf -c /tmp/torch-constraints.txt -q

echo "[System] Re-verifying torch still resolves correctly after marker-pdf's install."
python3 -c "import torch; print('torch OK:', torch.__version__, '| CUDA:', torch.cuda.is_available())"

echo "[System] Environment provisioning completed successfully."