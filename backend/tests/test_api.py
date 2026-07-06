from fastapi.testclient import TestClient
from pathlib import Path
import pytest

from app.exports import export_job, job_submission_dict, job_submission_payload
from app.main import app
from app.models import CaptionSegment, CaptionStyle, Evaluation, JobRecord, StyleOutput
from app.config import settings
from app.llm_client import caption_llm
from app.pipeline import _evidence_pack, _generation_prompt
from app.sound_tags import add_sound_tags
from app.storage import save_job
from app.transcription import base as transcription_base
from app.transcription.base import _caption_segments_from_payload, clean_transcript_outputs
from app import video as video_helpers
from app.subtitles import write_ass


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["app"] == "ClipForger"


def test_empty_batch_is_rejected():
    response = client.post("/api/batches", files=[])
    assert response.status_code in {400, 422}


def test_caption_track_exports_srt_and_vtt():
    job = JobRecord(
        job_id="job-1",
        filename="clip.mp4",
        video_path="clip.mp4",
        caption_track=[
            CaptionSegment(start=0, end=1.25, text="Hello there"),
            CaptionSegment(start=1.25, end=3.5, text="Caption track only"),
        ],
    )

    _, srt = export_job(job, "srt")
    _, vtt = export_job(job, "vtt")

    assert "00:00:00,000 --> 00:00:01,250" in srt
    assert "Hello there" in srt
    assert "WEBVTT" in vtt
    assert "00:00:01.250 --> 00:00:03.500" in vtt


def test_burned_caption_style_uses_sans_serif_font(tmp_path):
    subtitle_path = write_ass([CaptionSegment(start=0, end=1, text="Readable caption")], tmp_path / "clip.ass")
    content = subtitle_path.read_text(encoding="utf-8")

    assert "Style: Default,DejaVu Sans," in content
    assert "Arial Bold" not in content


def test_submission_json_separates_caption_track_and_style_outputs():
    job = JobRecord(
        job_id="job-2",
        filename="clip.mp4",
        video_path="clip.mp4",
        caption_track=[CaptionSegment(start=0, end=2, text="Literal subtitle")],
        style_outputs=[
            StyleOutput(
                style=CaptionStyle.formal,
                styled_caption="A formal caption.",
                summary="A formal summary.",
                tone_notes="Formal",
                evaluation=Evaluation(accuracy=0.9, tone_match=0.8, hallucination_risk="low", notes="ok"),
            )
        ],
    )

    payload = job_submission_dict(job)

    assert payload["caption_track"][0]["text"] == "Literal subtitle"
    assert payload["style_outputs"]["formal"]["styled_caption"] == "A formal caption."
    assert payload["style_outputs"]["formal"]["summary"] == "A formal summary."


def test_submission_payload_contains_only_track_two_outputs():
    job = JobRecord(
        job_id="job-3",
        filename="clip.mp4",
        video_path="clip.mp4",
        caption_track=[CaptionSegment(start=0, end=2, text="Literal subtitle")],
        transcript_provider="internal",
        generation_provider="internal",
        style_outputs=[
            StyleOutput(
                style=CaptionStyle.formal,
                styled_caption="A formal caption.",
                summary="A formal summary.",
                tone_notes="Formal",
                evaluation=Evaluation(accuracy=0.9, tone_match=0.8, hallucination_risk="low", notes="ok"),
            )
        ],
    )

    payload = job_submission_payload(job)
    media_type, exported = export_job(job, "submission")

    assert media_type == "application/json"
    assert payload == {"clip_id": "clip.mp4", "outputs": {"formal": {"caption": "A formal caption.", "summary": "A formal summary."}}}
    assert "caption_track" not in exported
    assert "generation_provider" not in exported


def test_style_output_patch_persists_to_submission_export(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_dir", tmp_path)
    job = JobRecord(
        job_id="editable-job",
        filename="clip.mp4",
        video_path="clip.mp4",
        style_outputs=[
            StyleOutput(
                style=CaptionStyle.sarcastic,
                styled_caption="Old caption.",
                summary="Old summary.",
                tone_notes="Sarcastic",
                evaluation=Evaluation(accuracy=0.9, tone_match=0.8, hallucination_risk="low", notes="ok"),
            )
        ],
    )
    save_job(job)

    response = client.patch(
        "/api/jobs/editable-job/style-outputs",
        json={
            "style": "sarcastic",
            "styled_caption": "Because solving crime now requires a boy-band audition.",
            "summary": "A detective has lineup suspects sing one by one so the witness can identify the voice.",
        },
    )
    exported = client.get("/api/jobs/editable-job/export?format=submission")

    assert response.status_code == 200
    assert exported.status_code == 200
    assert exported.json()["outputs"]["sarcastic"] == {
        "caption": "Because solving crime now requires a boy-band audition.",
        "summary": "A detective has lineup suspects sing one by one so the witness can identify the voice.",
    }


def test_word_timestamps_drive_caption_track():
    payload = {
        "words": [
            {"word": "hello", "start": 1.0, "end": 1.2},
            {"word": "there", "start": 1.25, "end": 1.5},
            {"word": "friend.", "start": 1.55, "end": 1.9},
        ],
        "segments": [{"text": "hello there friend.", "start": 1.0, "end": 3.0}],
    }

    segments = _caption_segments_from_payload(payload, time_offset=10)

    assert segments == [CaptionSegment(start=11.0, end=11.9, text="hello there friend.")]


def test_adjacent_word_caption_lines_do_not_overlap():
    payload = {
        "words": [
            {"word": "You're", "start": 0.0, "end": 0.35},
            {"word": "disgusting.", "start": 0.36, "end": 0.8},
            {"word": "my", "start": 0.8, "end": 1.0},
            {"word": "God.", "start": 1.02, "end": 1.3},
        ]
    }

    segments = _caption_segments_from_payload(payload)

    assert segments[0].text == "You're disgusting."
    assert segments[1].text == "my God."
    assert segments[0].end < segments[1].start


def test_malformed_long_word_timestamp_is_clamped():
    payload = {
        "words": [
            {"word": "The", "start": 0.02, "end": 0.3},
            {"word": "I'm", "start": 0.32, "end": 40.72},
            {"word": "very", "start": 40.8, "end": 41.1},
            {"word": "aggressive", "start": 41.2, "end": 41.8},
        ]
    }

    segments = _caption_segments_from_payload(payload)

    assert segments[0].text == "The I'm"
    assert segments[0].end < 2
    assert segments[1].start == 40.8


def test_transcription_language_is_sent_to_groq(monkeypatch):
    audio_path = Path(__file__).parent / "fake_clip.wav"
    audio_path.write_bytes(b"fake")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"text": "hello", "words": [], "segments": []}

    def fake_post(*args, **kwargs):
        captured["data"] = kwargs["data"]
        return FakeResponse()

    monkeypatch.setattr(settings, "transcription_language", "en")
    monkeypatch.setattr(transcription_base.requests, "post", fake_post)

    try:
        transcription_base._transcribe_groq_file(audio_path)
    finally:
        audio_path.unlink(missing_ok=True)

    assert ("language", "en") in captured["data"]


def test_transcript_cleanup_fixes_repeats_and_racing_names():
    text = "The The Lada has the lead. Where's Nicky? He chose the drive of the tyres."
    segments = [
        CaptionSegment(start=0, end=1, text="The The Lada has the lead."),
        CaptionSegment(start=1, end=2, text="Where's Nicky?"),
    ]

    cleaned_text, cleaned_segments = clean_transcript_outputs(text, segments)

    assert cleaned_text == "The Lauda has the lead. Where's Niki? He chose the dry tyres."
    assert cleaned_segments[0].text == "The Lauda has the lead."
    assert cleaned_segments[1].text == "Where's Niki?"


def test_sound_tags_are_inserted_for_crash_context_gaps():
    segments = [
        CaptionSegment(start=0.5, end=1.2, text="Go now!"),
        CaptionSegment(start=6.0, end=7.0, text="Are you okay?"),
    ]

    enhanced = add_sound_tags(segments, duration=8.0, visual_summary="A crash with flames and panic on the track.")

    assert any(segment.text == "[crashing sound]" for segment in enhanced)
    assert enhanced[0].text == "Go now!"


def test_chunk_extraction_uses_uncompressed_wav(monkeypatch, tmp_path):
    source = tmp_path / "source.wav"
    destination = tmp_path / "chunk.wav"
    source.write_bytes(b"fake")
    captured = {}

    class FakeResult:
        returncode = 0

    def fake_run(command, *args, **kwargs):
        captured["command"] = command
        destination.write_bytes(b"wav")
        return FakeResult()

    monkeypatch.setattr(transcription_base.subprocess, "run", fake_run)

    assert transcription_base._extract_audio_chunk(source, 0, 30, destination)
    assert "pcm_s16le" in captured["command"]
    assert "64k" not in captured["command"]
    assert destination.suffix == ".wav"


def test_gemma_routes_before_regular_fireworks_and_groq(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "auto")
    monkeypatch.setattr(settings, "fireworks_api_key", "fw-test")
    monkeypatch.setattr(settings, "fireworks_gemma_model", "accounts/fireworks/models/gemma-test")
    monkeypatch.setattr(settings, "groq_api_key", "gsk-test")

    assert caption_llm._provider_order() == ["fireworks_gemma", "fireworks", "groq"]


def test_explicit_gemma_provider_requires_gemma_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "gemma")
    monkeypatch.setattr(settings, "fireworks_api_key", "fw-test")
    monkeypatch.setattr(settings, "fireworks_gemma_model", "")

    assert caption_llm._provider_order() == []


def test_explicit_gemma_provider_fails_instead_of_falling_back(monkeypatch):
    def fake_provider(provider, messages):
        raise RuntimeError("404 model unavailable")

    monkeypatch.setattr(settings, "llm_provider", "gemma")
    monkeypatch.setattr(settings, "fireworks_api_key", "fw-test")
    monkeypatch.setattr(settings, "fireworks_gemma_model", "accounts/fireworks/models/gemma-test")
    monkeypatch.setattr(caption_llm, "_complete_with_provider", fake_provider)

    with pytest.raises(RuntimeError, match="Required LLM provider failed"):
        caption_llm.complete_json([], {})


def test_provider_errors_are_kept_when_fallback_succeeds(monkeypatch):
    calls = []

    def fake_provider(provider, messages):
        calls.append(provider)
        if provider == "fireworks_gemma":
            raise RuntimeError("404 model unavailable")
        return '{"formal": {}, "sarcastic": {}, "humorous_tech": {}, "humorous_non_tech": {}}'

    monkeypatch.setattr(settings, "llm_provider", "auto")
    monkeypatch.setattr(settings, "fireworks_api_key", "fw-test")
    monkeypatch.setattr(settings, "fireworks_gemma_model", "accounts/fireworks/models/gemma-test")
    monkeypatch.setattr(settings, "groq_api_key", "gsk-test")
    monkeypatch.setattr(caption_llm, "_complete_with_provider", fake_provider)

    _, provider = caption_llm.complete_json([], {})

    assert calls == ["fireworks_gemma", "fireworks"]
    assert provider == "fireworks"
    assert caption_llm.last_provider_errors == ["fireworks_gemma: 404 model unavailable"]


def test_provider_diagnostics_include_skipped_fireworks(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "auto")
    monkeypatch.setattr(settings, "fireworks_api_key", "")
    monkeypatch.setattr(settings, "fireworks_gemma_model", "accounts/fireworks/models/gemma-test")
    monkeypatch.setattr(settings, "groq_api_key", "gsk-test")

    assert "fireworks_gemma skipped: FIREWORKS_API_KEY is not configured" in caption_llm._configuration_notes()
    assert "fireworks skipped: FIREWORKS_API_KEY is not configured" in caption_llm._configuration_notes()


def test_evidence_pack_prefers_clean_timed_lines():
    evidence = _evidence_pack(
        "Full transcript",
        [
            CaptionSegment(start=0, end=1, text="[inaudible]"),
            CaptionSegment(start=1, end=2, text="Go!"),
            CaptionSegment(start=2, end=4, text="James Hunt is a long way up the road."),
        ],
        "A race car scene with pit crews and fire.",
    )

    assert "James Hunt is a long way up the road." in evidence
    assert "[inaudible]" not in evidence
    assert "Go!" in evidence
    assert "A race car scene" in evidence


def test_generation_prompt_requests_fuller_outputs():
    prompt = _generation_prompt("transcript", "visual", "evidence")
    combined = " ".join(message["content"] for message in prompt)

    assert "36-50 words" in combined
    assert "80-110 words" in combined
    assert "3-4 sentences" in combined
    assert "mean-but-not-hurtful" in combined
    assert "mocks the situation rather than a person's body, pain, identity, or trauma" in combined
    assert "may lightly tease a person's choices or overreaction without being cruel" in combined
    assert "Keep rhetorical devices mutually exclusive" in combined
    assert "sarcastic uses irony and situational mockery with no tech metaphors" in combined


def test_video_normalization_resets_timestamps(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake")
    captured = {}

    def fake_run(command, *args, **kwargs):
        captured["command"] = command
        output = Path(command[-1])
        output.write_bytes(b"normalized")

    monkeypatch.setattr(video_helpers.subprocess, "run", fake_run)

    result = video_helpers.normalize_video(str(source), tmp_path, "job-123")

    assert result is not None
    assert result.name == "job-123_normalized.mp4"
    command_text = " ".join(captured["command"])
    assert "setpts=PTS-STARTPTS" in command_text
    assert "asetpts=PTS-STARTPTS" in command_text
