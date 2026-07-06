from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path
from typing import Any

import requests

from app.config import settings
from app.models import CaptionSegment


NO_TRANSCRIPT = "NO_TRANSCRIPT_AVAILABLE"
MAX_TRANSCRIPTION_FILE_MB = 24
CHUNK_DURATION_SECONDS = 300
CAPTION_WORDS_PER_LINE = 7
CAPTION_MAX_SECONDS = 3.2
CAPTION_LINE_GAP_SECONDS = 0.08
MAX_WORD_DURATION_SECONDS = 1.2
MAX_WORD_GAP_SECONDS = 1.4
TRANSCRIPT_REPLACEMENTS = (
    (re.compile(r"\bLada\b", re.IGNORECASE), "Lauda"),
    (re.compile(r"\bNicky\b", re.IGNORECASE), "Niki"),
    (re.compile(r"\bdrive of the tyres\b", re.IGNORECASE), "dry tyres"),
    (re.compile(r"\bdrive of the tires\b", re.IGNORECASE), "dry tires"),
)


def transcribe(audio_path: Path | None, video_path: str, duration: float | None = None) -> tuple[str, list[CaptionSegment], str]:
    provider = settings.transcription_provider.lower()
    should_use_groq = provider in {"auto", "groq"} or (provider == "local" and bool(settings.groq_api_key))
    if should_use_groq and audio_path and audio_path.exists() and settings.groq_api_key:
        try:
            text, segments = _transcribe_groq(audio_path)
            text, segments = clean_transcript_outputs(text, segments)
            return text, segments or _coarse_segments(text, duration), "groq"
        except Exception as exc:
            text = f"{NO_TRANSCRIPT}: Groq transcription failed: {exc}"
            return text, [], "local_fallback"

    if audio_path and audio_path.exists():
        text = f"{NO_TRANSCRIPT}: Audio was extracted, but no transcription provider is enabled."
        return text, [], "local_fallback"
    text = f"{NO_TRANSCRIPT}: Could not extract audio from {Path(video_path).name}."
    return text, [], "local_fallback"


def _transcribe_groq(audio_path: Path) -> tuple[str, list[CaptionSegment]]:
    needs_chunking, _ = _needs_chunking(audio_path)
    if needs_chunking:
        return _transcribe_groq_chunked(audio_path)
    payload = _transcribe_groq_file(audio_path)
    text = str(payload.get("text", "")).strip()
    if not text:
        raise RuntimeError("Transcription response did not include text.")
    return text, _caption_segments_from_payload(payload)


def _transcribe_groq_chunked(audio_path: Path) -> tuple[str, list[CaptionSegment]]:
    duration = _probe_duration(audio_path)
    if not duration:
        payload = _transcribe_groq_file(audio_path)
        text = str(payload.get("text", "")).strip()
        return text, _caption_segments_from_payload(payload)

    temp_dir = audio_path.parent / f"{audio_path.stem}_chunks"
    temp_dir.mkdir(parents=True, exist_ok=True)
    chunk_count = math.ceil(duration / CHUNK_DURATION_SECONDS)
    texts: list[str] = []
    segments: list[CaptionSegment] = []
    try:
        for index in range(chunk_count):
            start = index * CHUNK_DURATION_SECONDS
            chunk_duration = min(CHUNK_DURATION_SECONDS, duration - start)
            chunk_path = temp_dir / f"chunk_{index:03d}.wav"
            if not _extract_audio_chunk(audio_path, start, chunk_duration, chunk_path):
                continue
            payload = _transcribe_groq_file(chunk_path)
            text = str(payload.get("text", "")).strip()
            if text:
                texts.append(text)
            segments.extend(_caption_segments_from_payload(payload, time_offset=start))
            chunk_path.unlink(missing_ok=True)
    finally:
        try:
            temp_dir.rmdir()
        except OSError:
            pass

    transcript = " ".join(texts).strip()
    if not transcript:
        raise RuntimeError("Transcription response did not include text.")
    return transcript, segments


def clean_transcript_outputs(text: str, segments: list[CaptionSegment]) -> tuple[str, list[CaptionSegment]]:
    cleaned_segments = [
        CaptionSegment(start=segment.start, end=segment.end, text=clean_caption_text(segment.text))
        for segment in segments
        if clean_caption_text(segment.text)
    ]
    return clean_caption_text(text), cleaned_segments


def clean_caption_text(text: str) -> str:
    clean = " ".join(text.split())
    if not clean:
        return ""
    clean = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", clean, flags=re.IGNORECASE)
    for pattern, replacement in TRANSCRIPT_REPLACEMENTS:
        clean = pattern.sub(replacement, clean)
    return clean.strip()


def _transcribe_groq_file(audio_path: Path) -> dict[str, Any]:
    request_data = [
        ("model", settings.groq_transcription_model),
        ("response_format", "verbose_json"),
        ("temperature", "0"),
        ("timestamp_granularities[]", "word"),
        ("timestamp_granularities[]", "segment"),
    ]
    if settings.transcription_language:
        request_data.append(("language", settings.transcription_language))

    with audio_path.open("rb") as audio_file:
        response = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            data=request_data,
            files={"file": (audio_path.name, audio_file, "audio/wav")},
            timeout=120,
        )
    response.raise_for_status()
    return response.json()


def _caption_segments_from_payload(payload: dict[str, Any], time_offset: float = 0.0) -> list[CaptionSegment]:
    words = _words_from_payload(payload, time_offset)
    if words:
        return _segments_from_words(words)
    return _segments_from_payload(payload, time_offset)


def _segments_from_payload(payload: dict[str, Any], time_offset: float = 0.0) -> list[CaptionSegment]:
    segments: list[CaptionSegment] = []
    for item in payload.get("segments") or []:
        try:
            raw_start = float(item.get("start", 0))
            raw_end = float(item.get("end", raw_start + 2))
            start = raw_start + time_offset
            end = raw_end + time_offset
            text = str(item.get("text", "")).strip()
        except (TypeError, ValueError):
            continue
        if text and end > start:
            segments.append(CaptionSegment(start=round(start, 3), end=round(end, 3), text=text))
    return segments


def _words_from_payload(payload: dict[str, Any], time_offset: float = 0.0) -> list[dict[str, float | str]]:
    words: list[dict[str, float | str]] = []
    for item in payload.get("words") or []:
        try:
            token = str(item.get("word", "")).strip()
            start = float(item.get("start", 0)) + time_offset
            end = float(item.get("end", start + 0.35)) + time_offset
        except (TypeError, ValueError):
            continue
        if token and end > start:
            words.append({"word": token, "start": round(start, 3), "end": round(end, 3)})
    return words


def _segments_from_words(words: list[dict[str, float | str]]) -> list[CaptionSegment]:
    segments: list[CaptionSegment] = []
    words = _normalize_word_timings(words)
    current: list[dict[str, float | str]] = []

    def flush() -> None:
        if not current:
            return
        start = float(current[0]["start"])
        end = float(current[-1]["end"])
        text = " ".join(str(item["word"]).strip() for item in current).strip()
        if text and end > start:
            segments.append(CaptionSegment(start=round(start, 3), end=round(end, 3), text=text))
        current.clear()

    for word in words:
        if current and float(word["start"]) - float(current[-1]["end"]) > MAX_WORD_GAP_SECONDS:
            flush()
        current.append(word)
        text = str(word["word"]).strip()
        line_start = float(current[0]["start"])
        line_end = float(word["end"])
        if (
            len(current) >= CAPTION_WORDS_PER_LINE
            or line_end - line_start >= CAPTION_MAX_SECONDS
            or text.endswith((".", "?", "!", ",", ";", ":"))
        ):
            flush()
    flush()
    return _separate_adjacent_segments(segments)


def _normalize_word_timings(words: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    normalized: list[dict[str, float | str]] = []
    for index, word in enumerate(words):
        start = float(word["start"])
        end = float(word["end"])
        if index + 1 < len(words):
            next_start = float(words[index + 1]["start"])
            if next_start > start:
                end = min(end, next_start - CAPTION_LINE_GAP_SECONDS)
        end = min(end, start + MAX_WORD_DURATION_SECONDS)
        if end <= start:
            end = start + 0.25
        normalized.append({"word": word["word"], "start": round(start, 3), "end": round(end, 3)})
    return normalized


def _separate_adjacent_segments(segments: list[CaptionSegment]) -> list[CaptionSegment]:
    if len(segments) < 2:
        return segments
    separated: list[CaptionSegment] = []
    for index, segment in enumerate(segments):
        end = segment.end
        if index + 1 < len(segments):
            next_start = segments[index + 1].start
            end = min(end, max(segment.start + 0.05, next_start - CAPTION_LINE_GAP_SECONDS))
        separated.append(CaptionSegment(start=segment.start, end=round(end, 3), text=segment.text))
    return separated


def _needs_chunking(audio_path: Path) -> tuple[bool, float]:
    size_mb = audio_path.stat().st_size / 1_000_000
    return size_mb > MAX_TRANSCRIPTION_FILE_MB, size_mb


def _probe_duration(path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def _extract_audio_chunk(source: Path, start: float, duration: float, destination: Path) -> bool:
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration:.3f}",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.returncode == 0 and destination.exists() and destination.stat().st_size > 0


def _coarse_segments(text: str, duration: float | None) -> list[CaptionSegment]:
    clean = " ".join(text.split())
    if not clean or clean.startswith(NO_TRANSCRIPT):
        return []
    words = clean.split()
    chunk_size = 9
    chunks = [" ".join(words[index : index + chunk_size]) for index in range(0, len(words), chunk_size)]
    if not chunks:
        return []
    total = max(float(duration or len(chunks) * 3), float(len(chunks)))
    step = total / len(chunks)
    segments: list[CaptionSegment] = []
    for index, chunk in enumerate(chunks):
        start = round(index * step, 2)
        end = round(min(total, (index + 1) * step), 2)
        segments.append(CaptionSegment(start=start, end=max(end, start + 0.5), text=chunk))
    return segments
