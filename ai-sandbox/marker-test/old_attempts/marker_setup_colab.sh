#!/usr/bin/env bash
set -e

echo "[System] Updating OS packages and rendering utilities."
sudo apt-get update -qq
sudo apt-get install -y -qq poppler-utils tesseract-ocr

echo "[System] Verifying Docker daemon status for VLM sandboxing."
# Deep Learning VM Images typically have Docker pre-installed.
# This ensures the service is active and the current user holds execution permissions.
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER

echo "[System] Installing Python dependencies."
# The --prefer-binary constraint is removed as GCP instances possess
# sufficient system memory to execute native wheel compilations if required.
python3 -m pip install --upgrade pip -q
python3 -m pip install --no-cache-dir marker-pdf pypdf -q

echo "[System] Environment provisioning completed successfully."