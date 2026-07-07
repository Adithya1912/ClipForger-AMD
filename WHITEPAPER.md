# ClipForger Whitepaper

ClipForger-AMD is a purpose-built captioning pipeline for AMD Developer Hackathon ACT II Track 2 — optimized for the **$3,000 Best Use of Gemma in Video Captioning** prize.

The product goal: given a fixed set of short video clips, produce accurate captions or summaries for each clip in four judged styles: formal, sarcastic, humorous-tech, and humorous-non-tech.

## Design Principles

- **Gemma-first architecture**: Google Gemma models via Fireworks AI are the primary caption generator. When `FIREWORKS_GEMMA_MODEL` is configured, Gemma is always attempted first.
- **Accuracy before comedy**: Every output must be grounded in the transcript and visual evidence.
- **Four styles must be visibly distinct**: Each style gets its own dedicated LLM call with unique system prompt, few-shot examples, and tone guardrails.
- **Richer visual context**: 7 keyframes (up from 3) feed a structured vision analysis covering setting, people, actions, mood, and pacing.
- **Fireworks AI + AMD hardware**: All LLM inference runs through Fireworks AI on AMD hardware. Groq is used for transcription and vision only.
- **The UI should look like a caption lab**, not a full nonlinear editor.

## Generation Strategy

### Before (baseline)
- One LLM call for all 4 styles at once
- 3 keyframes for visual context
- Generic system prompt for all styles

### After (current)
- **4 separate LLM calls** — one per style, each with:
  - Style-specific system prompt (e.g., "You are a broadcast journalist" for formal, "You are a dry-witted commentator" for sarcastic)
  - Few-shot examples showing the exact expected tone
  - Dedicated JSON output format
- **7 keyframes** extracted at even intervals
- **5 frames** sent to Groq vision for structured scene analysis
- **Richer evidence pack** combining timed transcript, scene description, and mood/pacing analysis

### Provider Chain
```
Gemma (Fireworks) ──> Fireworks Llama ──> Groq ──> Local fallback (deterministic templates)
```

In `LLM_PROVIDER=auto` mode, Gemma is attempted first. If the Gemma model is unavailable or returns errors, the pipeline falls back gracefully.

## Evaluation Strategy

Each generated caption/summary pair gets a style-aware self-check:

- **accuracy**: word-overlap based, capped at 0.95
- **tone match**: style-specific keyword detection with penalization for wrong-domain terms (e.g., tech terms in non-tech style)
- **hallucination risk**: low if accuracy > 0.75
- **notes**: describes what was evaluated

## Key Architectural Improvements

| Area | Before | After | Impact |
|------|--------|-------|--------|
| LLM calls | 1 call for 4 styles | 4 calls, 1 per style | Better tone differentiation |
| Keyframes | 3 frames | 7 frames | Richer visual context |
| Vision prompt | Brief scene description | Structured: setting, people, actions, mood, pacing | More actionable visual data |
| Style prompts | Generic system prompt | Per-style system prompt + few-shot examples | Sharper style separation |
| Evaluator | Simple tone check | Style-aware scoring with cross-domain penalties | More realistic self-evaluation |
| Evidence pack | Clean timed lines + visual | Same + mood/pacing/structured descriptions | Better LLM grounding |
