# Plan: Update project to use piper-swedish-tts-multispeaker

## Overview
Updated the slides-to-video project to use `piper-swedish-tts-multispeaker` (by SubZeroAI) as the TTS engine. The system uses:
- `script.md` as the text source for narration
- PDF pages as dynamic backgrounds (text and images per page)
- Local execution as much as possible

## Implementation Status

### ✅ `src/tts_engines.py` - PiperTTSEngine Added
New `PiperTTSEngine` class that uses the piper command-line TTS tool with ONNX models.

**Key features:**
- Uses `piper` CLI tool with `--model`, `--speaker`, `--output_file` flags
- Model config loaded for speaker_id_map
- `load(device)` verifies model files exist on disk
- `generate(text, voice_wav_path, language)` runs piper CLI via subprocess
- Falls back to `PIPER_MODEL_PATH` env var or default project path
- Compatible with existing engine abstraction (`get_engine()`, `ENGINES` dict)

**Engine created successfully:**
```
Available engines: ['chatterbox', 'qwen3', 'piper']
Piper engine created OK
Model path: /Users/rsv0011/Workspace/My-projects/slides-to-video/piper-model/piper-swedish-tts-multispeaker.onnx
```

**Error handling when model not found:**
```
FileNotFoundError: Piper model not found at ... Set PIPER_MODEL_PATH env var...
```

### ✅ ENGINES dict Updated
Added `"piper": PiperTTSEngine` to the ENGINES dictionary in `tts_engines.py`.

### ✅ CLI Automatically Updated
`generate.py` line 547 uses `choices=sorted(ENGINES)`, so "piper" is automatically available as a `--tts-engine` option.

### ✅ Server.py Compatible
`server.py` uses `get_engine(tts_engine)` which now supports "piper".

## Required Setup for User

### 1. Install piper binary
```bash
# macOS via Homebrew
brew install piper

# Or download from GitHub releases:
# https://github.com/rhasspy/piper/releases
```

### 2. Download the model
The piper-swedish-tts-multispeaker model from HuggingFace:
- Repository: `SubZeroAI/piper-swedish-tts-multispeaker`
- Files needed: `piper-swedish-tts-multispeaker.onnx` and `piper-swedish-tts-multispeaker.onnx.json`

**Set the model path:**
```bash
export PIPER_MODEL_PATH="/path/to/piper-swedish-tts-multispeaker.onnx"
```

Or place the model in the project directory:
```
slides-to-video/
├── piper-model/
│   ├── piper-swedish-tts-multispeaker.onnx
│   └── piper-swedish-tts-multispeaker.onnx.json
```

### 3. Verify dependencies
Ensure these are installed (already required by project):
- `ffmpeg` and `pdftoppm` (for PDF image extraction and video assembly)
- `soundfile` (for audio I/O)
- `numpy`

### 4. Run the full workflow
```bash
# Using the CLI
uv run src/generate.py \
  --slides presentation.pdf \
  --script script.md \
  --voice voice_sample.wav \
  --tts-engine piper \
  --output output.mp4

# Or via the API
# 1. Load engine: POST /api/load-engine with tts_engine="piper"
# 2. Upload voice sample: POST /api/upload-voice
# 3. Generate all audio: POST /api/generate-all
# 4. Build video: POST /api/build-video
```

## Workflow

```
1. Parse script.md → slides with text per slide (parse_script)
2. Extract PDF page images → dynamic backgrounds (extract_slide_images)
3. Generate TTS audio per slide using piper-swedish-tts-multispeaker
4. Assemble video: image + audio with ambient noise + subtitles (assemble_video)
5. Output narrated video file
```

## Key Differences from Current Engines

| Aspect | Chatterbox/Qwen3 | Piper-swedish-tts-multispeaker |
|---|---|---|
| **Mechanism** | Python voice cloning | CLI tool + ONNX model |
| **Speaker** | Cloned from voice sample | From model config (speaker_id_map) |
| **Language** | Multilingual (Qwen3) or English-only (Chatterbox) | Fixed to Swedish (model language) |
| **Model size** | Large (1.7B params) | Lightweight ONNX model |
| **GPU required** | Yes (for voice cloning) | No (ONNX CPU inference) |
| **Inference speed** | Slower | Faster |

## Verification Steps

1. ✅ Load piper engine: `get_engine("piper")` works
2. Set PIPER_MODEL_PATH and verify `engine.load("cpu")` succeeds
3. Generate audio for a slide text: `engine.generate(text, voice_wav_path)`
4. Verify output is valid WAV at correct sample rate
5. Build full video from PDF + script.md
6. Compare generated audio text matches script.md content

## Files Modified

- `src/tts_engines.py` - Added `PiperTTSEngine` class, updated `ENGINES` dict
- `PLAN.md` - Created with implementation details and setup instructions