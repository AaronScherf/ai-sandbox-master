# Instructions for using the Linux server

## Method 1: Using WinSCP (Best for Drag-and-Drop)
WinSCP is a free, visual file manager for Windows that splits your screen between your PC and your Linux laptop.Download and install WinSCP.Open WinSCP, select SFTP as the file protocol, and enter your laptop's IP address, Linux username, and password.Click Login to see your Windows files on the left and Linux files on the right.Drag and drop files between the two halves to transfer them.

## Method 2: Using Built-in Windows Command Prompt (No Software Install)
Windows has a built-in tool called scp (Secure Copy) that runs right in your terminal.Open Command Prompt or PowerShell on your Windows PC.To send a file from Windows to Linux:scp C:\path\to\windows-file.txt username@linux_ip:/home/username/DestinationFolder/To pull a file from Linux to Windows:scp username@linux_ip:/home/username/linux-file.txt C:\path\to\windows-folder\

## Method 3: Using RaiDrive (Best for a Permanent Network Drive)
If you prefer your Linux laptop to look and act like a regular USB drive or hard drive inside Windows File Explorer:Download and install RaiDrive.Click Add at the top, choose NAS, and select SFTP.Assign a drive letter (like Z:), enter your laptop's IP address, username, and password.Click OK. Your Linux laptop will now permanently appear under "This PC" in Windows File Explorer until you disconnect it.