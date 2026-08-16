#!/usr/bin/env bash
set -e

echo "[System] Updating OS packages and rendering utilities."
sudo apt-get update -qq
sudo apt-get install -y -qq poppler-utils tesseract-ocr

echo "[System] Verifying Docker daemon status for VLM sandboxing."
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

echo "[System] Installing Python dependencies."
python3 -m pip install --upgrade pip -q
python3 -m pip install --no-cache-dir marker-pdf pypdf -q

echo "[System] Environment provisioning completed successfully."