import os
import re
import shutil

# Paths configuration
OUTPUT_DIR = r"C:\marker-test\output"       # Where Docker put the chunks
FINAL_DIR = r"C:\marker-test\final_book"    # Where your clean book will go
FINAL_IMAGES_DIR = os.path.join(FINAL_DIR, "all_graphs")

os.makedirs(FINAL_IMAGES_DIR, exist_ok=True)

master_markdown = []
global_image_counter = 0

# 1. Gather all chunks sequentially
chunk_folders = sorted(
    [f for f in os.listdir(OUTPUT_DIR) if f.startswith("chunk_")],
    key=lambda x: int(x.split("_")[1])
)

for folder in chunk_folders:
    chunk_path = os.path.join(OUTPUT_DIR, folder)
    md_file_name = f"{folder}.md"
    md_path = os.path.join(chunk_path, md_file_name)
    images_subfolder_name = f"{folder}_images"
    images_path = os.path.join(chunk_path, images_subfolder_name)

    if not os.path.exists(md_path):
        continue

    print(f"Processing text and images for {folder}...")

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 2. Find all image links like: ![alt](chunk_X_images/image_Y.png)
    # We regex search for the specific image file names to safely copy and rename them
    pattern = rf"{images_subfolder_name}/(image_\d+\.png)"
    found_images = re.findall(pattern, content)

    for old_image_name in found_images:
        old_image_path = os.path.join(images_path, old_image_name)

        if os.path.exists(old_image_path):
            # Create a globally unique name: graph_0001.png, graph_0002.png...
            new_image_name = f"graph_{global_image_counter:04d}.png"
            new_image_path = os.path.join(FINAL_IMAGES_DIR, new_image_name)

            # Copy file to the master images folder
            shutil.copy2(old_image_path, new_image_path)

            # Update the markdown text to point to the new unified location
            old_link_str = f"{images_subfolder_name}/{old_image_name}"
            new_link_str = f"all_graphs/{new_image_name}"
            content = content.replace(old_link_str, new_link_str)

            global_image_counter += 1

    # Append the updated text chunk to our master list
    master_markdown.append(content)

# 3. Save the temporary unified book
unified_md_path = os.path.join(FINAL_DIR, "complete_book.md")
with open(unified_md_path, "w", encoding="utf-8") as f:
    f.write("\n\n<!-- CHUNK BREAK -->\n\n".join(master_markdown))

print(f"\nSuccess! All text combined into 'complete_book.md'.")
print(f"All {global_image_counter} graphs uniquely saved to the 'all_graphs' folder.")
