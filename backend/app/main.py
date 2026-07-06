from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pathlib import Path

from .exports import export_batch, export_job
from .models import SummaryPatch
from .pipeline import generate_for_batch, generate_for_job
from .storage import list_batches, list_jobs, load_batch, load_job, save_job, store_batch_upload, store_upload

app = FastAPI(title="ClipForger", version="0.1.0", description="ClipForger API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "ClipForger"}


@app.post("/api/videos")
def upload_video(file: UploadFile = File(...)):
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(status_code=400, detail="Upload a video file.")
    return store_upload(file)


@app.post("/api/batches")
def upload_batch(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one video file.")
    for file in files:
        if not (file.content_type or "").startswith("video/"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a video file.")
    return store_batch_upload(files)


@app.get("/api/jobs")
def jobs():
    return list_jobs()


@app.get("/api/batches")
def batches():
    return list_batches()


@app.get("/api/batches/{batch_id}")
def get_batch(batch_id: str):
    try:
        batch = load_batch(batch_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Batch not found") from None
    jobs = [load_job(job_id) for job_id in batch.job_ids]
    return {"batch": batch, "jobs": jobs}


@app.post("/api/batches/{batch_id}/generate")
def generate_batch(batch_id: str, background_tasks: BackgroundTasks):
    try:
        load_batch(batch_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Batch not found") from None
    background_tasks.add_task(generate_for_batch, batch_id)
    return {"batch_id": batch_id, "status": "processing"}


@app.get("/api/batches/{batch_id}/export")
def export_batch_results(batch_id: str, format: str = "jsonl"):
    try:
        batch = load_batch(batch_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Batch not found") from None
    media_type, content = export_batch(batch, format)
    return Response(content=content, media_type=media_type)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    try:
        return load_job(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found") from None


@app.post("/api/jobs/{job_id}/generate")
def generate(job_id: str, background_tasks: BackgroundTasks):
    try:
        load_job(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found") from None
    background_tasks.add_task(generate_for_job, job_id)
    return {"job_id": job_id, "status": "processing"}


@app.get("/api/jobs/{job_id}/results")
def results(job_id: str):
    return get_job(job_id)


@app.patch("/api/jobs/{job_id}/captions")
def update_summary_legacy(job_id: str, patch: SummaryPatch):
    return update_summary(job_id, patch)


@app.patch("/api/jobs/{job_id}/style-outputs")
def update_summary(job_id: str, patch: SummaryPatch):
    job = load_job(job_id)
    for index, output in enumerate(job.style_outputs):
        if output.style == patch.style:
            if patch.styled_caption is not None:
                output.styled_caption = patch.styled_caption
            if patch.summary is not None:
                output.summary = patch.summary
            job.style_outputs[index] = output
            return save_job(job)
    raise HTTPException(status_code=404, detail="Style output not found")


@app.patch("/api/jobs/{job_id}/summaries")
def update_summary_compat(job_id: str, patch: SummaryPatch):
    return update_summary(job_id, patch)


@app.get("/api/jobs/{job_id}/captioned-video")
def captioned_video(job_id: str):
    job = load_job(job_id)
    if not job.captioned_video_path:
        raise HTTPException(status_code=404, detail="Captioned video is not available")
    path = Path(job.captioned_video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Captioned video file is missing")
    return FileResponse(path, media_type="video/mp4", filename=f"{Path(job.filename).stem}_captioned.mp4")


@app.get("/api/jobs/{job_id}/export")
def export(job_id: str, format: str = "json"):
    job = load_job(job_id)
    media_type, content = export_job(job, format)
    return Response(content=content, media_type=media_type)
