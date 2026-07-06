from __future__ import annotations

from .models import CaptionStyle


STYLE_GUIDE = {
    CaptionStyle.formal: "precise, neutral, professional, and fact-first",
    CaptionStyle.sarcastic: "dry and witty while still describing only what is visible or spoken",
    CaptionStyle.humorous_tech: "playful with software/AI/dev metaphors, but still understandable",
    CaptionStyle.humorous_non_tech: "light, broadly funny, and free of tech jargon",
}


STYLE_LABELS = {
    CaptionStyle.formal: "Formal",
    CaptionStyle.sarcastic: "Sarcastic",
    CaptionStyle.humorous_tech: "Humorous Tech",
    CaptionStyle.humorous_non_tech: "Humorous Non-Tech",
}
