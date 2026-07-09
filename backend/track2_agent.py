from __future__ import annotations

import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.caption_styles import STYLE_GUIDE, STYLE_SYSTEM_PROMPTS, STYLE_FEW_SHOT
from app.config import settings
from app.llm_client import caption_llm
from app.models import CaptionSegment, CaptionStyle
from app.transcription import NO_TRANSCRIPT, transcribe
from app.video import extract_audio, extract_keyframes, normalize_video, probe_duration
from app.vision import NO_VISUAL_CONTEXT, describe_frames


INPUT_PATH = Path("/input/tasks.json")
OUTPUT_PATH = Path("/output/results.json")
WORK_DIR = Path("/tmp/clipforger-track2")
STYLE_KEYS = ("formal", "sarcastic", "humorous_tech", "humorous_non_tech")


def main() -> int:
    try:
        tasks = _read_tasks(INPUT_PATH)
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        results: list[dict] = [None] * len(tasks)
        with ThreadPoolExecutor(max_workers=min(3, len(tasks))) as ex:
            futures = {ex.submit(_process_task, task): idx for idx, task in enumerate(tasks)}
            for future in as_completed(futures):
                idx = futures[future]
                results[idx] = future.result()
        elapsed = time.time() - t0
        print(f"Processed {len(tasks)} clips in {elapsed:.0f}s", file=sys.stderr)
        OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps({"error": str(exc)}, ensure_ascii=False), encoding="utf-8")
        print(f"ClipForger-AMD Track 2 agent failed: {exc}", file=sys.stderr)
        return 1


def _read_tasks(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("/input/tasks.json must contain a JSON array")
    return payload


def _process_task(task: dict) -> dict:
    task_id = str(task.get("task_id") or uuid.uuid4())
    video_url = str(task.get("video_url") or "").strip()
    if not video_url:
        raise ValueError(f"Task {task_id} is missing video_url")
    requested_styles = _requested_styles(task)

    task_dir = WORK_DIR / _safe_name(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    video_path = _download_video(video_url, task_dir)

    duration = probe_duration(str(video_path))
    normalized = normalize_video(str(video_path), task_dir, "source")
    if normalized:
        video_path = normalized
        duration = probe_duration(str(video_path)) or duration

    audio_path = extract_audio(str(video_path), task_dir)
    transcript, caption_track, _transcript_provider = transcribe(audio_path, str(video_path), duration)
    frames = extract_keyframes(str(video_path), task_dir, duration)
    visual_summary, _visual_provider = describe_frames(frames)

    captions = _generate_captions(requested_styles, transcript, caption_track, visual_summary)
    return {"task_id": task_id, "captions": captions}


def _requested_styles(task: dict) -> list[str]:
    raw = task.get("styles") or list(STYLE_KEYS)
    if not isinstance(raw, list):
        raise ValueError("styles must be a list when provided")
    styles = [str(style).strip() for style in raw if str(style).strip()]
    invalid = [style for style in styles if style not in STYLE_KEYS]
    if invalid:
        raise ValueError(f"Unsupported styles requested: {', '.join(invalid)}")
    return styles or list(STYLE_KEYS)


def _download_video(video_url: str, task_dir: Path) -> Path:
    parsed = urlparse(video_url)
    suffix = Path(parsed.path).suffix or ".mp4"
    destination = task_dir / f"input{suffix}"
    with requests.get(video_url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    if destination.stat().st_size == 0:
        raise RuntimeError(f"Downloaded empty video from {video_url}")
    return destination


def _generate_captions(
    requested_styles: list[str],
    transcript: str,
    caption_track: list[CaptionSegment],
    visual_summary: str,
) -> dict[str, str]:
    fallback = {style: _fallback_caption(style, transcript, visual_summary) for style in requested_styles}
    evidence = _evidence_pack(transcript, caption_track, visual_summary)
    transcript_context = (
        "Transcript is unavailable."
        if transcript.startswith(NO_TRANSCRIPT)
        else transcript
    )
    visual_context = (
        "Visual context unavailable."
        if not visual_summary or visual_summary.startswith(NO_VISUAL_CONTEXT)
        else visual_summary
    )

    captions: dict[str, str] = {}
    for style_key in requested_styles:
        try:
            style = CaptionStyle(style_key)
            system_prompt = STYLE_SYSTEM_PROMPTS[style]
            few_shot = STYLE_FEW_SHOT.get(style, [])
            messages = [
                {"role": "system", "content": system_prompt + (
                    "\n\nReturn strict JSON only with key: styled_caption. "
                    "The value must be one concise caption string (24-40 words), not an object. "
                    "Stay grounded in the evidence. Do not mention transcripts, keyframes, or internal details."
                )},
            ]
            for shot in few_shot:
                messages.append(shot)
            messages.append({
                "role": "user",
                "content": (
                    f"Evidence pack:\n{evidence}\n\n"
                    f"Generate a {style_key} caption."
                ),
            })
            raw, _provider = caption_llm.complete_json(messages, {"styled_caption": fallback[style_key]})
            value = raw.get("styled_caption") or raw.get(style_key) or fallback[style_key]
            caption = " ".join(str(value).split())
            captions[style_key] = caption or fallback[style_key]
        except Exception:
            captions[style_key] = fallback[style_key]

    return captions


def _evidence_pack(transcript: str, caption_track: list[CaptionSegment], visual_summary: str) -> str:
    parts: list[str] = []
    if transcript and not transcript.startswith(NO_TRANSCRIPT):
        timed_lines = []
        for segment in caption_track[:20]:
            text = " ".join(segment.text.split())
            if text:
                timed_lines.append(f"{segment.start:.1f}-{segment.end:.1f}s: {text}")
        parts.append("Transcript:\n" + ("\n".join(timed_lines) if timed_lines else transcript))
    else:
        parts.append("Transcript unavailable.")

    if visual_summary and not visual_summary.startswith(NO_VISUAL_CONTEXT):
        parts.append("Visual context:\n" + visual_summary)
    else:
        parts.append("Visual context unavailable.")
    return "\n\n".join(parts)


def _fallback_caption(style: str, transcript: str, visual_summary: str) -> str:
    base = _plain_context(transcript, visual_summary)
    templates = {
        "formal": f"A concise factual caption describes the video's visible scene and main action: {base}",
        "sarcastic": f"Apparently this scene has chosen drama as its main feature, with the visible action still grounded in what happens: {base}",
        "humorous_tech": f"Runtime note: the clip processes a real-world scene with unpredictable human inputs and one very visible action queue: {base}",
        "humorous_non_tech": f"This clip turns an ordinary moment into something more amusing, while still following the visible action closely: {base}",
    }
    return " ".join(templates[style].split())[:420]


def _plain_context(transcript: str, visual_summary: str) -> str:
    if transcript and not transcript.startswith(NO_TRANSCRIPT):
        return transcript[:260]
    if visual_summary and not visual_summary.startswith(NO_VISUAL_CONTEXT):
        return visual_summary[:260]
    return "the video needs cautious description because only limited evidence is available."


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)[:80] or "task"


if __name__ == "__main__":
    raise SystemExit(main())
