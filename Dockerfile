FROM python:3.13-slim

# --- Base packages + google-colab-cli -----------------------------------
# jupyter-kernel-client is pinned below 1.0.0: that release renamed its
# KernelClient class to JupyterKernelClient, which breaks google-colab-cli
# 0.6.0 (AttributeError: module 'jupyter_kernel_client' has no attribute
# 'KernelClient'). Unpin once a google-colab-cli release supports the new API.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gnupg \
        apt-transport-https \
        bash \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir google-colab-cli "jupyter-kernel-client==0.15.0"

# --- Install Google Cloud SDK (gcloud) ----------------------------------
# Note: apt-key is deprecated/removed on modern Debian/Ubuntu, so we use
# gpg --dearmor into a keyring file instead.
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
        > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update && apt-get install -y --no-install-recommends google-cloud-cli \
    && rm -rf /var/lib/apt/lists/*

# --- Working directory ----------------------------------------------------
WORKDIR /workspace

# Persist gcloud/colab CLI credentials and session metadata outside the
# container by mounting volumes at these paths at `docker run` time:
#   -v $HOME/.config/gcloud:/root/.config/gcloud
#   -v $HOME/.config/colab-cli:/root/.config/colab-cli
# This lets you avoid re-authenticating every time you restart the container.

ENTRYPOINT ["/bin/bash"]
