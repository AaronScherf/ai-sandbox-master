# Stage 1: Grab the official pre-compiled Node binaries
FROM node:20-slim AS node_source

# Stage 2: Your actual container build
FROM python:3.11-slim
# Copy ONLY the node binary, not the entire bin folder contents
COPY --from=node_source /usr/local/bin/node /usr/local/bin/node
COPY --from=node_source /usr/local/lib/node_modules /usr/local/lib/node_modules/

# Safely link npm and npx into your path
RUN ln -sf /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -sf /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# Clean system utilities setup and pip configurations
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip

# Force npm to put global CLI tools into standard pathways
RUN npm config set prefix /usr/local

# Install open-interpreter, PDF tools, and the Gemini CLI cleanly
RUN pip install --no-cache-dir open-interpreter pypdf PyMuPDF \
    && npm install -g @google/gemini-cli

# Explicitly ensure binary pathways are appended globally
ENV PATH="/root/.local/bin:/usr/local/bin:${PATH}"

WORKDIR /workspace

# Use standard json-array formatting for CMD to bypass shell parsing bugs
CMD ["tail", "-f", "/dev/null"]
