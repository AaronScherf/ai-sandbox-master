FROM python:3.10-slim

# Install modern system dependencies required for PDF rendering and OCR
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Marker and its dependencies
RUN pip install --no-cache-dir marker-pdf pypdf

# Set environment variables to force CPU execution and prevent RAM crashes
ENV TORCH_DEVICE=cpu
ENV IN_DET_BATCH_SIZE=1
ENV OCR_BATCH_SIZE=1
ENV MARKER_NUM_THREADS=2

WORKDIR /app

# Copy the execution script into the container
COPY app/run_pipeline.py .

CMD ["python", "run_pipeline.py"]

# To execute from terminal
  # Build the Docker image
  #docker build -t marker-cpu-test .
  #
  ## Run the container and mount your current directory to share the PDF and output files
  #docker run --rm -v "${PWD}/app/data:/app/data" -v "${PWD}/output:/app/output" marker-cpu-test


 # Or, comment the two COPY commands and use the following
 # docker build -t marker-base-env .
 # docker run --rm `
    #  -v "${PWD}/run_pipeline.py:/app/run_pipeline.py" `
    #  -v "${PWD}/app/data:/app/data" `
    #  -v "${PWD}/output:/app/output" `
    #  marker-base-env python run_pipeline.py