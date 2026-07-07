from __future__ import annotations

from .models import CaptionStyle, Evaluation


def heuristic_evaluation(style: CaptionStyle, styled_caption: str, summary: str, transcript: str) -> Evaluation:
    text = f"{styled_caption} {summary}".lower()
    transcript_terms = {word.strip(".,!?;:()[]'\"").lower() for word in transcript.split() if len(word) > 4}
    if transcript.startswith("NO_TRANSCRIPT_AVAILABLE"):
        transcript_terms = set()
    overlap = sum(1 for word in transcript_terms if word and word in text)
    accuracy = min(0.95, 0.58 + overlap * 0.05)

    tone = 0.82
    if style == CaptionStyle.formal:
        formal_terms = ["the", "a", "an", "is", "are", "was", "were", "demonstrates", "indicates", "shows", "reports", "confirms", "conducts", "performs"]
        formal_score = sum(1 for term in formal_terms if term in text) / max(1, len(text.split()) * 0.1)
        tone = min(0.94, 0.78 + formal_score * 0.12)
        if any(term in text for term in ["debug", "runtime error", "apparently", "lol", "lmfao"]):
            tone = max(0.4, tone - 0.3)

    if style == CaptionStyle.sarcastic:
        sarcastic_terms = ["apparently", "because", "sure", "naturally", "clearly", "obviously", "indeed", "oh", "well then", "how convenient"]
        sarcastic_score = sum(1 for term in sarcastic_terms if term in text)
        tone = min(0.95, 0.78 + sarcastic_score * 0.04)
        if any(term in text for term in ["debug", "runtime error", "algorithm"]):
            tone = max(0.5, tone - 0.2)

    if style == CaptionStyle.humorous_tech:
        tech_terms = ["debug", "runtime error", "algorithm", "api", "deploy", "kernel panic", "system failure",
                     "memory leak", "exception", "thread", "buffer", "cache", "stack overflow", "loop",
                     "redundancy", "protocol", "pipeline", "data", "compile", "syntax", "recursion",
                     "throughput", "latency", "bandwidth", "segment fault", "404", "500"]
        tech_score = sum(1 for term in tech_terms if term in text)
        tone = min(0.95, 0.78 + tech_score * 0.03)
        if any(term in text for term in ["apparently", "how convenient"]):
            tone = max(0.5, tone - 0.15)

    if style == CaptionStyle.humorous_non_tech:
        tech_terms_in_text = sum(1 for term in ["api", "debug", "algorithm", "runtime", "deploy", "kernel", "syntax"] if term in text)
        if tech_terms_in_text == 0:
            tone = 0.90
        else:
            tone = max(0.6, 0.88 - tech_terms_in_text * 0.08)
        non_tech_humor_terms = ["everyone", "nobody", "somehow", "somewhere", "well", "thing", "really",
                               "absolutely", "literally", "basically", "actually", "moment",
                               "plan", "idea", "someone", "friend", "guy", "person"]
        humor_score = sum(1 for term in non_tech_humor_terms if term in text)
        tone = min(0.94, tone + humor_score * 0.015)

    return Evaluation(
        accuracy=round(accuracy, 2),
        tone_match=round(tone, 2),
        hallucination_risk="low" if accuracy > 0.75 else "medium",
        notes="Evaluated for transcript overlap, style-specific tone markers, and factual grounding.",
    )
