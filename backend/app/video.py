from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_duration(path: str) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return None


def normalize_video(video_path: str, output_dir: Path, job_id: str) -> Path | None:
    """Rebuild uploaded media with zero-based timestamps before ASR/rendering."""
    source = Path(video_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = output_dir / f"{job_id}_normalized.mp4"
    command = [
        "ffmpeg",
        "-y",
        "-fflags",
        "+genpts",
        "-i",
        str(source),
        "-filter_complex",
        "[0:v]setpts=PTS-STARTPTS[v];[0:a]asetpts=PTS-STARTPTS[a]",
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(normalized_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except Exception:
        video_only_command = [
            "ffmpeg",
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            str(source),
            "-vf",
            "setpts=PTS-STARTPTS",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-movflags",
            "+faststart",
            str(normalized_path),
        ]
        try:
            subprocess.run(video_only_command, check=True, capture_output=True, text=True)
        except Exception:
            return None
    return normalized_path if normalized_path.exists() and normalized_path.stat().st_size > 0 else None


def extract_audio(video_path: str, output_dir: Path) -> Path | None:
    audio_path = output_dir / f"{Path(video_path).stem}.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", str(audio_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return audio_path
    except Exception:
        return None


def extract_keyframes(video_path: str, output_dir: Path, duration: float | None, count: int = 3) -> list[Path]:
    frames_dir = output_dir / f"{Path(video_path).stem}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    if duration and duration > 0:
        timestamps = [duration * fraction for fraction in (0.2, 0.5, 0.8)][:count]
    else:
        timestamps = [2, 8, 14][:count]

    frames: list[Path] = []
    for index, timestamp in enumerate(timestamps, start=1):
        frame_path = frames_dir / f"frame_{index:02d}.jpg"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{timestamp:.2f}",
                    "-i",
                    video_path,
                    "-frames:v",
                    "1",
                    "-q:v",
                    "3",
                    str(frame_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            if frame_path.exists() and frame_path.stat().st_size > 0:
                frames.append(frame_path)
        except Exception:
            continue
    return frames
