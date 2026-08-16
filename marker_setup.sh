#!/usr/bin/env bash
set -e

echo "[System] Updating OS packages and rendering utilities."
sudo apt-get update -qq
sudo apt-get install -y -qq poppler-utils tesseract-ocr

echo "[System] Installing Python dependencies."
python3 -m pip install --upgrade pip -q
python3 -m pip install --no-cache-dir marker-pdf pypdf -q

echo "[System] Environment provisioning completed successfully."