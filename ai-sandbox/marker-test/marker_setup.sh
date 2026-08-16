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

echo "[System] Environment provisioning completed successfully."