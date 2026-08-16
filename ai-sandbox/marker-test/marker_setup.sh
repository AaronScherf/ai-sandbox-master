#!/usr/bin/env bash
set -e

echo "[System] Updating OS packages and rendering utilities."
sudo apt-get update -qq
sudo apt-get install -y -qq poppler-utils tesseract-ocr curl gnupg

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

echo "[System] Installing Python dependencies."
python3 -m pip install --upgrade pip -q
python3 -m pip install --no-cache-dir marker-pdf pypdf -q

echo "[System] Environment provisioning completed successfully."