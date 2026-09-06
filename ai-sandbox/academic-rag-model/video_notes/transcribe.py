"""
transcribe.py
Local CPU transcription via faster-whisper -- no cloud call. Spec §3
step 3, §7 for model defaults. `faster_whisper` is imported lazily
inside transcribe_audio(), matching indexer/index_card.py's own
"no heavy import at module load time" convention, so importing this
module never requires faster-whisper's model-loading machinery to
succeed.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

VIDEONOTES_WHISPER_MODEL = os.environ.get("VIDEONOTES_WHISPER_MODEL", "small")
VIDEONOTES_WHISPER_COMPUTE_TYPE = os.environ.get("VIDEONOTES_WHISPER_COMPUTE_TYPE", "int8")


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


def transcribe_audio(
    audio_path: str, model_size: str = VIDEONOTES_WHISPER_MODEL,
    device: str = "cpu", compute_type: str = VIDEONOTES_WHISPER_COMPUTE_TYPE,
) -> list[TranscriptSegment]:
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(audio_path, beam_size=5)
    return [TranscriptSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segments]


def save_transcript(path: str, segments: list[TranscriptSegment]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in segments], f, indent=2, ensure_ascii=False)


def load_transcript(path: str) -> list[TranscriptSegment]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [TranscriptSegment(**item) for item in raw]
