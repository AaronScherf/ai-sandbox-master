#!/usr/bin/env bash
set -e

echo "[System] Updating OS packages and core utilities."
apt-get update -qq && apt-get install -y -qq poppler-utils tesseract-ocr unzip

echo "[System] Installing Python dependencies with strict binary constraints."
python3 -m pip install --upgrade pip -q
python3 -m pip install --prefer-binary --no-cache-dir marker-pdf pypdf -q

echo "[System] Extracting pinned native CUDA llama-server binary."
# Version Pinning: Locks the pipeline to a known, stable release.
# This guarantees deterministic execution regardless of upstream repository changes.
PINNED_URL="https://github.com/ggml-org/llama.cpp/releases/download/b3500/llama-b3500-bin-ubuntu-cuda-cu12.2-x64.zip"

wget -qO /content/llama.zip "$PINNED_URL"
unzip -o -j /content/llama.zip "*llama-server" -d /content/
chmod +x /content/llama-server
rm -f /content/llama.zip

echo "[System] Environment provisioning completed successfully."