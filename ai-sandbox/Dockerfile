FROM python:3.11-slim

# Install system utilities, Node.js runtime, and upgrade pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

# Install open-interpreter, PDF tools, and the Gemini CLI explicitly
RUN pip install --no-cache-dir open-interpreter pypdf PyMuPDF \
    && npm install -g @google/gemini-cli

# Explicitly ensure the binary pathway is appended globally
ENV PATH="/root/.local/bin:/usr/local/bin:${PATH}"

WORKDIR /workspace

# Use standard json-array formatting for CMD to bypass shell parsing bugs
CMD ["tail", "-f", "/dev/null"]