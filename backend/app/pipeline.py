from __future__ import annotations

from .caption_styles import STYLE_GUIDE
from .config import settings
from .evaluator import heuristic_evaluation
from .llm_client import caption_llm
from .models import CaptionStyle, JobStatus, StyleOutput
from .sound_tags import add_sound_tags
from .storage import load_batch, load_job, save_batch, save_job
from .subtitles import render_captioned_video
from .transcription import NO_TRANSCRIPT, transcribe
from .video import extract_audio, extract_keyframes, normalize_video, probe_duration
from .vision import NO_VISUAL_CONTEXT, describe_frames


def _evidence_pack(transcript: str | None, caption_track: list, visual_summary: str | None) -> str:
    parts: list[str] = []
    if transcript and not transcript.startswith(NO_TRANSCRIPT):
        clean_lines = []
        for segment in caption_track:
            text = " ".join(str(segment.text).split())
            if not text or text.startswith("["):
                continue
            if len(text.split()) < 3 and not text.endswith(("!", "?")):
                continue
            clean_lines.append(f"{segment.start:.1f}-{segment.end:.1f}s: {text}")
            if len(clean_lines) >= 18:
                break
        if clean_lines:
            parts.append("Most reliable timed transcript evidence:\n" + "\n".join(clean_lines))
        else:
            parts.append("Transcript evidence:\n" + transcript)
    else:
        parts.append("Transcript evidence unavailable.")

    if visual_summary and not visual_summary.startswith(NO_VISUAL_CONTEXT):
        parts.append("Visual evidence:\n" + visual_summary)
    else:
        parts.append("Visual evidence unavailable.")
    return "\n\n".join(parts)


def _generation_prompt(transcript_context: str, visual_context: str, evidence_context: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Return strict JSON only. Generate a video summary for each required style. "
                "Also generate one styled caption for each style; this is a judged caption, not the subtitle track. "
                "Each styled_caption should be 36-50 words, substantial enough to feel like a complete judged caption. "
                "Each summary should be 80-110 words in 3-4 sentences describing what happens in the video in that style. "
                "Stay accurate to the transcript and visual context. Do not invent facts. "
                "Treat ASR as imperfect evidence: prefer named people, visible actions, and repeated clear phrases over garbled one-off words. "
                "If a phrase is unclear, summarize it cautiously instead of quoting or building a joke around it. "
                "Prioritize the evidence pack over the raw transcript when they conflict. "
                "Never claim a person caused a crash, hit another car, died, or was injured unless the evidence explicitly says so. "
                "If the clip involves a crash, fire, injury, death, panic, or rescue, keep humor restrained and never joke about a victim's pain, burning, injury, or death. "
                "For serious scenes, aim jokes at strategy, confusion, timing, or narration instead of the harmed person. "
                "Never describe API providers, placeholder text, prompts, or pipeline internals as clip content. "
                "Use concrete evidence from the transcript or visual context in every output. "
                "Tone must be unmistakable: formal is neutral, sarcastic is mean-but-not-hurtful and mocks the situation rather than a person's body, pain, identity, or trauma, humorous_tech uses software/AI metaphors, humorous_non_tech avoids tech jargon and may lightly tease a person's choices or overreaction without being cruel. "
                "Keep rhetorical devices mutually exclusive: sarcastic uses irony and situational mockery with no tech metaphors; humorous_tech uses one software, AI, or engineering metaphor with no courtroom sarcasm; humorous_non_tech uses everyday playful teasing with no tech terms and no deadpan irony. "
                "Sarcastic examples should feel dry and mildly biting, like mocking an overdramatic situation for treating a small problem like a major crisis. Avoid insults aimed at vulnerable people."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Evidence pack:\n{evidence_context}\n\nRaw transcript:\n{transcript_context}\n\nVisual context:\n{visual_context}\n\n"
                "Return JSON with exactly these keys: formal, sarcastic, humorous_tech, humorous_non_tech. "
                "Each key must contain: styled_caption, summary, tone_notes, confidence. "
                "styled_caption must be one complete sentence in the requested style, 36-50 words long. "
                "summary must be 80-110 words, use 3-4 sentences, and include the clip's concrete action, dialogue, setting, and why the moment matters. "
                "Avoid vague summaries like 'things happen' or 'the clip shows a moment'."
            ),
        },
    ]


def _fallback_style_output(style: CaptionStyle, transcript: str, visual_summary: str | None) -> dict[str, str | float]:
    if transcript.startswith(NO_TRANSCRIPT):
        base = "No transcript is available yet, so this draft should be treated as a cautious placeholder rather than a final judged summary."
    else:
        base = transcript.strip()
    if visual_summary and not visual_summary.startswith(NO_VISUAL_CONTEXT):
        base = f"{base} Visual context: {visual_summary}"
    templates = {
        CaptionStyle.formal: (
            "A clear formal caption describes the clip's central action, key participants, and visible stakes with neutral wording and no exaggerated claims or jokes.",
            "A factual summary explains the main action, setting, important dialogue, and visible context from the clip while staying grounded in the available transcript and scene evidence: " + base,
        ),
        CaptionStyle.sarcastic: (
            "Apparently, this clip has decided subtlety is optional, turning a tense moment into a showcase of questionable choices and dramatic timing.",
            "A dry, sarcastic summary explains the same clip with wit, restrained bite, and clear respect for the actual spoken and visual facts: " + base,
        ),
        CaptionStyle.humorous_tech: (
            "Runtime alert: this clip ships a high-pressure feature with unstable inputs, questionable decision logic, and absolutely no obvious rollback plan.",
            "A tech-flavored summary describes the clip using software or AI metaphors, while keeping the underlying events accurate, concrete, and easy to understand: " + base,
        ),
        CaptionStyle.humorous_non_tech: (
            "This clip turns pressure, confusion, and timing into a memorable little scene where everyone has feelings and nobody gets a quiet moment.",
            "A playful non-technical summary describes what happens in the clip with broad humor, warm wording, concrete details, and no developer jargon: " + base,
        ),
    }
    styled_caption, summary = templates[style]
    return {"styled_caption": styled_caption, "summary": summary, "tone_notes": STYLE_GUIDE[style], "confidence": 0.72}


def generate_for_job(job_id: str) -> None:
    job = load_job(job_id)
    try:
        job.status = JobStatus.processing
        job.progress = 12
        job.message = "Reading clip metadata"
        duration = probe_duration(job.video_path)
        job.duration_seconds = duration
        if duration and settings.min_duration_seconds is not None and duration < settings.min_duration_seconds:
            raise ValueError(f"Video must be at least {settings.min_duration_seconds:g} seconds.")
        if duration and settings.max_duration_seconds is not None and duration > settings.max_duration_seconds:
            raise ValueError(f"Video must be no longer than {settings.max_duration_seconds:g} seconds.")
        save_job(job)

        job.progress = 20
        job.message = "Normalizing clip timestamps"
        save_job(job)
        normalized_video = normalize_video(job.video_path, settings.storage_dir / "normalized", job.job_id)
        if normalized_video:
            job.video_path = str(normalized_video)
            duration = probe_duration(job.video_path) or duration
            job.duration_seconds = duration
            save_job(job)

        job.progress = 30
        job.message = "Extracting audio"
        save_job(job)
        audio_path = extract_audio(job.video_path, settings.storage_dir / "uploads")

        job.progress = 48
        job.message = "Building transcript, timed captions, and factual base"
        job.transcript, job.caption_track, job.transcript_provider = transcribe(audio_path, job.video_path, duration)
        frames = extract_keyframes(job.video_path, settings.storage_dir / "uploads", duration)
        job.visual_summary, job.visual_provider = describe_frames(frames)
        job.caption_track = add_sound_tags(job.caption_track, duration, job.visual_summary)
        if job.transcript.startswith(NO_TRANSCRIPT):
            job.base_summary = "No transcript is available yet. Captions will rely on visual context if available."
        else:
            job.base_summary = "Factual base generated from the clip transcript/context for tone-controlled captioning."
        save_job(job)

        job.progress = 62
        job.message = "Rendering captioned video"
        rendered = render_captioned_video(job.video_path, job.caption_track, settings.storage_dir / "captioned", job.job_id)
        job.captioned_video_path = str(rendered) if rendered else None
        save_job(job)

        fallback = {style.value: _fallback_style_output(style, job.transcript, job.visual_summary) for style in CaptionStyle}
        transcript_context = (
            "Transcript is unavailable. Do not mention provider names, placeholders, APIs, or internal pipeline details. "
            "Use the visual context if provided; otherwise return cautious summaries that state the clip needs more context before final judging."
            if job.transcript.startswith(NO_TRANSCRIPT)
            else job.transcript
        )
        visual_context = (
            "Visual context unavailable."
            if not job.visual_summary or job.visual_summary.startswith(NO_VISUAL_CONTEXT)
            else job.visual_summary
        )
        evidence_context = _evidence_pack(job.transcript, job.caption_track, job.visual_summary)
        prompt = _generation_prompt(transcript_context, visual_context, evidence_context)
        raw, provider = caption_llm.complete_json(prompt, fallback)
        job.generation_provider = provider
        job.generation_diagnostics = caption_llm.last_provider_errors

        style_outputs: list[StyleOutput] = []
        for style in CaptionStyle:
            item = raw.get(style.value, fallback[style.value])
            styled_caption = str(item.get("styled_caption", fallback[style.value]["styled_caption"]))
            summary = str(item.get("summary", fallback[style.value]["summary"]))
            style_outputs.append(
                StyleOutput(
                    style=style,
                    styled_caption=styled_caption,
                    summary=summary,
                    tone_notes=str(item.get("tone_notes", STYLE_GUIDE[style])),
                    confidence=float(item.get("confidence", 0.75)),
                    evaluation=heuristic_evaluation(style, styled_caption, summary, job.transcript),
                )
            )

        job.style_outputs = style_outputs
        job.status = JobStatus.complete
        job.progress = 100
        if provider == "local_fallback":
            job.message = "Captioned video and four styled outputs generated with local fallback"
        elif job.generation_diagnostics:
            job.message = f"Captioned video and four styled outputs generated with {provider} after provider fallback"
        else:
            job.message = f"Captioned video and four styled outputs generated with {provider}"
        save_job(job)
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        job.message = "Caption and summary generation failed"
        save_job(job)


def generate_for_batch(batch_id: str) -> None:
    batch = load_batch(batch_id)
    try:
        batch.status = JobStatus.processing
        batch.message = "Generating captioned videos and styled outputs for fixed clip set"
        save_batch(batch)
        total = max(1, len(batch.job_ids))
        for index, job_id in enumerate(batch.job_ids, start=1):
            generate_for_job(job_id)
            batch.progress = int((index / total) * 100)
            batch.message = f"Processed {index}/{total} clips"
            save_batch(batch)
        failed = [load_job(job_id) for job_id in batch.job_ids if load_job(job_id).status == JobStatus.failed]
        batch.status = JobStatus.failed if failed else JobStatus.complete
        batch.message = f"Complete: {total - len(failed)}/{total} clips generated"
        batch.error = "; ".join(job.error or job.job_id for job in failed) if failed else None
        save_batch(batch)
    except Exception as exc:
        batch.status = JobStatus.failed
        batch.error = str(exc)
        batch.message = "Batch generation failed"
        save_batch(batch)
