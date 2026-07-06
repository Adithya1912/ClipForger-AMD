from __future__ import annotations

from .models import CaptionSegment


CRASH_TERMS = ("crash", "fire", "flames", "chaotic", "shock", "panic", "rescue", "accident", "collision")
MUSIC_TERMS = ("music", "song", "singing", "theme")


def add_sound_tags(segments: list[CaptionSegment], duration: float | None, visual_summary: str | None = None) -> list[CaptionSegment]:
    if not segments:
        return []

    sorted_segments = sorted(segments, key=lambda item: item.start)
    enhanced: list[CaptionSegment] = []
    context = (visual_summary or "").lower()
    crash_tag_used = False
    music_tag_used = False

    for index, segment in enumerate(sorted_segments):
        if index == 0 and segment.start >= 2.0:
            tag = "[music]" if any(term in context for term in MUSIC_TERMS) else "[inaudible]"
            enhanced.append(_tag_segment(0.0, min(segment.start - 0.2, 2.2), tag))

        enhanced.append(segment)

        next_start = sorted_segments[index + 1].start if index + 1 < len(sorted_segments) else duration
        if next_start is None:
            continue
        gap = next_start - segment.end
        if gap < 2.0:
            continue

        tag = None
        if any(term in context for term in CRASH_TERMS) and not crash_tag_used:
            tag = "[crashing sound]"
            crash_tag_used = True
        elif any(term in context for term in MUSIC_TERMS) and not music_tag_used:
            tag = "[music]"
            music_tag_used = True
        elif gap >= 4.0:
            tag = "[inaudible]"

        if tag:
            start = segment.end + 0.25
            end = min(next_start - 0.25, start + 2.2)
            if end > start:
                enhanced.append(_tag_segment(start, end, tag))

    return sorted(enhanced, key=lambda item: item.start)


def _tag_segment(start: float, end: float, text: str) -> CaptionSegment:
    return CaptionSegment(start=round(max(0.0, start), 3), end=round(max(start + 0.4, end), 3), text=text)
