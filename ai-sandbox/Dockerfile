FROM python:3.11-slim

# Install system utilities and upgrade pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

# Install open-interpreter and PDF tools explicitly
RUN pip install --no-cache-dir open-interpreter pypdf PyMuPDF

# Explicitly ensure the binary pathway is appended globally
ENV PATH="/root/.local/bin:/usr/local/bin:${PATH}"

WORKDIR /workspace

# Use standard json-array formatting for CMD to bypass shell parsing bugs
CMD ["tail", "-f", "/dev/null"]