# ClipForger Backend

FastAPI service for Track 2 short-video captioning.

## Responsibilities

- Accept single video uploads and fixed clip-set batch uploads.
- Optionally validate clip duration when FFprobe is available.
- Extract audio through FFmpeg.
- Build transcript/context through a pluggable transcription provider.
- Build visual context from extracted keyframes.
- Render timed subtitles into the video and generate four styled captions/summaries with Fireworks AI first, then optional Groq development fallback, then local deterministic fallback.
- Evaluate outputs for tone and accuracy.
- Persist jobs as JSON.
- Export JSON, JSONL, SRT, VTT, and text.

## Run

```powershell
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

## Environment

```env
FIREWORKS_API_KEY=
FIREWORKS_MODEL=accounts/fireworks/models/llama-v3p1-8b-instruct
FIREWORKS_GEMMA_MODEL=
LLM_PROVIDER=auto
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3
TRANSCRIPTION_LANGUAGE=en
TRANSCRIPTION_PROVIDER=auto
VISUAL_PROVIDER=auto
STORAGE_DIR=./data
MIN_VIDEO_DURATION_SECONDS=30
MAX_VIDEO_DURATION_SECONDS=120
```

Set either duration value to `0` to disable that side of the validation.

Set `FIREWORKS_GEMMA_MODEL` to the hackathon-provided Gemma model id to try Gemma through Fireworks before the regular Fireworks model. Keep `LLM_PROVIDER=auto` so Groq remains a silent development fallback.

Use `TRANSCRIPTION_LANGUAGE=en` for English clips, `ta` for Tamil clips, or an empty value for auto-detection.
