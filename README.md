# ClipForger-AMD

**Best Use of Gemma in Video Captioning** — Track 2 submission for the AMD Developer Hackathon: ACT II.

ClipForger-AMD takes short video clips (30s–2min) and generates **four styled captions and summaries** (formal, sarcastic, humorous-tech, humorous-non-tech) using **Google Gemma 4 (via OpenRouter)** as the primary LLM, with Fireworks AI and Groq fallback. It also renders a captioned MP4 with burned-in subtitles and provides self-evaluation.

## What Makes This Stand Out

- **🎯 Gemma-first architecture**: Uses **Google Gemma 4 (`google/gemma-4-31b-it:free`)** via OpenRouter as the primary caption generator. When `OPENROUTER_API_KEY` is set, Gemma 4 is always attempted first. Falls back to Fireworks Llama, then Groq. This directly targets the **$3,000 Best Use of Gemma in Video Captioning** prize.
- **🎭 4 style-specific LLM calls**: Each style gets its own dedicated prompt with few-shot examples, separate system instructions, and tailored tone guidance — no cross-style contamination.
- **🖼️ 7 keyframe visual analysis**: Extracts 7 keyframes (up from 3) at evenly-spaced positions, feeding richer visual context to the caption generator.
- **🔍 Detailed evidence pack**: Combines timed transcript evidence with structured visual analysis (setting, people, actions, mood, pacing).
- **⚡ OpenRouter (Gemma 4) + Fireworks AI + Groq**: Gemma 4 via OpenRouter for primary inference. Falls back to Fireworks Llama, then Groq. Zero-cost Gemma 4 usage with the `:free` model.

## What It Does

- Upload one video clip or a fixed batch of hackathon clips.
- Validate the Track 2 duration window (configurable 30–120s default).
- Extract audio + 7 keyframes with FFmpeg.
- Transcribe via Groq Whisper (with chunking for long files).
- Describe frames via Groq vision (5 frames analyzed).
- Generate **4 separate style-specific captions** using Gemma (primary) / Fireworks / Groq.
- Render captioned video with burned-in ASS subtitles.
- Self-evaluate each output for accuracy and tone match.
- Edit and export submission JSON for LLM-Judge scoring.

## Track 2 Docker Submission

The root `Dockerfile` is the judged Track 2 container. It starts `backend/track2_agent.py`, reads `/input/tasks.json`, writes `/output/results.json`, then exits.

Expected input:

```json
[
  {
    "task_id": "v1",
    "video_url": "https://storage.example.com/clips/clip1.mp4",
    "styles": ["formal", "sarcastic", "humorous_tech", "humorous_non_tech"]
  }
]
```

Expected output:

```json
[
  {
    "task_id": "v1",
    "captions": {
      "formal": "...",
      "sarcastic": "...",
      "humorous_tech": "...",
      "humorous_non_tech": "..."
    }
  }
]
```

Build and push:

```bash
docker buildx build --platform linux/amd64 -t YOUR_DOCKERHUB_USERNAME/clipforger-amd:latest --push .
```

Local smoke test:

```bash
docker run --rm \
  -e FIREWORKS_API_KEY="$FIREWORKS_API_KEY" \
  -e FIREWORKS_GEMMA_MODEL="accounts/fireworks/models/gemma-3-12b-it" \
  -v "$PWD/examples:/input:ro" \
  -v "$PWD/out:/output" \
  YOUR_DOCKERHUB_USERNAME/clipforger-amd:latest
```

For the local smoke test, copy `examples/track2_tasks.json` to `examples/tasks.json` first. The hackathon evaluator provides its own `/input/tasks.json` during judging.

## Architecture

```
frontend/  React + TanStack Router caption workflow
backend/   FastAPI single/batch upload, job storage, generation, evaluation, export
data/      Local uploaded clips and job JSON files
```

Pipeline:

```
video upload -> duration probe -> normalize -> audio extraction + 7 keyframes
-> Groq Whisper transcript + Groq vision frame descriptions
-> captioned video render (FFmpeg ASS subtitles)
-> 4 separate style-specific Gemma/Fireworks LLM calls (formal, sarcastic, humorous-tech, humorous-non-tech)
-> heuristic self-evaluation -> edit/export submission JSON
```

### Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **4 separate LLM calls** (one per style) | Each style gets a dedicated system prompt + few-shot examples. No cross-contamination between styles. Better tone differentiation for LLM-Judge. |
| **Gemma-first provider chain** | Gemma is always attempted first when configured. Falls back to Fireworks Llama, then Groq, then local deterministic templates. Maximizes Gemma prize eligibility. |
| **7 keyframes at even intervals** | More visual coverage than 3 keyframes. Enables richer scene description without hitting token limits. |
| **5 frames sent to vision model** | Groq vision receives 5 representative frames for detailed scene analysis. |
| **Per-style few-shot examples** | Each style has 1-2 complete example dialogues showing the exact tone expected. Helps the LLM understand the style boundary. |
| **Sound tagging** | Detects crash/music/inaudible segments from visual context and inserts descriptive tags. |

## AMD / Fireworks AI / Gemma Usage

### Gemma Integration (Prize Track)

ClipForger-AMD uses **Google Gemma 4 (`google/gemma-4-31b-it:free`) via OpenRouter** as the primary caption generation engine. Here's how:

1. **Provider chain**: `LLM_PROVIDER=auto` (default) tries OpenRouter (Gemma 4) → Fireworks Gemma → Fireworks Llama → Groq fallback
2. **Style-specific generation**: Each of the 4 styles calls Gemma independently with a tailored prompt + few-shot examples
3. **Evidence enrichment**: Gemma receives timed transcript + 7-frame visual analysis for accurate captioning
4. **Free tier**: The `:free` suffix means zero-cost Gemma 4 inference via OpenRouter's free tier

To enable Gemma via OpenRouter (recommended for the Gemma prize):

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
OPENROUTER_MODEL=google/gemma-4-31b-it:free
LLM_PROVIDER=auto
```

To use Gemma via Fireworks instead:

```env
FIREWORKS_API_KEY=your_key_here
FIREWORKS_GEMMA_MODEL=accounts/fireworks/models/gemma-model-id
LLM_PROVIDER=auto
```

### Environment Variables

```env
# Required (pick at least one)
FIREWORKS_API_KEY=
OPENROUTER_API_KEY=  # Recommended for Gemma 4 free tier
OPENROUTER_MODEL=google/gemma-4-31b-it:free

# Caption Generation (Gemma-first)
LLM_PROVIDER=auto
FIREWORKS_MODEL=accounts/fireworks/models/llama-v3p1-8b-instruct
FIREWORKS_GEMMA_MODEL=  # Alternative Gemma path via Fireworks

# Groq (transcription + vision + fallback LLM)
GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3

# Transcription
TRANSCRIPTION_LANGUAGE=en
TRANSCRIPTION_PROVIDER=auto

# Vision
VISUAL_PROVIDER=auto

# Storage & Validation
STORAGE_DIR=./data
MIN_VIDEO_DURATION_SECONDS=30
MAX_VIDEO_DURATION_SECONDS=120

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

Set `MIN_VIDEO_DURATION_SECONDS=0` or `MAX_VIDEO_DURATION_SECONDS=0` to disable either side of the duration check.

`TRANSCRIPTION_LANGUAGE=en` forces English transcription. Use `ta` for Tamil, or leave it blank for auto-detect.

## Running Locally

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Docker

```powershell
docker compose up --build
```

Frontend runs on `http://localhost:3000`; backend runs on `http://localhost:8000`.

## API Reference

- `GET /health`
- `POST /api/videos`
- `POST /api/batches`
- `GET /api/jobs`
- `GET /api/batches`
- `GET /api/jobs/{job_id}`
- `POST /api/jobs/{job_id}/generate`
- `POST /api/batches/{batch_id}/generate`
- `GET /api/jobs/{job_id}/results`
- `PATCH /api/jobs/{job_id}/style-outputs`
- `GET /api/jobs/{job_id}/captioned-video`
- `GET /api/jobs/{job_id}/export?format=submission|json|srt|vtt|txt`
- `GET /api/batches/{batch_id}/export?format=submission|json|jsonl`

## Demo Flow

1. Upload one hackathon clip or the fixed clip batch.
2. Watch the caption and summary pipeline progress.
3. Review the captioned video and timed transcript.
4. Compare/edit the four style-specific captions and summaries.
5. Export submission JSON for judging, or JSON/SRT/VTT for inspection.

## Submission Checklist

- [ ] Public GitHub repository with README
- [ ] Containerized with `docker compose up --build`
- [ ] Track 2 agent reads `/input/tasks.json`, writes `/output/results.json`
- [ ] Gemma model configured via `FIREWORKS_GEMMA_MODEL` for prize eligibility
- [ ] Demo video showing upload → processing → 4 styled captions → export
- [ ] Slide deck highlighting Gemma integration and architectural improvements
