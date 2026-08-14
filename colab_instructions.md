# Textbook Conversion Pipeline

## Step 0: Spin up the Docker container

Run these from PowerShell in your project directory (`Dockerfile` + `.env` + `convert_textbook.py`). Make sure the Docker daemon is running first — open Docker Desktop if needed.

### Step 0.0–0.1: Build the image (first time only) and start the container

- **First run:** no `colab-container` exists yet, so this builds the image (~3 minute to install libraries) and creates + starts a named container.
- **Every run after:** skips the build entirely and reuses the same existing container via `docker start`.
- Loads `PROJECT_ID` from `.env` (kept one directory up, alongside the rest of the project — not inside this subdirectory).
- Mounts this project dir into `/workspace` (so `convert_textbook.py` is visible inside).
- Persists `gcloud`/`colab-cli` auth across container restarts.

```shell
if (docker ps -aq -f "name=^colab-container$") {
    docker start -ai colab-container
} else {
    docker build -t colab-runner .
    docker run -it --name colab-container `
        --env-file ../.env `
        -v ${PWD}:/workspace `
        -v gcloud-config:/root/.config/gcloud `
        -v colab-cli-config:/root/.config/colab-cli `
        colab-runner
}
```

You are now inside the container's bash shell for everything below.

### Step 0.2: Ensure the Dockerfile has `gcloud` and `google-colab-cli` installed

```bash
# Verify colab
colab version

# Verify gcloud
gcloud version

# Verify jupyter-kernel-client, since pinned to specific version 0.15.0 in dockerfile
pip show jupyter-kernel-client
```

## Step 1: Authenticate gcloud and colab within the Docker container

### 1.1 Update the global active gcloud developer identity profile

```bash
gcloud auth application-default login --disable-quota-project
gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID
```

## Step 2: Create Colab session and mount Google Drive, upload script

### 2.1 Create a persistent named session
Prune any existing sessions via:

```bash
colab stop
```

Then create a new session:
```bash
colab new -s my_session --gpu T4
```

### 2.2 Mount your Google Drive to that specific session

```bash
colab drivemount -s my_session
```

### 2.3 Upload the script to the Drive root folder

```bash
colab upload -s my_session convert_textbook.py /content/convert_textbook.py
```

## Step 3: Execute the script within the Colab session

### 3.1 Execute package installation first



```bash
colab exec -s my_session --timeout 14400 << 'EOF'
# 1. Install base OS dependencies
!apt-get update -qq && apt-get install -y --no-install-recommends poppler-utils tesseract-ocr libgl1 libglx-mesa0

# 2. Install Python packages (vLLM and llama.cpp are intentionally omitted)
!python -m pip install --upgrade pip
!python -m pip install --progress-bar on marker-pdf pypdf transformers accelerate huggingface_hub
EOF
```

### 3.2 Execute the conversion script

```bash
colab exec -s my_session --timeout 14400 << 'EOF'
!python3 -u /content/convert_textbook.py 'academic_resources/math-camp/textbooks-and-papers/textbook.pdf' 'academic_resources/math-camp/textbooks-and-papers/processed_textbooks'
EOF
```

## Step 4: Manually tear down the session when finished

```bash
colab stop -s my_session
```

## Troubleshooting

### `AttributeError: module 'jupyter_kernel_client' has no attribute 'KernelClient'`

**Root cause (confirmed):** `jupyter-kernel-client` (from Datalayer) renamed its `KernelClient` class to `JupyterKernelClient` in its `1.0.0` release. `google-colab-cli` 0.6.0 was written against the old pre-1.0 API. Since neither this Dockerfile nor `google-colab-cli`'s own install pins an exact version of that dependency, `pip install` grabs the latest `1.0.x` release by default — which no longer has the name the CLI is looking for.

**Fix — pin `jupyter-kernel-client` below `1.0.0`:**

```bash
# Inside an existing container, to fix it immediately without rebuilding:
pip install --force-reinstall "jupyter-kernel-client==0.15.0"
```

The Dockerfile now pins this version at build time so future rebuilds don't reintroduce the break. Once a `google-colab-cli` release ships support for the renamed `JupyterKernelClient` API, this pin can be removed.

