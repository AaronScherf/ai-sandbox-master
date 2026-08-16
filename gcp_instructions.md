# Textbook Conversion Pipeline



## Step 0: Initialize the Docker Container

Execute the following script from PowerShell within the project directory (containing the `Dockerfile`, `.env`, and `convert_textbook.py`). Ensure the Docker daemon is operational prior to execution.

### Step 0.1: Build and instantiate the environment

* **Initial Execution:** This builds the image and instantiates a named container. The `colab-cli` dependencies have been structurally excised.
* **Subsequent Executions:** Skips the build phase and restores the existing container via `docker start`.
* Loads `PROJECT_ID` from the `.env` file located in the parent directory.
* Mounts the current project directory into `/workspace` to ensure local synchronization of the extraction scripts.
* Persists `gcloud` authentication configurations across container lifecycles via volume mounting.

```powershell
if (docker ps -aq -f "name=^gcp-container$") {
    docker start -ai gcp-container
} else {
    docker build -t gcp-runner .
    docker run -it --name gcp-container `
        --env-file ../.env `
        -v ${PWD}:/workspace `
        -v ${PWD}\..\academic-hub:/academic-hub `
        -v gcloud-config:/root/.config/gcloud `
        -v gcloud-ssh:/root/.ssh `
        gcp-runner
}
```
Note: To stop and remove a previously created Docker container (in case you need to reconfigure it), use:
docker stop gcp-container
docker rm gcp-container

You are now operating within the container's interactive bash shell for all subsequent operations.

### Step 0.2: Declare textbook filename

Change this to update the target textbook

```bash
export PDF_FILENAME="Book_of_Proof_Hammack_Richard_2018.pdf"
```

### Step 0.3: Verify SDK Installation

Validate the Google Cloud SDK installation.

```bash
gcloud version
```

## Step 1: Authenticate the SDK within the Container

### 1.1 Update the global active developer identity profile

```bash
gcloud auth application-default login --disable-quota-project
gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID
```

## Step 2: Synchronize Scripts to the Virtual Machine

Transfer the provisioning and execution scripts to the home directory of the remote Compute Engine instance.

This will trigger the SSH key metadata to update, which may require additional authentication.

```bash
gcloud compute scp marker_setup.sh convert_textbook.py $VM_INSTANCE_NAME:~/ --zone=$GCP_ZONE --tunnel-through-iap
```

## Step 3: Execute the Extraction Pipeline

### 3.1 Execute environment provisioning

This provisions the OS and Python dependencies. Capitalizing on the VM's persistent disk architecture, this command only requires execution once following instance creation.

```bash
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="bash -s" << 'EOF'
bash ~/marker_setup.sh
EOF
```

### 3.2 Stage the input document in Google Cloud Storage
Before executing the extraction, the raw PDF must be uploaded to your GCS bucket so the remote Virtual Machine can access it.

```bash
gcloud storage cp "/academic-hub/academic_resources/math-camp/textbooks-and-papers/$PDF_FILENAME" "gs://$BUCKET_NAME/input_documents/$PDF_FILENAME"
```

### 3.3 Convert the PDF to structured artifacts

Execute the conversion. Because the underlying hardware is persistent, this command can be run iteratively to process distinct PDFs without re-provisioning the environment or recompiling binaries.

```bash
gcloud compute ssh $VM_INSTANCE_NAME --zone=$GCP_ZONE --tunnel-through-iap --command="bash -s" << EOF
echo "[System] Purging residual VLM server locks."
sudo rm -f /root/.cache/datalab/surya/vllm_server.lock

echo "[System] Initiating document extraction."
python3 -u ~/convert_textbook.py "gs://$BUCKET_NAME/input_documents/$PDF_FILENAME" "gs://$BUCKET_NAME/processed_outputs"
EOF
```

### 3.4 Export the structured artifacts to the local host

Google Cloud VMs do not natively mount Google Drive. To retrieve the markdown and image artifacts, execute a recursive secure copy from the VM back to the local Docker workspace. The volume mount established in Step 0.1 will automatically synchronize these files to your local Windows filesystem.

```bash
# Ensure the local target directory structure exists prior to transfer
mkdir -p ./academic_resources/math-camp/textbooks-and-papers/processed_outputs/

# Recursively download the processed artifacts from the GCS bucket
gcloud storage cp -r gs://$BUCKET_NAME/processed_outputs/* ./academic_resources/math-camp/textbooks-and-papers/processed_outputs/
```

## Step 4: Terminate the Compute Instance

To halt billing cycles, the VM must be explicitly stopped or deleted upon completion of the pipeline.

```bash
# Option A: Stop the instance. This halts compute billing but preserves the disk 
# (and provisioning state) for future executions. Minimal storage fees apply.
gcloud compute instances stop $VM_INSTANCE_NAME --zone=$GCP_ZONE

# Option B: Delete the instance entirely. This permanently destroys the disk and 
# halts all billing mechanisms. Provisioning (Step 3.1) must be repeated upon recreation.
gcloud compute instances delete $VM_INSTANCE_NAME --zone=$GCP_ZONE --quiet

```