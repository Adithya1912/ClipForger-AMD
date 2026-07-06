# ClipForger Submission Guide

## Positioning

ClipForger is a Track 2 video captioning pipeline that turns short clips into:

- A captioned MP4 with burned-in timed subtitles.
- SRT, VTT, TXT, JSON, and batch JSONL exports.
- A submission JSON that contains only the four Track 2 styled deliverables.
- Four judge-ready styled outputs: formal, sarcastic, humorous-tech, and humorous-non-tech.

## Recommended Demo Flow

1. Upload one 30 second to 2 minute clip with clear speech.
2. Click generate.
3. Show the captioned video preview.
4. Show the timed transcript track.
5. Show the four styled outputs.
6. Edit one summary in the UI to show human-in-the-loop polish.
7. Download the captioned MP4.
8. Export the judge-facing submission JSON and optional SRT/VTT.

## Submission Copy

Short description:

ClipForger generates captioned videos and four tone-controlled summaries for short clips, using a Fireworks-first pipeline with safe fallback routing and export-ready subtitle files.

Long description:

ClipForger is a focused Track 2 submission for video captioning. It accepts short hackathon clips, extracts audio, builds a timed transcript, adds conservative sound tags, renders a captioned MP4, and generates four styled outputs for formal, sarcastic, humorous-tech, and humorous-non-tech tones. The app keeps captions and summaries separate: captions are literal timed subtitles, while the four styles are judge-facing summaries and styled captions. The backend is containerized with FastAPI and FFmpeg, the frontend is a React workflow, and outputs can be exported as JSON, JSONL, SRT, VTT, TXT, or MP4.

## Technology Tags

AI, Video Captioning, Fireworks AI, AMD, Gemma-ready, FastAPI, React, FFmpeg, Whisper, Multimodal AI, Subtitles

## Credit-Safe Provider Story

Use this wording if Gemma dedicated deployment is too expensive:

The app includes Gemma-ready routing through Fireworks AI, but the live demo keeps dedicated Gemma deployment disabled to stay within hackathon credit limits. The architecture uses a Fireworks-first route when configured and preserves fallback diagnostics in exported job metadata.

## Final Checklist

- Public GitHub repository.
- README includes setup and usage instructions.
- Docker build works with `docker compose up --build`.
- Backend health endpoint works at `/health`.
- Demo app URL is reachable.
- At least one clean clip has been generated and reviewed.
- Captions are synced enough for the demo clip.
- Four styled outputs are manually reviewed before export.
- Captioned MP4 download works.
- Submission JSON and optional SRT/VTT exports work.
- No real API keys are committed.
