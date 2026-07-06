from __future__ import annotations

import json

from .caption_styles import STYLE_LABELS
from .models import BatchRecord, JobRecord
from .storage import load_job
from .subtitles import format_srt, format_txt, format_vtt


def export_job(job: JobRecord, export_format: str) -> tuple[str, str]:
    if export_format == "submission":
        return "application/json", json.dumps(job_submission_payload(job), indent=2)

    if export_format == "json":
        return "application/json", job.model_dump_json(indent=2)

    if export_format == "srt":
        return "application/x-subrip", format_srt(job.caption_track)

    if export_format == "vtt":
        return "text/vtt", format_vtt(job.caption_track)

    if export_format == "txt":
        return "text/plain", format_txt(job.caption_track)

    return "text/plain", "\n\n".join(
        f"{STYLE_LABELS[item.style]}\nStyled caption: {item.styled_caption}\nSummary: {item.summary}"
        for item in job.style_outputs
    )


def job_submission_dict(job: JobRecord) -> dict:
    return {
        "clip_id": job.filename,
        "job_id": job.job_id,
        "duration_seconds": job.duration_seconds,
        "providers": {
            "transcript": job.transcript_provider,
            "vision": job.visual_provider,
            "generation": job.generation_provider,
        },
        "caption_track": [segment.model_dump() for segment in job.caption_track],
        "captioned_video_path": job.captioned_video_path,
        "style_outputs": {
            output.style.value: {
                "styled_caption": output.styled_caption,
                "summary": output.summary,
                "confidence": output.confidence,
                "evaluation": output.evaluation.model_dump(),
            }
            for output in job.style_outputs
        },
    }


def job_submission_payload(job: JobRecord) -> dict:
    return {
        "clip_id": job.filename,
        "outputs": {
            output.style.value: {
                "caption": output.styled_caption,
                "summary": output.summary,
            }
            for output in job.style_outputs
        },
    }


def export_batch(batch: BatchRecord, export_format: str) -> tuple[str, str]:
    jobs = [load_job(job_id) for job_id in batch.job_ids]
    if export_format == "submission":
        return "application/json", json.dumps({"clips": [job_submission_payload(job) for job in jobs]}, indent=2)
    rows = [job_submission_dict(job) for job in jobs]
    if export_format == "jsonl":
        return "application/x-ndjson", "\n".join(json.dumps(row) for row in rows) + "\n"
    return "application/json", json.dumps({"batch_id": batch.batch_id, "status": batch.status, "clips": rows}, indent=2)
