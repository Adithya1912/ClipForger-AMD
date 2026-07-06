from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class CaptionStyle(str, Enum):
    formal = "formal"
    sarcastic = "sarcastic"
    humorous_tech = "humorous_tech"
    humorous_non_tech = "humorous_non_tech"


class Evaluation(BaseModel):
    accuracy: float = Field(ge=0, le=1)
    tone_match: float = Field(ge=0, le=1)
    hallucination_risk: str
    notes: str


class CaptionSegment(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str


class StyleOutput(BaseModel):
    style: CaptionStyle
    styled_caption: str
    summary: str
    tone_notes: str = ""
    confidence: float = Field(default=0.75, ge=0, le=1)
    evaluation: Evaluation


class JobRecord(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.queued
    progress: int = Field(default=0, ge=0, le=100)
    message: str = "Queued"
    filename: str
    video_path: str
    duration_seconds: float | None = None
    transcript: str | None = None
    caption_track: list[CaptionSegment] = Field(default_factory=list)
    transcript_provider: str | None = None
    visual_summary: str | None = None
    visual_provider: str | None = None
    generation_provider: str | None = None
    generation_diagnostics: list[str] = Field(default_factory=list)
    captioned_video_path: str | None = None
    base_summary: str | None = None
    style_outputs: list[StyleOutput] = Field(default_factory=list)
    error: str | None = None


class BatchRecord(BaseModel):
    batch_id: str
    status: JobStatus = JobStatus.queued
    progress: int = Field(default=0, ge=0, le=100)
    message: str = "Queued"
    job_ids: list[str] = Field(default_factory=list)
    error: str | None = None


class SummaryPatch(BaseModel):
    style: CaptionStyle
    styled_caption: str | None = None
    summary: str | None = None
