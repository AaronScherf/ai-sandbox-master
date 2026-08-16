FROM python:3.13-slim

# --- Base packages & OpenSSH -----------------------------------
# OpenSSH client is structurally required by the Google Cloud SDK to
# execute `gcloud compute ssh` and `gcloud compute scp` tunneling.
# Legacy Colab and Jupyter kernel dependencies have been excised.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gnupg \
        apt-transport-https \
        bash \
        openssh-client \
    && rm -rf /var/lib/apt/lists/*

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

# Persist gcloud credentials and session metadata outside the
# container by mounting a volume at this path during `docker run`:
#   -v gcloud-config:/root/.config/gcloud
# This prevents the need to re-authenticate OAuth profiles on container restarts.

ENTRYPOINT ["/bin/bash"]