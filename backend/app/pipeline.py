from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from .caption_styles import STYLE_FEW_SHOT, STYLE_GUIDE, STYLE_SYSTEM_PROMPTS
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
        word_count = 0
        for segment in caption_track:
            text = " ".join(str(segment.text).split())
            if not text or text.startswith("["):
                continue
            if len(text.split()) < 3 and not text.endswith(("!", "?")):
                continue
            clean_lines.append(f"{segment.start:.1f}-{segment.end:.1f}s: {text}")
            word_count += len(text.split())
            if word_count >= 60:
                break
        if clean_lines:
            parts.append("Transcript (timed):\n" + "\n".join(clean_lines))
        else:
            parts.append("Transcript:\n" + transcript)

        sound_tags = [s.text for s in caption_track if s.text.startswith("[")]
        if sound_tags:
            parts.append("Audio events: " + ", ".join(set(sound_tags)))
    else:
        parts.append("Transcript unavailable.")

    if visual_summary and not visual_summary.startswith(NO_VISUAL_CONTEXT):
        lines = [l.strip() for l in visual_summary.strip().split("\n") if l.strip()]
        summary_text = " ".join(lines)
        parts.append("Visual analysis:\n" + summary_text)
    else:
        parts.append("Visual analysis: unavailable.")

    transcript_lower = (transcript or "").lower()
    scene_keywords = {
        "sports": ["race", "game", "match", "goal", "score", "player", "team", "track", "lap", "pit", "drive", "ball"],
        "nature": ["tree", "forest", "garden", "animal", "bird", "flower", "mountain", "river", "ocean", "sky", "sun"],
        "urban": ["street", "city", "building", "car", "traffic", "road", "sidewalk", "store", "office"],
        "food": ["cook", "recipe", "kitchen", "food", "eat", "meal", "ingredient", "bake", "chef"],
        "technology": ["computer", "screen", "phone", "code", "software", "data", "system", "app", "device", "robot"],
        "people": ["person", "people", "man", "woman", "child", "group", "crowd", "family", "friend", "interview"],
    }
    detected = [k for k, v in scene_keywords.items() if any(w in transcript_lower for w in v)]
    if detected:
        parts.append("Scene category: " + ", ".join(detected))

    return "\n\n".join(parts)


def _style_specific_prompt(
    style: CaptionStyle,
    transcript_context: str,
    visual_context: str,
    evidence_context: str,
) -> list[dict[str, str]]:
    system_prompt = STYLE_SYSTEM_PROMPTS[style]
    few_shot = STYLE_FEW_SHOT.get(style, [])
    messages = [
        {"role": "system", "content": system_prompt + (
            "\n\nReturn strict JSON only with these keys: styled_caption, summary, tone_notes, confidence. "
            "styled_caption must be one complete sentence in the requested style, 36-50 words. "
            "summary must be concise and under 100 words (ideally 40-70), as a single paragraph or 3-5 bullet points, covering the clip's key action and context."
            "Stay accurate to the evidence. Do not invent facts. "
            "Never mention transcripts, keyframes, APIs, pipelines, or internal details. "
            "Treat ASR as imperfect evidence: prefer named people, visible actions, and repeated clear phrases. "
            "If a phrase is unclear, summarize cautiously instead of quoting it. "
            "Never claim a person caused a crash, hit another car, died, or was injured unless the evidence explicitly says so. "
            "For serious scenes involving crashes, fire, or injury, keep humor restrained. "
            "Use concrete evidence from the transcript or visual context in every output."
        )},
    ]
    for shot in few_shot:
        messages.append(shot)
    messages.append({
        "role": "user",
        "content": (
            f"Evidence pack:\n{evidence_context}\n\nRaw transcript:\n{transcript_context}\n\nVisual context:\n{visual_context}\n\n"
            f"Generate a {style.value} caption and summary."
        ),
    })
    return messages


def _generate_single_style(
    style: CaptionStyle,
    transcript_context: str,
    visual_context: str,
    evidence_context: str,
    fallback_output: dict,
) -> tuple[dict, str]:
    prompt = _style_specific_prompt(style, transcript_context, visual_context, evidence_context)
    raw, provider = caption_llm.complete_json(prompt, fallback_output)
    return raw, provider


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


def _parallel_extract(video_path: str, output_dir, duration) -> tuple[Path | None, list[Path]]:
    """Extract audio and keyframes in parallel."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        audio_future = ex.submit(extract_audio, video_path, output_dir)
        frames_future = ex.submit(extract_keyframes, video_path, output_dir, duration)
        return audio_future.result(), frames_future.result()


def _parallel_understand(audio_path, video_path, duration, frames) -> tuple:
    """Transcribe and describe frames in parallel."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        trans_future = ex.submit(transcribe, audio_path, video_path, duration)
        vis_future = ex.submit(describe_frames, frames)
        transcript, caption_track, trans_provider = trans_future.result()
        visual_summary, vis_provider = vis_future.result()
    return transcript, caption_track, trans_provider, visual_summary, vis_provider


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
        job.message = "Extracting audio and keyframes in parallel"
        save_job(job)
        audio_path, frames = _parallel_extract(job.video_path, settings.storage_dir / "uploads", duration)

        job.progress = 40
        job.message = "Transcribing and analyzing video in parallel"
        save_job(job)
        job.transcript, job.caption_track, job.transcript_provider, job.visual_summary, job.visual_provider = \
            _parallel_understand(audio_path, job.video_path, duration, frames)
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

        job.progress = 70
        job.message = "Generating all 4 style captions in parallel"
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

        provider_used = "unknown"
        all_diagnostics: list[str] = []

        def run_style(style: CaptionStyle) -> tuple[CaptionStyle, StyleOutput, str]:
            raw, provider = _generate_single_style(style, transcript_context, visual_context, evidence_context, fallback[style.value])
            item = raw if "styled_caption" in raw else raw.get(style.value, fallback[style.value])
            styled_caption = str(item.get("styled_caption", item.get("caption", fallback[style.value]["styled_caption"])))
            summary = str(item.get("summary", fallback[style.value]["summary"]))
            output = StyleOutput(
                style=style,
                styled_caption=styled_caption,
                summary=summary,
                tone_notes=str(item.get("tone_notes", STYLE_GUIDE[style])),
                confidence=float(item.get("confidence", 0.75)),
                evaluation=heuristic_evaluation(style, styled_caption, summary, job.transcript),
            )
            return style, output, provider

        results: dict[CaptionStyle, StyleOutput] = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(run_style, style): style for style in CaptionStyle}
            for future in as_completed(futures):
                try:
                    style, output, provider = future.result()
                    results[style] = output
                    if provider != "local_fallback":
                        provider_used = provider
                    if caption_llm.last_provider_errors:
                        all_diagnostics.extend(caption_llm.last_provider_errors)
                except Exception:
                    style = futures[future]
                    results[style] = StyleOutput(
                        style=style,
                        styled_caption=str(fallback[style.value].get("styled_caption", "")),
                        summary=str(fallback[style.value].get("summary", "")),
                        tone_notes=STYLE_GUIDE[style],
                        confidence=0.5,
                        evaluation=heuristic_evaluation(style, fallback[style.value].get("styled_caption", ""), fallback[style.value].get("summary", ""), job.transcript or ""),
                    )
        style_outputs = [results[style] for style in CaptionStyle]

        job.style_outputs = style_outputs
        job.generation_provider = provider_used
        job.generation_diagnostics = all_diagnostics
        job.status = JobStatus.complete
        job.progress = 100
        if provider_used == "local_fallback":
            job.message = "Captioned video and four styled outputs generated with local fallback"
        elif all_diagnostics:
            job.message = f"Captioned video and four styled outputs generated with {provider_used} after provider fallback"
        else:
            job.message = f"Captioned video and four styled outputs generated with {provider_used}"
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
        batch.message = "Generating captioned videos and styled outputs in parallel"
        save_batch(batch)
        total = max(1, len(batch.job_ids))
        completed = 0
        with ThreadPoolExecutor(max_workers=min(3, total)) as ex:
            futures = {ex.submit(generate_for_job, jid): jid for jid in batch.job_ids}
            for future in as_completed(futures):
                completed += 1
                batch.progress = int((completed / total) * 100)
                batch.message = f"Processed {completed}/{total} clips"
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
