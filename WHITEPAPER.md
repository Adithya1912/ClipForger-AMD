# ClipForger Whitepaper

ClipForger narrows the original ClipForger idea into a purpose-built captioning pipeline for AMD Developer Hackathon ACT II Track 2.

The product goal is simple: given a fixed set of short video clips, produce accurate captions or summaries for each clip in four judged styles: formal, sarcastic, humorous-tech, and humorous-non-tech.

## Design Principles

- Accuracy before comedy.
- Four styles must be visibly distinct.
- Funny outputs must stay grounded in the clip.
- Fireworks AI should be central to generation and evaluation.
- The UI should look like a caption lab, not a full nonlinear editor.

## Generation Strategy

The backend prepares transcript and visual-context payloads, asks Fireworks AI for strict JSON, and validates the returned structure. Each style includes a caption, summary, tone notes, confidence, and evaluation metadata. A batch API can process the full fixed clip set and export JSONL for leaderboard-style review.

## Evaluation Strategy

Each generated caption/summary pair gets a self-check object with:

- accuracy
- tone match
- hallucination risk
- notes

This creates a local pre-judge before leaderboard scoring.
