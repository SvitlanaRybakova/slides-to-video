"""TTS engine abstraction for voice cloning.

Each engine implements the same interface: load a model, then generate WAV audio
from text using a voice sample for cloning.
"""

from __future__ import annotations

import abc
from pathlib import Path

import json
import subprocess
import numpy as np
import soundfile as sf


class TTSEngine(abc.ABC):
    """Base class for TTS engines with voice cloning."""

    @abc.abstractmethod
    def load(self, device: str) -> None:
        """Load the model onto the given device."""

    @abc.abstractmethod
    def generate(
        self, text: str, voice_wav_path: Path, language: str = "en",
    ) -> tuple[np.ndarray, int]:
        """Generate speech from text, cloning the voice in voice_wav_path.

        Returns (waveform as numpy array, sample_rate).
        """

    def generate_to_file(
        self, text: str, voice_wav_path: Path, output_path: Path,
        language: str = "en",
    ) -> float:
        """Generate speech and save to a WAV file. Returns duration in seconds."""
        wav, sr = self.generate(text, voice_wav_path, language=language)
        sf.write(str(output_path), wav, sr)
        return len(wav) / sr


LANGUAGE_MAP_QWEN3 = {
    "en": "English", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "fr": "French", "de": "German", "es": "Spanish", "ar": "Arabic",
    "ru": "Russian", "pt": "Portuguese",
}


class PiperTTSEngine(TTSEngine):
    """Piper TTS: local speech synthesis with pre-trained ONNX models.

    Uses the piper command-line tool with ONNX models.
    Supports multilingual models including piper-swedish-tts-multispeaker.

    Requires: piper binary installed and model files available.
    Model can be downloaded from: https://huggingface.co/SubZeroAI/piper-swedish-tts-multispeaker

    Example:
        >>> engine = PiperTTSEngine()
        >>> engine.load("cpu")
        >>> wav, sr = engine.generate("Hej på dig", voice_wav_path)
    """

    def __init__(self, model_path: str = None, speaker_id: int = 0):
        import os
        self.speaker_id = speaker_id
        # Resolve model path: param > env var > default relative path
        if model_path:
            self.model_path = os.path.abspath(model_path)
        elif os.environ.get("PIPER_MODEL_PATH"):
            self.model_path = os.path.abspath(os.environ["PIPER_MODEL_PATH"])
        else:
            # Default: look for model in project directory
            default_path = Path(__file__).parent.parent / "piper-model" / "piper-swedish-tts-multispeaker.onnx"
            self.model_path = str(default_path.resolve())
        self.config_path = self.model_path.replace(".onnx", ".onnx.json")

    def load(self, device: str) -> None:
        """Verify model files are available on disk."""
        import os
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Piper model not found at {self.model_path}. "
                "Set PIPER_MODEL_PATH env var or provide model_path parameter. "
                "Download from: https://huggingface.co/SubZeroAI/piper-swedish-tts-multispeaker"
            )
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(
                f"Piper config not found at {self.config_path}."
            )

    def generate(
        self, text: str, voice_wav_path: Path, language: str = "en",
    ) -> tuple[np.ndarray, int]:
        """Generate speech using piper CLI tool."""
        OUTPUT_FILE = str(voice_wav_path)
        command = [
            "piper",
            "--model", self.model_path,
            "--speaker", str(self.speaker_id),
            "--output_file", OUTPUT_FILE,
        ]
        result = subprocess.run(
            command,
            input=text,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Piper TTS failed: {result.stderr}")
        import soundfile as sf
        wav, sr = sf.read(str(OUTPUT_FILE))
        return wav, sr


class ChatterboxEngine(TTSEngine):
    """Chatterbox TTS: local zero-shot voice cloning.

    Requires: uv add chatterbox-tts
    """

    def __init__(self) -> None:
        self.model = None

    def load(self, device: str) -> None:
        from chatterbox.tts import ChatterboxTTS
        self.model = ChatterboxTTS.from_pretrained(device)

    def generate(
        self, text: str, voice_wav_path: Path, language: str = "en",
    ) -> tuple[np.ndarray, int]:
        if language != "en":
            print(
                f"  WARNING: Chatterbox only supports English. "
                f"Ignoring --language {language}. Use --tts-engine qwen3 "
                f"for multilingual support."
            )
        wav_tensor = self.model.generate(text, audio_prompt_path=str(voice_wav_path))
        sr = self.model.sr
        wav = wav_tensor.squeeze().cpu().numpy()
        return wav, sr


class Qwen3TTSEngine(TTSEngine):
    """Qwen3-TTS: 3-second voice cloning, 10 languages, 1.7B params.

    Requires: uv add qwen-tts
    Uses the Base model for voice cloning from a reference audio sample.
    """

    def __init__(self) -> None:
        self.model = None

    def load(self, device: str) -> None:
        import torch
        from qwen_tts import Qwen3TTSModel
        self.model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            device_map=device,
            dtype=torch.bfloat16,
        )

    def generate(
        self, text: str, voice_wav_path: Path, language: str = "en",
    ) -> tuple[np.ndarray, int]:
        lang_name = LANGUAGE_MAP_QWEN3.get(language, "English")
        wavs, sr = self.model.generate_voice_clone(
            text=text,
            language=lang_name,
            ref_audio=str(voice_wav_path),
            x_vector_only_mode=True,
        )
        return wavs[0], sr


ENGINES: dict[str, type[TTSEngine]] = {
    "chatterbox": ChatterboxEngine,
    "qwen3": Qwen3TTSEngine,
    "piper": PiperTTSEngine,
}


def get_engine(name: str) -> TTSEngine:
    """Create a TTS engine by name."""
    if name not in ENGINES:
        available = ", ".join(sorted(ENGINES))
        raise ValueError(f"Unknown TTS engine {name!r}. Available: {available}")
    return ENGINES[name]()