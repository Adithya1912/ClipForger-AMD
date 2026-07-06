from __future__ import annotations

from .models import CaptionStyle, Evaluation


def heuristic_evaluation(style: CaptionStyle, styled_caption: str, summary: str, transcript: str) -> Evaluation:
    text = f"{styled_caption} {summary}".lower()
    transcript_terms = {word.strip(".,!?;:()[]").lower() for word in transcript.split() if len(word) > 4}
    if transcript.startswith("NO_TRANSCRIPT_AVAILABLE"):
        transcript_terms = set()
    overlap = sum(1 for word in transcript_terms if word and word in text)
    accuracy = min(0.95, 0.58 + overlap * 0.05)
    tone = 0.82
    if style == CaptionStyle.sarcastic and any(term in text for term in ["apparently", "because", "sure", "naturally"]):
        tone = 0.9
    if style == CaptionStyle.humorous_tech and any(term in text for term in ["debug", "algorithm", "runtime", "api", "deploy"]):
        tone = 0.92
    if style == CaptionStyle.humorous_non_tech and not any(term in text for term in ["api", "debug", "algorithm"]):
        tone = 0.88
    return Evaluation(
        accuracy=round(accuracy, 2),
        tone_match=round(tone, 2),
        hallucination_risk="low" if accuracy > 0.75 else "medium",
        notes="Checks transcript overlap, style cues, and grounded wording before export.",
    )
