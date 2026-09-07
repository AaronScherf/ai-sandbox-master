"""
engine.py
Wraps the two local TTS engines (spec §4): Piper (default, fast) and
Kokoro-ONNX (secondary, higher quality). Both synthesize to a temporary WAV;
pydub/ffmpeg then encodes the final .mp3 -- one shared conversion step
regardless of engine.
"""
from __future__ import annotations

import os
import tempfile
import wave

from pydub import AudioSegment

ENGINES = ("piper", "kokoro")

_MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")

DEFAULT_PIPER_MODEL_PATH = os.environ.get(
    "AUDIOGEN_PIPER_MODEL_PATH", os.path.join(_MODELS_DIR, "en_US-lessac-medium.onnx"),
)
DEFAULT_PIPER_CONFIG_PATH = os.environ.get(
    "AUDIOGEN_PIPER_CONFIG_PATH", os.path.join(_MODELS_DIR, "en_US-lessac-medium.onnx.json"),
)
DEFAULT_KOKORO_MODEL_PATH = os.environ.get(
    "AUDIOGEN_KOKORO_MODEL_PATH", os.path.join(_MODELS_DIR, "kokoro-v1.0.onnx"),
)
DEFAULT_KOKORO_VOICES_PATH = os.environ.get(
    "AUDIOGEN_KOKORO_VOICES_PATH", os.path.join(_MODELS_DIR, "voices-v1.0.bin"),
)
DEFAULT_KOKORO_VOICE = os.environ.get("AUDIOGEN_KOKORO_VOICE", "af_sarah")


def _synthesize_piper_wav(text: str, wav_path: str, model_path: str, config_path: str) -> None:
    from piper import PiperVoice

    voice = PiperVoice.load(model_path, config_path=config_path)
    with wave.open(wav_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)


def _synthesize_kokoro_wav(text: str, wav_path: str, model_path: str, voices_path: str, voice: str) -> None:
    import soundfile as sf
    from kokoro_onnx import Kokoro

    kokoro = Kokoro(model_path, voices_path)
    samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
    sf.write(wav_path, samples, sample_rate)


def synthesize_speech(text: str, output_mp3_path: str, engine: str = "piper") -> None:
    """Synthesizes `text` to `output_mp3_path` using the given engine.
    Raises ValueError up front for an unknown engine name, before any
    synthesis work starts."""
    if engine not in ENGINES:
        raise ValueError(f"Unknown engine {engine!r}, expected one of {ENGINES}")

    os.makedirs(os.path.dirname(output_mp3_path), exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
        wav_path = tmp_wav.name
    try:
        if engine == "piper":
            _synthesize_piper_wav(text, wav_path, DEFAULT_PIPER_MODEL_PATH, DEFAULT_PIPER_CONFIG_PATH)
        else:
            _synthesize_kokoro_wav(
                text, wav_path, DEFAULT_KOKORO_MODEL_PATH, DEFAULT_KOKORO_VOICES_PATH, DEFAULT_KOKORO_VOICE,
            )
        audio = AudioSegment.from_wav(wav_path)
        audio.export(output_mp3_path, format="mp3", bitrate="128k")
    finally:
        os.unlink(wav_path)
