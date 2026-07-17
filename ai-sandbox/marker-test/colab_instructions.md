
## If colab is not authenticated

# 1. Update the global active gcloud developer identity profile
gcloud auth login --disable-quota-project

gcloud config set project PROJECT_ID

gcloud auth application-default set-quota-project PROJECT_ID

colab new --gpu T4

colab drivemount

# To execute the script

colab run --gpu T4 convert_textbook.py "drive/MyDrive/academic_resources/math-camp/textbooks-and-papers/textbook.pdf" "drive/MyDrive/academic_resources/math-camp/textbooks-and-papers/processed_textbooks"


OR 

# 1. Create a persistent named session
colab new -s my_session --gpu T4

# 2. Mount your Google Drive to that specific session
colab drivemount -s my_session

# 3. Execute your local script against the active session

cat convert_textbook.py | colab exec -s my_session -- python3 - "academic_resources/math-camp/textbooks-and-papers/textbook.pdf" "academic_resources/math-camp/textbooks-and-papers/processed_textbooks"

cat convert_textbook.py | colab exec -s my_session "python3 - 'academic_resources/math-camp/textbooks-and-papers/textbook.pdf' 'academic_resources/math-camp/textbooks-and-papers/processed_textbooks'"


# 4. Manually tear down the session when finished
colab stop -s my_session



Option 2:

colab run -s my_session --keep convert_textbook.py "academic_resources/math-camp/textbooks-and-papers/textbook.pdf" "academic_resources/math-camp/textbooks-and-papers/processed_textbooks"

colab drivemount -s my_session

colab exec -s my_session -- python3 convert_textbook.py "academic_resources/textbook.pdf" "academic_resources/processed"


# 1. Spin up a GPU session and upload/run the file (it will fail when checking for the Drive path, which is expected)
colab run -s my_session --gpu T4 --keep convert_textbook.py \
"academic_resources/math-camp/textbooks-and-papers/textbook.pdf" \
"academic_resources/math-camp/textbooks-and-papers/processed_textbooks"

# 2. Complete the interactive Drive authentication to mount your space
colab drivemount -s my_session

# 3. Re-execute the script now that the drive is mounted. The file already sits inside the VM.
colab exec -s my_session "!python3 convert_textbook.py 'academic_resources/math-camp/textbooks-and-papers/textbook.pdf' 'academic_resources/math-camp/textbooks-and-papers/processed_textbooks'"


# Option 3: Upload script during session

colab new -s my_session --gpu T4

colab drivemount -s my_session

colab upload -s my_session convert_textbook.py /content/convert_textbook.py

colab exec -s my_session << 'EOF'
!PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 python3 /content/convert_textbook.py 'academic_resources/math-camp/textbooks-and-papers/textbook.pdf' 'academic_resources/math-camp/textbooks-and-papers/processed_textbooks'
EOF
