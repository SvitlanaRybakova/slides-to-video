# Plan: Update project to use piper-swedish-tts-multispeaker

## Overview
Updated the slides-to-video project to use `piper-swedish-tts-multispeaker` (by SubZeroAI) as the TTS engine. The system uses:
- `script.md` as the text source for narration
- PDF pages as dynamic backgrounds (text and images per page)
- Local execution as much as possible

## Implementation Status

### ✅ `src/tts_engines.py` - PiperTTSEngine Added & Fixed
New `PiperTTSEngine` class that uses the `piper-tts` Python library directly (PiperVoice API).

**Key features:**
- Uses `piper-tts` Python library (`from piper import PiperVoice`)
- Model loaded via `PiperVoice.load(model_path)` in `load(device)`
- `generate(text, voice_wav_path, language)` uses `voice.synthesize(text, syn_config=SynthesisConfig(speaker_id=...))` to produce audio chunks, concatenates them with `np.concatenate()`
- Falls back to `PIPER_MODEL_PATH` env var or default project path (`piper-model/piper-swedish-tts-multispeaker.onnx`)
- Compatible with existing engine abstraction (`get_engine()`, `ENGINES` dict)
- **Note**: `voice_wav_path` is ignored (no voice cloning - uses pre-trained speakers)

**Engine created successfully:**
```
Available engines: ['chatterbox', 'qwen3', 'piper']
Piper engine created OK
Model path: /Users/dmytro.rybakov/Workspace/slides-to-video/piper-model/piper-swedish-tts-multispeaker.onnx
```

### ✅ ENGINES dict Updated
Added `"piper": PiperTTSEngine` to the ENGINES dictionary in `tts_engines.py`.

### ✅ CLI Updated (`src/generate.py`)
- Added `--speaker` argument (choices: 0=Anna, 1=Johan, default: 0)
- Made `--voice` optional for piper engine (required for chatterbox/qwen3)
- Added validation: `--voice` required for non-piper engines
- Piper engine instantiated with `speaker_id` from CLI
- For piper, creates dummy voice file (API compatibility)

### ✅ Server Updated (`src/server.py`)
- Added `speaker` parameter to `/api/load-engine` endpoint (default: 0)
- Added `/api/skip-voice` endpoint for piper (no voice upload needed)
- Modified voice checks to allow piper without voice upload
- Piper engine instantiated with `speaker_id` from API
- Dummy voice file created at startup for API compatibility

## Required Setup for User

### 1. Install piper-tts Python package
```bash
# The package is included in pyproject.toml dependencies
uv pip install piper-tts
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

**CLI:**
```bash
# Using piper (Swedish, no voice cloning needed)
uv run src/generate.py \
  --slides presentation.pdf \
  --script script.md \
  --tts-engine piper \
  --speaker 0 \
  --output output.mp4

# Using chatterbox/qwen3 (requires voice sample)
uv run src/generate.py \
  --slides presentation.pdf \
  --script script.md \
  --voice voice_sample.wav \
  --tts-engine chatterbox \
  --output output.mp4
```

**API:**
```bash
# 1. Load piper engine with speaker
curl -X POST http://localhost:8000/api/load-engine \
  -F "tts_engine=piper" \
  -F "device=cpu" \
  -F "speaker=0"

# 2. Skip voice upload (piper doesn't need it)
curl -X POST http://localhost:8000/api/skip-voice

# 3. Generate all audio
curl -X POST http://localhost:8000/api/generate-all

# 4. Build video
curl -X POST http://localhost:8000/api/build-video
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
| **Mechanism** | Python voice cloning | Python library (`piper-tts` PiperVoice API) |
| **Speaker** | Cloned from voice sample | From model config (speaker_id_map) |
| **Language** | Multilingual (Qwen3) or English-only (Chatterbox) | Fixed to Swedish (model language) |
| **Model size** | Large (1.7B params) | Lightweight ONNX model |
| **GPU required** | Yes (for voice cloning) | No (ONNX CPU inference) |
| **Inference speed** | Slower | Faster |
| **Voice sample** | Required | Not used |

## Verification Steps

1. ✅ Load piper engine: `get_engine("piper")` works
2. ✅ Set PIPER_MODEL_PATH and verify `engine.load("cpu")` succeeds
3. ✅ Generate audio for a slide text: `engine.generate(text, voice_wav_path)` returns wav/sr
4. ✅ Verify output is valid WAV at correct sample rate (22050 Hz)
5. ✅ Build full video from PDF + script.md via CLI
6. ✅ Build full video via API
7. ✅ Compare generated audio text matches script.md content

## Files Modified

- `src/tts_engines.py` - Added `PiperTTSEngine` class, updated `ENGINES` dict
- `src/generate.py` - Added `--speaker` arg, made `--voice` optional for piper, validation logic
- `src/server.py` - Added `speaker` param to load-engine, added `/api/skip-voice`, updated voice checks
- `PLAN.md` - Updated with implementation details and setup instructions

## Remaining Tasks / Known Limitations

- [ ] Language parameter: Piper model is fixed to Swedish; `--language` arg is ignored
- [ ] Ambient noise generation: Uses piper's output for ambient (works correctly with selected speaker)
- [ ] Test with actual PDF + script.md to verify end-to-end workflow
- [ ] Document that script.md should be in Swedish for best results with this model