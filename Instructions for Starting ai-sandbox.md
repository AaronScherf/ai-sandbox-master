# **Instructions for Starting ai-sandbox**

This zero-knowledge, step-by-step blueprint will guide you through setting up an isolated Docker workspace on Windows, installing Open Interpreter inside it, and using a free Google Gemini API key to securely query your exact folder architecture.

#### **Step 1: Install Docker Desktop on Windows**

Docker Desktop provides the background machinery that lets you run an isolated container on your Surface Pro.

* **Download the Installer:** Visit the official Docker Desktop for Windows download page and download the executable file.  
* **Run the Setup Wizard:** Double-click the installer, and ensure "Use WSL 2 instead of Hyper-V" is checked on the configuration screen (this keeps Docker ultra-lightweight and battery-efficient on a Surface Pro).  
* **Reboot Your PC:** Let the installer finish, then restart Windows when prompted.  
* **Launch Docker:** Open the newly installed Docker Desktop application from your Start Menu. Accept the terms of service, and leave the dashboard running in the background.

#### **Step 2: Grab your Free Google Gemini API Key**

Open Interpreter requires a remote language model backend to function as the "brain".

* **Go to AI Studio:** Log into your Google account and head to the Google AI Studio Console.  
* **Create Key:** Click the blue "Get API key" button in the top left, followed by "Create API key".  
* **Copy It:** Copy the long string of text generated for you (it usually begins with AIzaSy...). Keep this secure and temporarily paste it into a notepad file.

#### **Step 3: Initialize the Master Workspace Sandbox via Bash Script**

Instead of building folders manually, we will use your automated script to generate the walled-off ai-sandbox environment.

* **Open Terminal:** Open Git Bash, WSL, or PowerShell on your Windows PC.  
* **Navigate to Your Root Drive:** Go to the drive where you want your system to live (e.g., cd E:/).  
* **Run the Script:** Save the Bash script provided above as workspace_generator.sh in that root drive, and execute it (bash workspace_generator.sh).  
* **Automated Results:** The script will:
  1. **Master Git Sync**: Check if an existing top-level Git repository is present in the parent directory (`ai-sandbox-master/`) and pull the latest templates. If `GITHUB_SANDBOX_URL` is configured and `.git` is missing, it will initialize and pull from GitHub.
  2. **Scaffold Directory Tree**: Automatically build out the entire directory architecture inside the `ai-sandbox` folder safely.
  3. **Child Git Sync**: Clone or update any nested child repositories (such as your personal portfolio).
  4. **Inject Manuals & Safeguard Configs**: Create/overwrite the latest system documentation, while safeguarding your custom `.gitignore` in the parent directory and `docker-compose.yml` inside the sandbox (including your API keys!) from being overwritten.
  5. **Auto-Initialize Master Repo**: If a top-level Git repository is not found in the parent folder, the script initializes a new one there, makes an initial commit of all workspace-generator files and instructions, and leverages the GitHub CLI (`gh`) to create a private repository on your account and push it. If the CLI is not logged in, it prints clear manual push commands.

#### **Step 4: Secure Your Docker Blueprint (Add API Keys)**

* **Navigate:** Open the newly generated `ai-sandbox/` folder in your file explorer.  
* **Edit:** Open the `.env` file using Windows Notepad or a code editor.  
* **Crucial Edit:** Replace `YOUR_ACTUAL_GEMINI_KEY_HERE` with your raw Google Gemini API key from Step 2. Save and close the file. (This `.env` file is automatically ignored by Git so your key remains 100% secure!).

#### **Step 5: Fire Up Your Container**

Now we will tell Docker to build your virtual boundary workspace.

* Press Windows Key \+ X and select Terminal or PowerShell.  
* Navigate to your tracking directory by typing: cd E:\\ai-sandbox  
* Boot up the environment template by executing: docker compose up \-d  
* (Docker will spend 30 seconds downloading a lightweight official Python layer and creating the secure boundary. You can verify it's active by glancing at the green dot in your visual Docker Desktop dashboard panel).

#### **Step 6: Install Open Interpreter & Launch Your First Analysis**

Your sandbox container is fully built, but it is currently a blank canvas. We will now push Open Interpreter inside it and attach to it.

* **Enter the Sandbox:** Run the following command in your terminal to dive inside your isolated Linux environment: docker exec \-it open\_interpreter\_sandbox bash (Your terminal prompt will instantly change, indicating you are safely working from within the /workspace folder of the container).  
* **Install Open Interpreter:** Run the standard download command: pip install open-interpreter  
* **Launch with Gemini Backend:** Instruct Open Interpreter to initialize itself using your active cloud Gemini API credential string: interpreter \--model gemini/gemini-2.5-flash

#### **Step 7: Querying Your Local Workspace**

Open Interpreter will say hello and offer a chat interface. Because you mapped your files via volume rules, type this exact prompt to test its local map and spatial awareness:  
Hello\! Look at your workspace directory. Run a bash command to find what directories are available to you, and tell me which ones are Read-Only and which ones are Read-Write based on my setup.  
**What to Expect next:**

* Open Interpreter will analyze your question.  
* It will write a small Python/Bash script like os.listdir('.') to inspect the workspace.  
* Because safe mode is natively enabled, it will pause and display the code block on your screen, asking: Would you like to run this code? (y/n).  
* Type y and hit enter. It will execute inside the isolated block, see your exact nested academic-hub, personal-website, and research nodes, and confidently summarize your setup\!