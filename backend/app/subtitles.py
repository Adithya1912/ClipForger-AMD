from __future__ import annotations

import html
import subprocess
from pathlib import Path

from .models import CaptionSegment


def format_srt(segments: list[CaptionSegment]) -> str:
    blocks = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(f"{index}\n{_srt_time(segment.start)} --> {_srt_time(segment.end)}\n{segment.text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def format_vtt(segments: list[CaptionSegment]) -> str:
    blocks = ["WEBVTT\n"]
    for segment in segments:
        blocks.append(f"{_vtt_time(segment.start)} --> {_vtt_time(segment.end)}\n{segment.text}\n")
    return "\n".join(blocks)


def format_txt(segments: list[CaptionSegment]) -> str:
    return "\n".join(f"[{_plain_time(segment.start)}] {segment.text}" for segment in segments) + ("\n" if segments else "")


def write_ass(segments: list[CaptionSegment], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = """[Script Info]
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,52,&H00FFFFFF,&H0000FFFF,&H00000000,&H70000000,1,0,0,0,100,100,0,0,1,4,1.5,2,90,90,86,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [
        f"Dialogue: 0,{_ass_time(segment.start)},{_ass_time(segment.end)},Default,,0,0,0,,{{\\an2}}{_ass_text(segment.text)}"
        for segment in segments
    ]
    destination.write_text(header + "\n".join(lines), encoding="utf-8")
    return destination


def render_captioned_video(source: str, segments: list[CaptionSegment], output_dir: Path, job_id: str) -> Path | None:
    if not segments:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    subtitle_path = write_ass(segments, output_dir / f"{job_id}.ass")
    output_path = output_dir / f"{job_id}_captioned.mp4"
    subtitle_value = str(subtitle_path.resolve()).replace("\\", "/").replace(":", r"\:")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        source,
        "-filter_complex",
        f"[0:v]setpts=PTS-STARTPTS,subtitles='{subtitle_value}'[v];[0:a]asetpts=PTS-STARTPTS[a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except Exception:
        silent_command = [
            "ffmpeg",
            "-y",
            "-i",
            source,
            "-vf",
            f"setpts=PTS-STARTPTS,subtitles='{subtitle_value}'",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        try:
            subprocess.run(silent_command, check=True, capture_output=True, text=True)
        except Exception:
            return None
    return output_path if output_path.exists() and output_path.stat().st_size > 0 else None


def _srt_time(value: float) -> str:
    hours, minutes, seconds, millis = _parts(value)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _vtt_time(value: float) -> str:
    hours, minutes, seconds, millis = _parts(value)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def _ass_time(value: float) -> str:
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = value % 60
    return f"{hours}:{minutes:02d}:{seconds:05.2f}"


def _plain_time(value: float) -> str:
    minutes = int(value // 60)
    seconds = int(value % 60)
    return f"{minutes:02d}:{seconds:02d}"


def _parts(value: float) -> tuple[int, int, int, int]:
    clamped = max(0.0, value)
    hours = int(clamped // 3600)
    minutes = int((clamped % 3600) // 60)
    seconds = int(clamped % 60)
    millis = int(round((clamped - int(clamped)) * 1000))
    if millis == 1000:
        seconds += 1
        millis = 0
    return hours, minutes, seconds, millis


def _ass_text(value: str) -> str:
    return html.escape(value, quote=False).replace("\n", r"\N")
