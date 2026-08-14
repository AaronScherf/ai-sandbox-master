## Step 0: Spin up Docker container to run from Linux environment with correct libraries
#### Run these from PowerShell in your project directory (Dockerfile + .env + convert_textbook.py)

### Step 0.0: Build the image
docker build -t colab-runner .

### Step 0.1: Run the container
#### - Loads PROJECT_ID from .env
#### - Mounts this project dir into /workspace (so convert_textbook.py is visible inside)
#### - Persists gcloud/colab-cli auth across container restarts
docker run -it `
  --env-file .env `
-v ${PWD}:/workspace `
  -v gcloud-config:/root/.config/gcloud `
-v colab-cli-config:/root/.config/colab-cli `
colab-runner

#### You are now inside the container's bash shell for everything below.

### Step 0.2: Ensure Dockerfile has gcloud and google-colab-cli installed

#### Verify colab
colab version

#### Verify gcloud
gcloud version

## Step 1. Authenticate gcloud and colab within Docker container

### 1.1 Update the global active gcloud developer identity profile
gcloud auth application-default login --disable-quota-project
gcloud config set project $PROJECT_ID
gcloud auth application-default set-quota-project $PROJECT_ID

## Step 2. Create Colab session and mount Google Drive, upload script
### 2.1. Create a persistent named session
colab new -s my_session --gpu T4

### 2.2. Mount your Google Drive to that specific session
colab drivemount -s my_session

### 2.3. Upload the script to the Drive root folder
colab upload -s my_session convert_textbook.py /content/convert_textbook.py

## Step 3. Execute the script within colab session
### 3.1. Execute your script in drive against the active session
#### Note: This will take a while to run
colab exec -s my_session << 'EOF'
!PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True TORCH_DEVICE=cuda python3 /content/convert_textbook.py 'academic_resources/math-camp/textbooks-and-papers/textbook.pdf' 'academic_resources/math-camp/textbooks-and-papers/processed_textbooks'
EOF


## Step 4. Manually tear down the session when finished
colab stop -s my_session