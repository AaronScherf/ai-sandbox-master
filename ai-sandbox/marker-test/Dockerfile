FROM python:3.13-slim

# --- Base packages -----------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gnupg \
        apt-transport-https \
        bash \
    && rm -rf /var/lib/apt/lists/*

# --- Install Google Cloud SDK (gcloud) ----------------------------------
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
        > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update && apt-get install -y --no-install-recommends google-cloud-cli \
    && rm -rf /var/lib/apt/lists/*

# --- Install the Google Colab CLI directly via pip -----------------------
RUN pip install --no-cache-dir google-colab-cli

# --- Working directory ----------------------------------------------------
WORKDIR /workspace

# Persist gcloud/colab CLI credentials and session metadata outside the
# container by mounting volumes at these paths at `docker run` time:
#   -v $HOME/.config/gcloud:/root/.config/gcloud
#   -v $HOME/.config/colab-cli:/root/.config/colab-cli
# This lets you avoid re-authenticating every time you restart the container.

ENTRYPOINT ["/bin/bash"]