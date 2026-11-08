"""
Export presentation_slides.marp.md to high-res, standalone HTML and PDF
using Microsoft Edge headless printing.
"""

import os
import re
import base64
import subprocess

base_dir = r"c:\Users\theaa\ai-sandbox-master\ai-sandbox\research\independent-research\notes\00_overview-and-strategy"
marp_path = os.path.join(base_dir, "presentation_slides.marp.md")
html_path = os.path.join(base_dir, "presentation_slides.html")
pdf_path = os.path.join(base_dir, "presentation_slides.pdf")
edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

with open(marp_path, "r", encoding="utf-8") as f:
    content = f.read()

# Separate frontmatter and slides
# Frontmatter is between first and second '---'
parts = re.split(r'\n---\n', content)
if parts[0].strip() == '' or 'marp: true' in parts[0]:
    frontmatter = parts[0]
    slide_texts = parts[1:]
else:
    slide_texts = parts

def convert_md_to_html(text):
    # Remove presenter notes <!-- Note: ... -->
    notes = re.findall(r'<!--\s*Note:\s*(.*?)\s*-->', text, flags=re.DOTALL)
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # Process classes like <!-- _class: lead -->
    text = re.sub(r'<!--\s*_class:\s*\w+\s*-->', '', text)
    
    # Headers
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    
    # Bold & Italic
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    
    # Inline code
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    
    # Links
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    
    # Bullet points: convert lines starting with * or - into lists
    lines = text.split('\n')
    new_lines = []
    in_list = False
    in_nested_list = False
    
    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        
        if stripped.startswith('* ') or stripped.startswith('- '):
            item = stripped[2:]
            if indent >= 2:
                if not in_nested_list:
                    new_lines.append('<ul style="margin-top: 2px; margin-bottom: 4px; padding-left: 20px;">')
                    in_nested_list = True
                new_lines.append(f'<li>{item}</li>')
            else:
                if in_nested_list:
                    new_lines.append('</ul>')
                    in_nested_list = False
                if not in_list:
                    new_lines.append('<ul style="margin-top: 4px; margin-bottom: 6px; padding-left: 20px;">')
                    in_list = True
                new_lines.append(f'<li>{item}</li>')
        else:
            if in_nested_list:
                new_lines.append('</ul>')
                in_nested_list = False
            if in_list:
                new_lines.append('</ul>')
                in_list = False
            new_lines.append(line)
            
    if in_nested_list:
        new_lines.append('</ul>')
    if in_list:
        new_lines.append('</ul>')
        
    html_body = '\n'.join(new_lines)
    return html_body, notes

# Convert all slides
slides_html = []
for idx, st in enumerate(slide_texts):
    st_clean = st.strip()
    if not st_clean:
        continue
    body, notes = convert_md_to_html(st_clean)
    slide_num = len(slides_html) + 1
    
    # Embed images as Base64 to ensure 100% self-contained rendering
    def replace_img(match):
        img_src = match.group(1)
        # Resolve full path
        img_full_path = os.path.normpath(os.path.join(base_dir, img_src))
        if os.path.exists(img_full_path):
            with open(img_full_path, "rb") as img_f:
                b64_data = base64.b64encode(img_f.read()).decode('utf-8')
            mime = "image/svg+xml" if img_src.endswith('.svg') else "image/png"
            return f'src="data:{mime};base64,{b64_data}"'
        return match.group(0)
        
    body = re.sub(r'src="(figures/[^"]+)"', replace_img, body)
    
    slide_card = f"""
    <section class="slide" id="slide-{slide_num}">
      <div class="slide-content">
        {body}
      </div>
      <div class="slide-footer">
        <span>Aaron Scherf &bull; Columbia University Sustainable Development</span>
        <span>Slide {slide_num} / 15</span>
      </div>
    </section>
    """
    slides_html.append(slide_card)

# Complete HTML Document with 16:9 presentation and print styling
full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>The Humanitarian Planner's Dilemma &bull; Presentation Slides</title>
  <style>
    @page {{
      size: 16in 9in;
      margin: 0;
    }}
    * {{
      box-sizing: border-box;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }}
    body {{
      margin: 0;
      padding: 0;
      background-color: #0b0f19;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .slide {{
      width: 16in;
      height: 9in;
      background: #ffffff;
      padding: 42px 56px 36px 56px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
      margin-bottom: 24px;
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
      page-break-after: always;
      break-after: page;
      overflow: hidden;
    }}
    .slide-content {{
      flex: 1;
      display: flex;
      flex-direction: column;
    }}
    h1 {{
      color: #0f172a;
      font-size: 32px;
      margin-top: 0;
      margin-bottom: 8px;
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 8px;
      font-weight: 700;
      letter-spacing: -0.01em;
    }}
    h2 {{
      color: #1e3a8a;
      font-size: 23px;
      margin-top: 0;
      margin-bottom: 12px;
      font-weight: 600;
    }}
    p, li {{
      font-size: 17.5px;
      line-height: 1.45;
      color: #334155;
    }}
    li {{
      margin-bottom: 6px;
    }}
    strong {{
      color: #0f172a;
    }}
    code {{
      font-family: monospace;
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.9em;
      color: #0f766e;
    }}
    a {{
      color: #2563eb;
      text-decoration: none;
    }}
    .columns {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 36px;
      align-items: start;
      flex: 1;
      margin-top: 4px;
    }}
    .tag {{
      display: inline-block;
      background: #e0e7ff;
      color: #3730a3;
      font-size: 13px;
      padding: 2px 8px;
      border-radius: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      vertical-align: middle;
    }}
    .slide-footer {{
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: #94a3b8;
      border-top: 1px solid #f1f5f9;
      padding-top: 10px;
      margin-top: 10px;
    }}
    @media print {{
      body {{
        background: transparent;
      }}
      .slide {{
        margin: 0;
        box-shadow: none;
        width: 16in;
        height: 9in;
      }}
    }}
  </style>
</head>
<body>
  {''.join(slides_html)}
</body>
</html>
"""

with open(html_path, "w", encoding="utf-8") as f:
    f.write(full_html)
print(f"Generated standalone HTML presentation at {html_path}")

# Run Microsoft Edge headless to print to PDF
cmd = [
    edge_path,
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={pdf_path}",
    html_path
]

print("Executing Microsoft Edge headless PDF print...")
res = subprocess.run(cmd, capture_output=True, text=True)
if os.path.exists(pdf_path):
    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"SUCCESS: Generated PDF deck at {pdf_path} ({size_mb:.2f} MB)")
else:
    print(f"Edge execution finished with code {res.returncode}. Stderr: {res.stderr}")
