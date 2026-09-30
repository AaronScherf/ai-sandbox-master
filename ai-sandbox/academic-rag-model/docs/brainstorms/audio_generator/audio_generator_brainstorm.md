Two high-performance, open-weight neural engines run locally on commodity CPUs without calling any external APIs or requiring a GPU:

| Engine | Model Size | CPU Speed | Voice Quality | Best Used For |
| --- | --- | --- | --- | --- |
| **Piper TTS** | ~20–60 MB | Very Fast (~10× real-time) | Good, clean prosody | Fast batch generation, low resource usage |
| **Kokoro-ONNX** | ~82M params (~300 MB) | Real-time to 3× real-time | Near-human / audiobook grade | Long study notes requiring natural inflection |

---

### Recommended Pipeline: Piper TTS

**Piper** is a VITS-based neural engine running on ONNX Runtime. It is lightweight, ships with a Python API and CLI, and synthesizes audio in seconds on standard CPU hardware.

#### 1. System Dependencies & Python Packages

Ensure `ffmpeg` is installed on your system PATH for MP3 conversion. Then install the Python dependencies:

```bash
pip install piper-tts markdown beautifulsoup4 pydub

```

Download an ONNX voice model and its JSON configuration (for example, `en_US-lessac-medium`):

```bash
# Model weights (~60MB) and voice config
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -L -O https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json

```

---

#### 2. End-to-End Conversion Script

Markdown containing raw code blocks, bullet syntax, and LaTeX will sound disruptive if read literally. The script below:

1. Strips markdown syntax and converts structure into natural prose pauses.
2. Synthesizes audio using Piper via Python.
3. Encodes the output into an `.mp3` file.

```python
#!/usr/bin/env python3
import re
import wave
from pathlib import Path
from bs4 import BeautifulSoup
import markdown
from pydub import AudioSegment
from piper import PiperVoice


def clean_markdown_for_speech(md_text: str) -> str:
    """Strip code blocks, tables, and markup to optimize for audio narration."""
    # Remove code blocks entirely (or summarize them)
    text = re.sub(r"```[\s\S]*?```", " [Code snippet omitted.] ", md_text)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Convert LaTeX delimiters to readable pauses if present
    text = re.sub(r"\$\$([^\$]+)\$\$", r" Equation: \1. ", text)
    text = re.sub(r"\$([^\$]+)\$", r" \1 ", text)

    # Parse remaining markdown via HTML parser to strip syntax clean
    html = markdown.markdown(text)
    soup = BeautifulSoup(html, "html.parser")
    clean_text = soup.get_text(separator=" ")

    # Normalize whitespace
    return re.sub(r"\s+", " ", clean_text).strip()


def md_to_mp3(
    md_file_path: str,
    output_mp3_path: str,
    model_path: str = "en_US-lessac-medium.onnx",
    config_path: str = "en_US-lessac-medium.onnx.json",
):
    md_path = Path(md_file_path)
    text = clean_markdown_for_speech(md_path.read_text(encoding="utf-8"))

    if not text:
        raise ValueError("Provided Markdown file contains no speakable text.")

    # Load Piper model
    voice = PiperVoice.load(model_path, config_path=config_path)

    # Synthesize directly into a temporary WAV
    temp_wav = md_path.with_suffix(".tmp.wav")
    with wave.open(str(temp_wav), "wb") as wav_file:
        voice.synthesize(text, wav_file)

    # Convert WAV to MP3 using ffmpeg/pydub
    audio = AudioSegment.from_wav(str(temp_wav))
    audio.export(output_mp3_path, format="mp3", bitrate="128k")

    # Clean up intermediate WAV file
    temp_wav.unlink(missing_ok=True)
    print(f"Generated: {output_mp3_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert Markdown to MP3 via local CPU TTS")
    parser.add_argument("input_md", help="Path to input .md file")
    parser.add_argument("output_mp3", help="Path to output .mp3 file")
    parser.add_argument("--model", default="en_US-lessac-medium.onnx", help="Path to Piper ONNX file")
    parser.add_argument("--config", default="en_US-lessac-medium.onnx.json", help="Path to Piper config JSON")

    args = parser.parse_args()
    md_to_mp3(args.input_md, args.output_mp3, args.model, args.config)

```

---

### Alternative: CLI Shell Pipeline

If you prefer invoking standard UNIX pipes directly without embedding the Python package:

```bash
# Clean markdown using pandoc and feed straight into piper and ffmpeg
pandoc -f markdown -t plain input.md | \
  piper --model en_US-lessac-medium.onnx --output-raw | \
  ffmpeg -f s16le -ar 22050 -ac 1 -i - -b:a 128k output.mp3

```