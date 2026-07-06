# ClipForger-AMD

ClipForger-AMD is a focused Track 2 hackathon build for short-video captioning. It accepts hackathon clips, builds timed subtitles plus visual context, renders a captioned video, generates four styled captions and summaries, self-evaluates accuracy and tone, and exports review-ready outputs.

## What It Does

- Upload one video clip or a fixed batch of hackathon clips.
- Optionally validate the Track 2 duration window through environment settings.
- Extract audio with FFmpeg.
- Build transcript and visual context layers.
- Use Fireworks AI as the primary structured summary-generation provider when `FIREWORKS_API_KEY` is configured.
- Render transcript subtitles into the video and generate judged captions/summaries in four styles: formal, sarcastic, humorous-tech, and humorous-non-tech.
- Score each output for accuracy, tone match, concision, and hallucination risk.
- Review timed subtitles and edit styled captions/summaries in the results view.
- Export a judge-facing submission JSON plus engineering JSON, JSONL, SRT, VTT, or plain text.

## Track 2 Alignment

This is not a full video editor. Cropping, reframing, publishing, pricing, and creator-workflow features have been removed from the core path so the app maps directly to the Video Captioning challenge.

## Architecture

```text
frontend/ React + TanStack Router caption workflow
backend/  FastAPI single/batch upload, job storage, generation, evaluation, export
data/     Local uploaded clips and job JSON files
```

Pipeline:

```text
video upload -> optional duration probe -> audio extraction + keyframes
-> timed transcript + visual context -> captioned video render
-> Fireworks summary generation -> self-evaluation -> edit/export
```

## AMD / Fireworks AI Usage

Fireworks AI is the primary judging-facing summary generation step. `LLM_PROVIDER=auto` uses a Fireworks-first route and keeps fallback diagnostics in exported job metadata so the UI and export flow can still be tested when model access is limited.

Environment variables:

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
VITE_API_BASE_URL=http://localhost:8000
```

Set `MIN_VIDEO_DURATION_SECONDS=0` or `MAX_VIDEO_DURATION_SECONDS=0` to disable either side of the duration check.

Set `FIREWORKS_GEMMA_MODEL` to the hackathon-provided Gemma model id to enter the Best Use of Gemma Models path. With `LLM_PROVIDER=auto`, ClipForger tries Gemma through Fireworks first, then the regular Fireworks model, then Groq as a silent development fallback.

`TRANSCRIPTION_LANGUAGE=en` forces English transcription for the hackathon clips and prevents noisy audio from drifting into another language. Use `ta` for Tamil, or leave it blank for auto-detect.

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

## Hackathon Submission Notes

- The project is containerized with `docker-compose.yml`, `backend/Dockerfile`, and `frontend/Dockerfile`.
- Use `SUBMISSION_GUIDE.md` for the final lablab.ai copy, demo flow, tags, and checklist.
- Submit the public GitHub repository plus the hosted demo URL in the lablab.ai dashboard.
- Required runtime secrets are provided through environment variables; do not commit real API keys.
- Track 2 outputs are available from the Results page: a judge-facing submission JSON, four styled captions/summaries, captioned MP4, SRT/VTT/TXT subtitles, and full engineering JSON.
- For judging, keep `LLM_PROVIDER=auto` with a valid `FIREWORKS_API_KEY`; Gemma through Fireworks is attempted first when `FIREWORKS_GEMMA_MODEL` is set, then the regular Fireworks model. Fallback details are preserved in JSON diagnostics.

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
4. Compare/edit the four styled captions and summaries.
5. Export submission JSON for judging, or JSON/SRT/VTT for inspection.

## Limitations

The final hackathon model list may change. The pipeline is intentionally pluggable so Fireworks multimodal/audio models or a local open-source transcriber can be dropped in without changing the frontend. The submission story should emphasize the Fireworks-first Track 2 compute path.
