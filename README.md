# Marker Test

This pipeline tests the marker package functionality for converting a large PDF into a md file with figures saved as referenced images

## To run:

### If the COPY and CMD above are not commented out:
#### Build the Docker image

docker build -t marker-cpu-test .

Run the container and mount your current directory to share the PDF and output files

docker run --rm -v "${PWD}/app/data:/app/data" -v "${PWD}/output:/app/output" marker-cpu-test

to run on a port:

docker run -d -p 8080:8080 -v "${PWD}/app/data:/app/data" -v "${PWD}/output:/app/output" --name my-web-app marker-cpu-test

### Or, if the COPY and CMD commands are commented out, use the following
#### Windows:
docker build -t marker-base-env .

docker run --rm `
      -v "${PWD}/run_pipeline.py:/app/run_pipeline.py" `
      -v "${PWD}/app/data:/app/data" `
      -v "${PWD}/app/output:/app/output" `
      marker-base-env python run_pipeline.py


#### BASH version:
docker build -t marker-base-env .

docker run --rm \
-v "$PWD/run_pipeline.py:/app/run_pipeline.py" \
-v "$PWD/app/data:/app/data" \
-v "$PWD/app/output:/app/output" \
-v "$HOME/.cache/huggingface:/root/.cache/huggingface" \
marker-base-env python /app/run_pipeline.py


### If needed, create swap space
#### 1. Allocate a empty 16 Gigabyte file block
sudo fallocate -l 16G /swapfile

#### 2. Set secure file permissions
sudo chmod 600 /swapfile

#### 3. Format the block as a Linux system Swap space
sudo mkswap /swapfile

#### 4. Turn on the swap space immediately
sudo swapon /swapfile
