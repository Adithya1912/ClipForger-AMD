# ClipForger Submission Guide

## Positioning

ClipForger-AMD is a Track 2 video captioning pipeline that uses **Google Gemma via Fireworks AI** to transform short clips into four distinct style-specific captions and summaries.

Key differentiators:
- **Gemma-first architecture** — targets the $3,000 Best Use of Gemma prize
- **4 style-specific LLM calls** — each style has its own prompt, few-shot examples, and tone guardrails
- **7 keyframe visual analysis** — richer scene context for accurate captioning

## Recommended Demo Flow

1. Upload one 30 second to 2 minute clip with clear speech.
2. Click generate.
3. Show the **Gemma badge** on the results page (appears when Gemma model is active).
4. Show the captioned video preview with burned-in subtitles.
5. Show the timed transcript track.
6. Show the four styled outputs — highlight how **each style sounds distinct**.
7. Edit one summary in the UI to show human-in-the-loop polish.
8. Download the captioned MP4.
9. Export the judge-facing submission JSON.

## Submission Copy

**Short description:**
ClipForger-AMD generates captioned videos and four tone-controlled summaries for short clips using a Gemma-first pipeline on Fireworks AI, with 7-keyframe visual analysis and export-ready subtitle files.

**Long description:**
ClipForger-AMD is a Track 2 submission for video captioning built on a **Gemma-first architecture** — Google Gemma models via Fireworks AI are the primary caption generator. It accepts short hackathon clips (30s–2min), extracts audio via FFmpeg, builds a timed transcript with Groq Whisper, analyzes 7 keyframes for visual context, renders a captioned MP4, and generates **four separate style-specific outputs** (formal, sarcastic, humorous-tech, humorous-non-tech) — each with its own dedicated LLM call, system prompt, and few-shot examples. The backend is containerized with FastAPI, the frontend is a React/TanStack Start workflow, and outputs can be exported as JSON, SRT, VTT, TXT, or MP4.

**Key features:**
- **Gemma-first provider chain** — Gemma attempted first, falls back to Fireworks Llama, then Groq
- **4 style-specific prompts** — no cross-contamination between styles, each with few-shot examples
- **7 keyframe visual analysis** — structured scene description (setting, people, actions, mood, pacing)
- **Style-aware evaluation** — per-style tone matching with cross-domain penalties
- **Self-evaluation** — accuracy, tone match, and hallucination risk for every output

## Technology Tags

AI, Video Captioning, Google Gemma, Fireworks AI, AMD, FastAPI, React, TanStack Start, FFmpeg, Whisper, Groq, Multimodal AI, Subtitles

## Gemma Story

We chose **Google Gemma** as our primary caption generation model for several reasons:

1. **Gemma's instruction-following** produces sharply differentiated tones across all four required styles.
2. **Gemma's safety alignment** means outputs stay grounded in evidence and avoid harmful or hallucinated content — critical for an LLM-Judge scoring on accuracy.
3. **Gemma on Fireworks AI** provides fast, AMD-hardware-backed inference with no infrastructure overhead.
4. **Gemma's Apache 2.0 license** means we can build production-ready captioning without licensing constraints.

In our pipeline, Gemma receives:
- Timed transcript with word-level timestamps
- Structured visual analysis from 7 keyframes (setting, people, actions, mood, pacing)
- Style-specific system prompt with few-shot examples
- Sound event tags (crash, music, inaudible markers)

## Final Checklist

- [ ] Public GitHub repository.
- [ ] README includes setup and usage instructions.
- [ ] Docker build works with `docker compose up --build`.
- [ ] Backend health endpoint works at `/health`.
- [ ] Demo app URL is reachable.
- [ ] At least one clean clip has been generated and reviewed.
- [ ] Captions are synced enough for the demo clip.
- [ ] Four styled outputs are manually reviewed before export.
- [ ] Captioned MP4 download works.
- [ ] Submission JSON and optional SRT/VTT exports work.
- [ ] No real API keys are committed.
- [ ] **FIREWORKS_GEMMA_MODEL is configured** for Gemma prize eligibility.
- [ ] **Docker run command includes FIREWORKS_GEMMA_MODEL env var**.
