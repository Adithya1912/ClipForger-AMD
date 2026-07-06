from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from .config import settings
from .models import BatchRecord, JobRecord


def ensure_storage() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    (settings.storage_dir / "uploads").mkdir(exist_ok=True)
    (settings.storage_dir / "jobs").mkdir(exist_ok=True)
    (settings.storage_dir / "batches").mkdir(exist_ok=True)
    (settings.storage_dir / "captioned").mkdir(exist_ok=True)


def job_path(job_id: str) -> Path:
    return settings.storage_dir / "jobs" / f"{job_id}.json"


def batch_path(batch_id: str) -> Path:
    return settings.storage_dir / "batches" / f"{batch_id}.json"


def save_job(job: JobRecord) -> JobRecord:
    ensure_storage()
    job_path(job.job_id).write_text(job.model_dump_json(indent=2), encoding="utf-8")
    return job


def load_job(job_id: str) -> JobRecord:
    data = json.loads(job_path(job_id).read_text(encoding="utf-8"))
    return JobRecord(**data)


def save_batch(batch: BatchRecord) -> BatchRecord:
    ensure_storage()
    batch_path(batch.batch_id).write_text(batch.model_dump_json(indent=2), encoding="utf-8")
    return batch


def load_batch(batch_id: str) -> BatchRecord:
    data = json.loads(batch_path(batch_id).read_text(encoding="utf-8"))
    return BatchRecord(**data)


def list_batches() -> list[BatchRecord]:
    ensure_storage()
    batches = [BatchRecord(**json.loads(path.read_text(encoding="utf-8"))) for path in (settings.storage_dir / "batches").glob("*.json")]
    return sorted(batches, key=lambda item: batch_path(item.batch_id).stat().st_mtime, reverse=True)


def list_jobs() -> list[JobRecord]:
    ensure_storage()
    jobs = [JobRecord(**json.loads(path.read_text(encoding="utf-8"))) for path in (settings.storage_dir / "jobs").glob("*.json")]
    return sorted(jobs, key=lambda item: job_path(item.job_id).stat().st_mtime, reverse=True)


def store_upload(file: UploadFile) -> JobRecord:
    ensure_storage()
    suffix = Path(file.filename or "clip.mp4").suffix or ".mp4"
    job_id = str(uuid4())
    video_path = settings.storage_dir / "uploads" / f"{job_id}{suffix}"
    with video_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return save_job(JobRecord(job_id=job_id, filename=file.filename or video_path.name, video_path=str(video_path)))


def store_batch_upload(files: list[UploadFile]) -> BatchRecord:
    ensure_storage()
    batch = BatchRecord(batch_id=str(uuid4()), message=f"Queued {len(files)} clips")
    for file in files:
        job = store_upload(file)
        batch.job_ids.append(job.job_id)
    return save_batch(batch)
